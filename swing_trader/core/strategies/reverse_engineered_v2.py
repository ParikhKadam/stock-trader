"""
Reverse Engineered Strategy V2: Fundamental Redesign

Instead of loose conditions with high recall, use tight patterns with high precision.
Focus on forward probability from the start.
"""
from typing import Dict, Any, Optional
import pandas as pd
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class ReverseEngineeredV2Strategy(TradingStrategy):
    """
    V2: Precision-focused approach
    - Waits for extreme setups only
    - Uses confluence of multiple rare events
    - Dynamic exits based on momentum
    - Accepts fewer trades for higher quality
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            # Extreme conditions only
            'vol_threshold': 3.0,    # 3x volume spike
            'rsi_oversold': 25,      # Extreme panic
            'rsi_lookback': 3,       # Must be oversold recently
            'sma_window': 50,
            'price_drop_pct': 0.05,  # Must have dropped 5%+ recently
            'drop_days': 10,         # In last 10 days
            
            # Exit strategy
            'use_trailing_stop': True,
            'trailing_stop_pct': 0.03,  # 3% trailing stop
            'initial_target_pct': 0.08, # Take some profit at 8%
            'max_hold_days': 20,        # Don't hold forever
        }
        params = {**default_params, **(params or {})}
        super().__init__("Reverse Engineered V2", params)
        self.reset_state()

    def reset_state(self):
        self.entry_price = None
        self.entry_date = None
        self.highest_since_entry = None

    def get_min_lookback(self) -> int:
        return max(self.params['sma_window'], self.params['drop_days'] + 20)

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
            # Update highest price since entry
            if self.highest_since_entry is None or latest_close > self.highest_since_entry:
                self.highest_since_entry = latest_close
            
            gain_pct = (latest_close - self.entry_price) / self.entry_price
            
            # Check max hold period
            days_held = len(data[data.index > self.entry_date])
            if days_held >= self.params['max_hold_days']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Max hold period: {gain_pct:+.1%}')
            
            # Check trailing stop
            if self.params['use_trailing_stop'] and self.highest_since_entry:
                drawdown_from_high = (latest_close - self.highest_since_entry) / self.highest_since_entry
                if drawdown_from_high <= -self.params['trailing_stop_pct']:
                    self.reset_state()
                    return TradingSignal(signal='sell', price=latest_close, 
                                       reason=f'Trailing stop: {gain_pct:+.1%}')
            
            # Check initial target
            if gain_pct >= self.params['initial_target_pct']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Target hit: {gain_pct:+.1%}')
            
            return TradingSignal(signal='hold', price=None, reason='in_position')

        # Check for EXTREME entry setup (high precision, low recall)
        recent = data.tail(self.params['drop_days'])
        
        # Condition 1: Extreme volume spike TODAY (not just in window)
        has_extreme_volume = latest['volume'] > self.params['vol_threshold'] * latest['vol_avg']
        
        # Condition 2: RSI in extreme oversold in recent days
        has_extreme_rsi = (recent['rsi'].tail(self.params['rsi_lookback']) < self.params['rsi_oversold']).any()
        
        # Condition 3: Significant price drop from recent high
        recent_high = recent['close'].max()
        price_drop_pct = (latest_close - recent_high) / recent_high
        has_significant_drop = price_drop_pct <= -self.params['price_drop_pct']
        
        # Condition 4: Currently below SMA50
        below_sma = latest_close < latest['sma']
        
        # REQUIRE ALL CONDITIONS (confluence for high precision)
        conditions_met = [has_extreme_volume, has_extreme_rsi, has_significant_drop, below_sma]
        num_conditions = sum(conditions_met)
        
        if all(conditions_met):
            self.entry_price = latest_close
            self.entry_date = latest_date
            self.highest_since_entry = latest_close
            return TradingSignal(signal='buy', price=latest_close, 
                               reason=f'Extreme setup: 3x_vol + RSI<{self.params["rsi_oversold"]} + {price_drop_pct:.1%}_drop + below_SMA')

        return TradingSignal(signal='hold', price=None, 
                           reason=f'waiting_extreme_setup_{num_conditions}/4')