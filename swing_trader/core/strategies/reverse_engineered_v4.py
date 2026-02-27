"""
Reverse Engineered Strategy V4: Bollinger Band Mean Reversion

Key insight: Bollinger Bands provide statistical measure of oversold/overbought
Price at lower band = 2 std deviations below mean = true extreme
This should have higher precision than generic RSI thresholds
"""
from typing import Dict, Any, Optional
import pandas as pd
import pandas_ta_classic as ta
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger


class ReverseEngineeredV4Strategy(TradingStrategy):
    """
    V4: Bollinger Band mean reversion
    - Enter when price touches/crosses below lower BB (statistical extreme)
    - Exit at middle BB (mean reversion complete) or stop loss
    - Add volume confirmation to reduce false signals
    """

    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            # Bollinger Band parameters
            'bb_length': 20,         # Standard BB period
            'bb_std': 2.0,           # Standard deviations
            'bb_touch_pct': 0.002,   # Must be within 0.2% of lower band
            
            # Confirmation filters
            'vol_threshold': 1.5,    # Volume confirmation
            'rsi_max': 40,           # Additional RSI filter (optional)
            
            # Exit strategy
            'exit_at_middle': True,  # Exit at BB middle (mean reversion)
            'stop_pct': 0.015,       # 1.5% stop below entry
            'max_hold_days': 10,     # Don't hold forever
        }
        params = {**default_params, **(params or {})}
        super().__init__("Reverse Engineered V4 (Bollinger)", params)
        self.reset_state()

    def reset_state(self):
        self.entry_price = None
        self.entry_date = None
        self.entry_lower_bb = None

    def get_min_lookback(self) -> int:
        return max(self.params['bb_length'] + 20, 50)

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

        # Calculate Bollinger Bands using pandas_ta_classic
        bb = ta.bbands(data['close'], length=self.params['bb_length'], std=self.params['bb_std'])
        data['bb_lower'] = bb[f'BBL_{self.params["bb_length"]}_{self.params["bb_std"]}']
        data['bb_middle'] = bb[f'BBM_{self.params["bb_length"]}_{self.params["bb_std"]}']
        data['bb_upper'] = bb[f'BBU_{self.params["bb_length"]}_{self.params["bb_std"]}']
        
        # Additional indicators
        data['rsi'] = self.calculate_rsi(data['close'])
        data['vol_avg'] = data['volume'].rolling(20).mean()

        latest = data.iloc[-1]
        latest_close = latest['close']
        latest_date = data.index[-1]

        # If in position, check exit
        if self.entry_price is not None:
            gain_pct = (latest_close - self.entry_price) / self.entry_price
            
            # Exit 1: Price reached middle band (mean reversion complete)
            if self.params['exit_at_middle'] and not pd.isna(latest['bb_middle']):
                if latest_close >= latest['bb_middle']:
                    self.reset_state()
                    return TradingSignal(signal='sell', price=latest_close, 
                                       reason=f'BB mean reversion: {gain_pct:+.1%}')
            
            # Exit 2: Stop loss
            if gain_pct <= -self.params['stop_pct']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Stop loss: {gain_pct:+.1%}')
            
            # Exit 3: Max hold period
            days_held = len(data[data.index > self.entry_date])
            if days_held >= self.params['max_hold_days']:
                self.reset_state()
                return TradingSignal(signal='sell', price=latest_close, 
                                   reason=f'Max hold: {gain_pct:+.1%}')
            
            return TradingSignal(signal='hold', price=None, reason='in_position')

        # Entry: Price at/below lower Bollinger Band
        if pd.isna(latest['bb_lower']) or pd.isna(latest['bb_middle']):
            return TradingSignal(signal='hold', price=None, reason='bb_not_ready')
        
        # Check if price is at lower band (within tolerance)
        distance_from_lower = (latest_close - latest['bb_lower']) / latest['bb_lower']
        at_lower_band = distance_from_lower <= self.params['bb_touch_pct']
        
        # Additional confirmations
        has_volume = latest['volume'] > self.params['vol_threshold'] * latest['vol_avg']
        rsi_ok = pd.isna(latest['rsi']) or latest['rsi'] < self.params['rsi_max']
        
        # Entry signal: Price at lower BB + volume + RSI
        if at_lower_band and has_volume and rsi_ok:
            self.entry_price = latest_close
            self.entry_date = latest_date
            self.entry_lower_bb = latest['bb_lower']
            
            bb_width = (latest['bb_upper'] - latest['bb_lower']) / latest['bb_middle'] * 100
            return TradingSignal(signal='buy', price=latest_close, 
                               reason=f'BB lower touch: {distance_from_lower:.2%} from band, width={bb_width:.1f}%')

        # Log how close we are
        if distance_from_lower <= 0.01:  # Within 1%
            return TradingSignal(signal='hold', price=None, 
                               reason=f'near_lower_bb_{distance_from_lower:.2%}')
        
        return TradingSignal(signal='hold', price=None, reason='waiting_bb_signal')