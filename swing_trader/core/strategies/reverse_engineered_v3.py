"""
Reverse Engineered Strategy V3: Mean Reversion Focus

Key insight: The patterns don't predict BIG moves (10%+), but they might predict
SMALL bounces (2-4%) from oversold conditions. Adjust strategy accordingly.
"""
from typing import Dict, Any, Optional
import pandas as pd
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class ReverseEngineeredV3Strategy(TradingStrategy):
    """
    V3: Mean reversion approach
    - Accept that we can't predict 10% moves
    - Focus on 2-3% bounce from extreme oversold
    - Very tight stops (1%)
    - Take profit quickly (2-3%)
    - Higher win rate, smaller wins
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            # Entry conditions
            'rsi_oversold': 30,      # Oversold level
            'rsi_lookback': 5,       # Recent days
            'sma_window': 50,
            'vol_threshold': 2.0,    # Moderate volume
            
            # Exit strategy - SMALL targets for mean reversion
            'target_pct': 0.03,      # 3% target (realistic)
            'stop_pct': 0.01,        # 1% stop (tight)
            'max_hold_days': 5,      # Quick in/out
            
            # Risk management
            'require_below_sma': True,  # Only buy dips below trend
        }
        params = {**default_params, **(params or {})}
        super().__init__("Reverse Engineered V3 (Mean Reversion)", params)
        self.reset_state()

    def reset_state(self):
        self.entry_price = None
        self.entry_date = None

    def get_min_lookback(self) -> int:
        return max(self.params['sma_window'], 20)

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(historical_data):
            return TradingSignal(signal='hold', price=None, reason='invalid_data')

        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        data = historical_data.copy().sort_index()

        # Calculate indicators
        data['sma'] = data['close'].rolling(self.params['sma_window']).mean()
        data['rsi'] = self.calculate_rsi(data['close'])
        data['vol_avg'] = data['volume'].rolling(20).mean()

        latest = data.iloc[-1]
        latest_close = latest['close']
        latest_date = data.index[-1]

        # If in position, check exit
        if self.entry_price is not None:
            gain_pct = (latest_close - self.entry_price) / self.entry_price
            
            # Quick exit on target (mean reversion complete)
            if gain_pct >= self.params['target_pct']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Mean reversion target: {gain_pct:+.1%}')
            
            # Tight stop to preserve capital
            if gain_pct <= -self.params['stop_pct']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Stop loss: {gain_pct:+.1%}')
            
            # Don't hold too long (mean reversion trades are quick)
            days_held = len(data[data.index > self.entry_date])
            if days_held >= self.params['max_hold_days']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Max hold: {gain_pct:+.1%}')
            
            return TradingSignal(signal='hold', price=None, reason='in_position')

        # Entry: oversold + volume confirmation
        recent = data.tail(self.params['rsi_lookback'])
        
        # RSI oversold in recent days
        is_oversold = (recent['rsi'] < self.params['rsi_oversold']).any()
        
        # Volume confirmation (interest in the stock)
        has_volume = latest['volume'] > self.params['vol_threshold'] * latest['vol_avg']
        
        # Below SMA (buy the dip in downtrend)
        below_sma = latest_close < latest['sma']
        
        # Enter on oversold + volume
        if is_oversold and has_volume:
            # Only if below SMA (if required)
            if self.params['require_below_sma'] and not below_sma:
                return TradingSignal(signal='hold', price=None, reason='above_sma')
            
            self.entry_price = latest_close
            self.entry_date = latest_date
            return TradingSignal(signal='buy', price=latest_close, 
                               reason=f'Oversold bounce: RSI<{self.params["rsi_oversold"]} + vol{self.params["vol_threshold"]}x')

        return TradingSignal(signal='hold', price=None, reason='waiting_oversold')