"""
Simple Moving Average crossover strategy using pandas-ta-classic
"""
from typing import Dict, Any, Optional
import pandas as pd
import pandas_ta_classic as ta
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class SimpleMovingAverageTAStrategy(TradingStrategy):
    """
    Simple moving average crossover strategy using pandas-ta-classic
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {'short_window': 10, 'long_window': 20}
        params = {**default_params, **(params or {})}
        super().__init__("SMA Crossover TA", params)

    def get_min_lookback(self) -> int:
        return self.params['long_window']

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on SMA crossover using pandas-ta-classic."""
        if not self.validate_data(historical_data):
            logger.error("Invalid data format for SMA TA strategy")
            return TradingSignal(signal='hold', price=None, reason='invalid_data')

        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        # Ensure data is sorted
        data = historical_data.copy().sort_index()

        # Calculate SMAs using pandas-ta-classic
        data['sma_short'] = ta.sma(data['close'], length=self.params['short_window'])
        data['sma_long'] = ta.sma(data['close'], length=self.params['long_window'])

        # Get the last two days for crossover detection
        if len(data) < 2:
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        prev_short = data['sma_short'].iloc[-2]
        prev_long = data['sma_long'].iloc[-2]
        curr_short = data['sma_short'].iloc[-1]
        curr_long = data['sma_long'].iloc[-1]
        latest_close = data['close'].iloc[-1]

        if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        # Bullish crossover: short MA crosses above long MA
        if curr_short > curr_long and prev_short <= prev_long:
            return TradingSignal(
                signal='buy',
                price=latest_close,
                reason=f'SMA{self.params["short_window"]} crossed above SMA{self.params["long_window"]}'
            )
        # Bearish crossover: short MA crosses below long MA
        elif curr_short < curr_long and prev_short >= prev_long:
            return TradingSignal(
                signal='sell',
                price=latest_close,
                reason=f'SMA{self.params["short_window"]} crossed below SMA{self.params["long_window"]}'
            )

        return TradingSignal(signal='hold', price=None, reason='no_crossover')