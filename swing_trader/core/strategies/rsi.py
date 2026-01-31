"""
Relative Strength Index (RSI) strategy
"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class RSIStrategy(TradingStrategy):
    """
    RSI-based trading strategy

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
        super().__init__("RSI Strategy", params)
        self.reset_state()

    def reset_state(self):
        """Reset any cached state"""
        pass

    def get_min_lookback(self) -> int:
        return self.params['rsi_period'] + 1

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI for the given price series"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """Generate trading signal based on RSI levels"""
        if not self.validate_data(historical_data):
            logger.error("Invalid data format for RSI strategy")
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
        latest_close = close_prices.iloc[-1]

        # Calculate RSI
        rsi = self._calculate_rsi(close_prices, self.params['rsi_period'])
        current_rsi = rsi.iloc[-1]

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