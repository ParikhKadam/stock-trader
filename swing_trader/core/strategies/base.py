"""
Base classes for trading strategies
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field
from ...utils.logging import logger


class TradingSignal(BaseModel):
    """
    Standardized trading signal response
    """
    signal: str = Field(..., description="Trading signal: 'buy', 'sell', or 'hold'")
    price: Optional[float] = Field(None, description="Execution price (None for hold signals)")
    reason: str = Field(..., description="Reason for the signal")

    def __str__(self) -> str:
        return f"Signal({self.signal}, price={self.price}, reason='{self.reason}')"


class TradingStrategy(ABC):
    """
    Base class for trading strategies
    """

    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """
        Generate a trading signal for the next day based on historical data up to today

        Args:
            historical_data: DataFrame with columns ['date', 'open', 'high', 'low', 'close', 'volume']
                             Data up to current date (t), used to predict signal for t+1

        Returns:
            TradingSignal object with signal, price, and reason
        """
        pass

    def reset_state(self):
        """Reset internal state (e.g., cached indicators)"""
        pass

    def get_min_lookback(self) -> int:
        """Return minimum number of historical days required for signal generation"""
        return 1

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that data has required columns (case-insensitive)"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        data_columns = [col.lower() for col in data.columns]
        missing = [col for col in required_columns if col not in data_columns]
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return False
        # Normalize column names to snakecase
        data.columns = [col.lower() for col in data.columns]
        return True