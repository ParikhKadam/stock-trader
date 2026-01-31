"""
Trading strategy base classes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
from ..utils.logging import logger


class TradingStrategy(ABC):
    """
    Base class for trading strategies
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate trading signals based on data

        Returns:
            Dict with keys like 'buy', 'sell', 'hold' and associated data
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that data has required columns"""
        required_columns = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        return all(col in data.columns for col in required_columns)


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Simple moving average crossover strategy
    """

    def __init__(self, short_window: int = 20, long_window: int = 50):
        super().__init__("SMA Crossover")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        if not self.validate_data(data):
            logger.error("Invalid data format for SMA strategy")
            return {'signal': 'hold', 'reason': 'invalid_data'}

        # Calculate moving averages
        data = data.copy()
        data['SMA_short'] = data['CLOSE'].rolling(window=self.short_window).mean()
        data['SMA_long'] = data['CLOSE'].rolling(window=self.long_window).mean()

        # Generate signals
        latest = data.iloc[-1]
        if len(data) < self.long_window:
            return {'signal': 'hold', 'reason': 'insufficient_data'}

        if latest['SMA_short'] > latest['SMA_long']:
            return {
                'signal': 'buy',
                'price': latest['CLOSE'],
                'reason': f'SMA{self.short_window} crossed above SMA{self.long_window}'
            }
        elif latest['SMA_short'] < latest['SMA_long']:
            return {
                'signal': 'sell',
                'price': latest['CLOSE'],
                'reason': f'SMA{self.short_window} crossed below SMA{self.long_window}'
            }
        else:
            return {'signal': 'hold', 'reason': 'no_crossover'}