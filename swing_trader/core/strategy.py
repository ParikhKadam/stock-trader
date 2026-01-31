"""
Trading strategy base classes
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field
from ..utils.logging import logger


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
            historical_data: DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
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

    def get_current_signal(self, data: pd.DataFrame) -> TradingSignal:
        """
        Get signal for the latest data point (for prediction)

        Args:
            data: Recent data DataFrame

        Returns:
            TradingSignal object
        """
        signals_df = self.generate_signals(data)
        if signals_df.empty:
            return TradingSignal(signal='hold', price=None, reason='no_data')
        latest = signals_df.iloc[-1]
        return TradingSignal(
            signal=latest['signal'],
            price=latest['price'],
            reason=latest['reason']
        )


class SimpleMovingAverageStrategy(TradingStrategy):
    """
    Simple moving average crossover strategy
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {'short_window': 20, 'long_window': 50}
        params = {**default_params, **(params or {})}
        super().__init__("SMA Crossover", params)
        self.reset_state()

    def reset_state(self):
        """Reset cached indicators and rolling windows"""
        # Lists to store the last 'window' close prices for efficient rolling mean calculation
        self.short_closes = []
        self.long_closes = []
        # Running sums for O(1) updates
        self.short_sum = 0.0
        self.long_sum = 0.0
        # Cached MA values for crossover detection (current day's MAs)
        self.sma_short = None
        self.sma_long = None

    def get_min_lookback(self) -> int:
        return self.params['long_window']

    def _update_rolling_mean(self, new_close: float, closes_list: list, sum_val: float, window: int) -> tuple:
        """Update rolling mean incrementally, return (new_sum, new_mean)
        
        This maintains a sliding window of closes and updates the sum in O(1) time.
        - Append new close to the list.
        - Add to sum.
        - If list exceeds window, remove oldest close and subtract from sum.
        - Return new sum and mean (if window is full).
        """
        closes_list.append(new_close)
        sum_val += new_close
        if len(closes_list) > window:
            sum_val -= closes_list.pop(0)
        if len(closes_list) == window:
            return sum_val, sum_val / window
        return sum_val, None

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on SMA crossover.
        
        This strategy uses incremental updates to maintain rolling MAs efficiently.
        - Updates MAs with the latest close from historical_data.
        - Detects crossover by comparing previous day's MAs with current day's MAs.
        - Signals are for the next trading day (t+1), using today's close as execution price.
        """
        if not self.validate_data(historical_data):
            logger.error("Invalid data format for SMA strategy")
            return TradingSignal(signal='hold', price=None, reason='invalid_data')

        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        # Ensure date is datetime and sorted
        historical_data = historical_data.copy()
        if 'date' not in historical_data.columns:
            historical_data = historical_data.reset_index().rename(columns={'index': 'date'})
        historical_data['date'] = pd.to_datetime(historical_data['date'])
        historical_data = historical_data.sort_values('date').reset_index(drop=True)

        close_prices = historical_data['close']

        # Capture previous MA values before updating (for crossover detection)
        prev_sma_short = self.sma_short
        prev_sma_long = self.sma_long

        # Update rolling MAs incrementally with the latest close
        # This assumes historical_data ends with today's data (t)
        latest_close = close_prices.iloc[-1]
        self.short_sum, self.sma_short = self._update_rolling_mean(latest_close, self.short_closes, self.short_sum, self.params['short_window'])
        self.long_sum, self.sma_long = self._update_rolling_mean(latest_close, self.long_closes, self.long_sum, self.params['long_window'])

        # Check for crossover: compare previous day's MAs with current day's MAs
        # Only signal if both MAs are available and we have previous values
        if self.sma_short is not None and self.sma_long is not None and prev_sma_short is not None and prev_sma_long is not None:
            # Bullish crossover: short MA crosses above long MA
            if self.sma_short > self.sma_long and prev_sma_short <= prev_sma_long:
                return TradingSignal(
                    signal='buy',
                    price=latest_close,  # Execute at today's close price
                    reason=f'SMA{self.params["short_window"]} crossed above SMA{self.params["long_window"]}'
                )
            # Bearish crossover: short MA crosses below long MA
            elif self.sma_short < self.sma_long and prev_sma_short >= prev_sma_long:
                return TradingSignal(
                    signal='sell',
                    price=latest_close,  # Execute at today's close price
                    reason=f'SMA{self.params["short_window"]} crossed below SMA{self.params["long_window"]}'
                )

        # No crossover or insufficient data for comparison
        return TradingSignal(signal='hold', price=None, reason='no_crossover')