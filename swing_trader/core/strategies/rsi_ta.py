"""
Relative Strength Index (RSI) strategy using pandas-ta-classic
"""
from typing import Dict, Any, Optional
import pandas as pd
import pandas_ta_classic as ta
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class RSITAStrategy(TradingStrategy):
    """
    RSI-based trading strategy using pandas-ta-classic

    Generates signals based on RSI overbought/oversold levels.
    - Buy when RSI < 30 (oversold)
    - Sell when RSI > 70 (overbought)
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'rsi_period': 14,
            'overbought': 75,
            'oversold': 25
        }
        params = {**default_params, **(params or {})}
        super().__init__("RSI TA Strategy", params)

    def get_min_lookback(self) -> int:
        return self.params['rsi_period'] + 1

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on RSI levels using pandas-ta-classic"""
        if not self.validate_data(historical_data):
            logger.error("Invalid data format for RSI TA strategy")
            return TradingSignal(signal='hold', price=None, reason='invalid_data')

        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        # Ensure data is sorted
        data = historical_data.copy().sort_index()

        # Calculate RSI using pandas-ta-classic
        data['rsi'] = ta.rsi(data['close'], length=self.params['rsi_period'])

        latest_close = data['close'].iloc[-1]
        current_rsi = data['rsi'].iloc[-1]

        if pd.isna(current_rsi):
            return TradingSignal(signal='hold', price=None, reason='rsi_not_available')

        # Generate signals based on RSI levels
        if current_rsi <= self.params['oversold']:
            return TradingSignal(
                signal='buy',
                price=latest_close,
                reason=f'RSI {current_rsi:.2f} <= {self.params["oversold"]} (oversold)'
            )
        elif current_rsi >= self.params['overbought']:
            return TradingSignal(
                signal='sell',
                price=latest_close,
                reason=f'RSI {current_rsi:.2f} >= {self.params["overbought"]} (overbought)'
            )

        return TradingSignal(signal='hold', price=None, reason=f'RSI {current_rsi:.2f} in neutral zone')