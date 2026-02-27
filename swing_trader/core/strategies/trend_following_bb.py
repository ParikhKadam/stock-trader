"""
Trend Following Strategy: The Opposite Insight

Key realization: If oversold conditions don't predict profitable reversals,
maybe OVERBOUGHT conditions predict profitable continuations.

Flip the logic: Buy breakouts above Bollinger Bands in uptrends.
"""
from typing import Dict, Any, Optional
import pandas as pd
import pandas_ta_classic as ta
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class TrendFollowingBBStrategy(TradingStrategy):
    """
    Trend Following with Bollinger Bands
    - Buy when price breaks ABOVE upper band (strength continuation)
    - Ride the trend with trailing stop
    - Exit when momentum fades or stop hit
    
    This is the OPPOSITE of mean reversion - follow strength, not weakness.
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            # Bollinger Band parameters
            'bb_length': 20,
            'bb_std': 2.0,
            'bb_breakout_pct': 0.005,  # Must be 0.5% above upper band
            
            # Trend filter
            'use_trend_filter': True,
            'trend_sma': 50,  # Only buy if above this SMA (uptrend)
            
            # Volume confirmation
            'vol_threshold': 1.3,  # Breakout with volume
            
            # Exit strategy
            'use_trailing_stop': True,
            'trailing_stop_pct': 0.03,  # 3% trailing
            'initial_stop_pct': 0.02,    # 2% initial stop
            'max_hold_days': 15,
        }
        params = {**default_params, **(params or {})}
        super().__init__("Trend Following BB", params)
        self.reset_state()

    def reset_state(self):
        self.entry_price = None
        self.entry_date = None
        self.highest_since_entry = None

    def get_min_lookback(self) -> int:
        return max(self.params['bb_length'] + 20, self.params['trend_sma'])

    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        if not self.validate_data(historical_data):
            return TradingSignal(signal='hold', price=None, reason='invalid_data')

        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(signal='hold', price=None, reason='insufficient_data')

        data = historical_data.copy().sort_index()

        # Calculate Bollinger Bands
        bb = ta.bbands(data['close'], length=self.params['bb_length'], std=self.params['bb_std'])
        data['bb_lower'] = bb[f'BBL_{self.params["bb_length"]}_{self.params["bb_std"]}']
        data['bb_middle'] = bb[f'BBM_{self.params["bb_length"]}_{self.params["bb_std"]}']
        data['bb_upper'] = bb[f'BBU_{self.params["bb_length"]}_{self.params["bb_std"]}']
        
        # Trend filter
        data['sma_trend'] = data['close'].rolling(self.params['trend_sma']).mean()
        data['vol_avg'] = data['volume'].rolling(20).mean()

        latest = data.iloc[-1]
        latest_close = latest['close']
        latest_date = data.index[-1]

        # If in position, manage exits
        if self.entry_price is not None:
            # Update highest price
            if self.highest_since_entry is None or latest_close > self.highest_since_entry:
                self.highest_since_entry = latest_close
            
            gain_pct = (latest_close - self.entry_price) / self.entry_price
            
            # Trailing stop
            if self.params['use_trailing_stop'] and self.highest_since_entry:
                drawdown = (latest_close - self.highest_since_entry) / self.highest_since_entry
                if drawdown <= -self.params['trailing_stop_pct']:
                    self.reset_state()
                    return TradingSignal(signal='sell', price=latest_close, 
                                       reason=f'Trailing stop: {gain_pct:+.1%}')
            
            # Initial stop loss
            if gain_pct <= -self.params['initial_stop_pct']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Stop loss: {gain_pct:+.1%}')
            
            # Max hold period
            days_held = len(data[data.index > self.entry_date])
            if days_held >= self.params['max_hold_days']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Max hold: {gain_pct:+.1%}')
            
            # Exit if trend reverses (close below middle BB)
            if not pd.isna(latest['bb_middle']) and latest_close < latest['bb_middle']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Momentum fade: {gain_pct:+.1%}')
            
            return TradingSignal(signal='hold', price=None, reason='in_position')

        # Entry: Breakout ABOVE upper Bollinger Band
        if pd.isna(latest['bb_upper']) or pd.isna(latest['sma_trend']):
            return TradingSignal(signal='hold', price=None, reason='indicators_not_ready')
        
        # Check if price broke above upper band
        distance_from_upper = (latest_close - latest['bb_upper']) / latest['bb_upper']
        above_upper_band = distance_from_upper >= self.params['bb_breakout_pct']
        
        # Trend filter: only buy in uptrend
        in_uptrend = latest_close > latest['sma_trend']
        
        # Volume confirmation
        has_volume = latest['volume'] > self.params['vol_threshold'] * latest['vol_avg']
        
        # Entry signal: Breakout + uptrend + volume
        entry_conditions = [above_upper_band, has_volume]
        if self.params['use_trend_filter']:
            entry_conditions.append(in_uptrend)
        
        if all(entry_conditions):
            self.entry_price = latest_close
            self.entry_date = latest_date
            self.highest_since_entry = latest_close
            
            return TradingSignal(signal='buy', price=latest_close, 
                               reason=f'BB breakout: {distance_from_upper:+.2%} above upper band')

        return TradingSignal(signal='hold', price=None, reason='waiting_breakout')