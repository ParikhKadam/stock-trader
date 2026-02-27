"""
Reverse Engineered Strategy based on validated patterns
"""
from typing import Dict, Any, Optional
import pandas as pd
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class ReverseEngineeredStrategy(TradingStrategy):
    """
    Strategy based on reverse engineering: volume spike, RSI <50, below SMA50 precede up moves.
    Enters long on conditions, exits on 10% gain or 2% loss.
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'vol_threshold': 2.5,  # Much stricter: 2.5x average (was 1.5x)
            'rsi_threshold': 30,    # Extreme oversold (was 50)
            'sma_window': 50,
            'lookback_days': 5,     # Shorter window for precision
            'target_pct': 0.10,
            'stop_pct': 0.02,
            'require_confluence': True,  # Require multiple conditions
            'min_conditions': 2     # Must have at least 2 conditions
        }
        params = {**default_params, **(params or {})}
        super().__init__("Reverse Engineered (Fixed)", params)
        self.reset_state()

    def reset_state(self):
        self.entry_price = None

    def get_min_lookback(self) -> int:
        return max(self.params['sma_window'], 20, self.params['lookback_days'] + 10)  # For indicators

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
        data['vol_spike'] = data['volume'] > self.params['vol_threshold'] * data['vol_avg']

        latest = data.iloc[-1]
        latest_close = latest['close']

        # If in position, check exit
        if self.entry_price is not None:
            gain_pct = (latest_close - self.entry_price) / self.entry_price
            if gain_pct >= self.params['target_pct']:
                self.entry_price = None
                return TradingSignal(signal='sell', price=latest_close, reason=f'Target hit: {gain_pct:.1%}')
            elif gain_pct <= -self.params['stop_pct']:
                self.entry_price = None
                return TradingSignal(signal='sell', price=latest_close, reason=f'Stop hit: {gain_pct:.1%}')
            else:
                return TradingSignal(signal='hold', price=None, reason='in_position')

        # Check entry conditions with stricter requirements
        recent = data.tail(self.params['lookback_days'])
        
        # Count how many conditions are met
        conditions_met = 0
        reasons = []
        
        # Condition 1: Volume spike (now much rarer at 2.5x)
        has_vol_spike = recent['vol_spike'].any()
        if has_vol_spike:
            conditions_met += 1
            reasons.append('vol_spike_2.5x')
        
        # Condition 2: Extreme RSI (now <30 not <50)
        has_extreme_rsi = (recent['rsi'] < self.params['rsi_threshold']).any()
        if has_extreme_rsi:
            conditions_met += 1
            reasons.append(f'rsi<{self.params["rsi_threshold"]}')
        
        # Condition 3: Below SMA50
        has_below_sma = (recent['close'] < recent['sma']).any()
        if has_below_sma:
            conditions_met += 1
            reasons.append('below_sma50')
        
        # Require confluence: multiple conditions must be true
        if self.params['require_confluence']:
            min_required = self.params['min_conditions']
            if conditions_met >= min_required:
                self.entry_price = latest_close
                reason_str = f"Confluence: {'+'.join(reasons)} ({conditions_met}/{min_required})"
                return TradingSignal(signal='buy', price=latest_close, reason=reason_str)
        else:
            # Old logic: any single condition (not recommended)
            if conditions_met > 0:
                self.entry_price = latest_close
                return TradingSignal(signal='buy', price=latest_close, reason='+'.join(reasons))
        
        return TradingSignal(signal='hold', price=None, reason=f'insufficient_conditions_{conditions_met}')