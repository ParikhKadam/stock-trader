"""
Regime-Adaptive Hybrid Strategy for Indian Markets (NSE/BSE)

This strategy automatically detects market regime and applies appropriate logic:
- TRENDING UP: Breakout entries, ride momentum
- SIDEWAYS: Mean reversion, buy dips/sell rallies  
- TRENDING DOWN: Capital preservation, no entries

Optimized for Indian market characteristics:
- Faster swing cycles (3-7 days)
- High retail participation
- Regime-specific entry/exit logic
"""
from typing import Dict, Any, Optional, Literal
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from .base import TradingStrategy, TradingSignal
from ...utils.logging import logger

MarketRegime = Literal['trending_up', 'sideways', 'trending_down']


class HybridStrategy(TradingStrategy):
    """
    Regime-Adaptive Hybrid Strategy for Indian Markets
    
    Automatically detects if market is trending up, sideways, or down,
    then applies regime-appropriate entry/exit logic for better performance.
    """
    
    def __init__(self, params: Dict[str, Any] = None):
        # Optimized defaults for Indian markets
        default_params = {
            # Trend filters
            'sma_fast': 10,           # Faster for Indian market cycles
            'sma_slow': 20,
            'sma_regime': 200,
            
            # Regime detection parameters
            'regime_lookback': 50,     # Days to analyze for regime
            'trending_slope_threshold': 0.08,  # Min slope for trending (relaxed)
            'sideways_range_threshold': 8.0,   # Max % range for sideways (relaxed)
            
            # Keltner Channels (for trending breakouts)
            'kc_length': 20,
            'kc_multiplier': 2.0,
            
            # Bollinger Bands (for mean reversion)
            'bb_length': 20,
            'bb_std': 2.0,
            
            # Volume
            'volume_sma_length': 20,
            'volume_multiplier_trending': 1.3,  # Volume for trending entries (relaxed)
            'volume_multiplier_sideways': 2.0,   # Higher for mean reversion
            
            # ATR for stops
            'atr_length': 14,
            'atr_stop_multiplier': 2.0,
            
            # RSI
            'rsi_period': 14,
            
            # Trending regime thresholds
            'rsi_trending_min': 50,     # Momentum required (relaxed)
            'rsi_trending_max': 75,     # Avoid extreme tops
            
            # Sideways regime thresholds
            'rsi_sideways_buy': 35,     # Oversold entry
            'rsi_sideways_sell': 65,    # Overbought exit
            
            # Liquidity filters (optional)
            'min_daily_turnover_cr': None,
            'min_delivery_pct': None,
        }
        params = {**default_params, **(params or {})}
        super().__init__("Hybrid Regime-Adaptive Strategy", params)
        self.reset_state()
    
    def reset_state(self):
        """Reset any cached state"""
        self._indicators_cache = {}
        self._current_regime = None
    
    def get_min_lookback(self) -> int:
        """Return minimum number of days required"""
        return max(
            self.params['sma_regime'],
            self.params['kc_length'],
            self.params['bb_length'],
            self.params['volume_sma_length'],
            self.params['atr_length'],
            self.params['rsi_period'],
            self.params['regime_lookback']
        ) + 10
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = data.copy()
        
        # SMAs for trend
        df['sma_fast'] = ta.sma(df['close'], length=self.params['sma_fast'])
        df['sma_slow'] = ta.sma(df['close'], length=self.params['sma_slow'])
        df['sma_200'] = ta.sma(df['close'], length=self.params['sma_regime'])
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.params['atr_length'])
        
        # Keltner Channels (for trending)
        kc = ta.kc(df['high'], df['low'], df['close'], 
                   length=self.params['kc_length'], 
                   scalar=self.params['kc_multiplier'])
        df['kc_upper'] = kc[f"KCUe_{self.params['kc_length']}_{self.params['kc_multiplier']}"]
        df['kc_mid'] = kc[f"KCBe_{self.params['kc_length']}_{self.params['kc_multiplier']}"]
        df['kc_lower'] = kc[f"KCLe_{self.params['kc_length']}_{self.params['kc_multiplier']}"]
        
        # Bollinger Bands (for mean reversion)
        bb = ta.bbands(df['close'], length=self.params['bb_length'], std=self.params['bb_std'])
        df['bb_upper'] = bb[f"BBU_{self.params['bb_length']}_{self.params['bb_std']}"]
        df['bb_mid'] = bb[f"BBM_{self.params['bb_length']}_{self.params['bb_std']}"]
        df['bb_lower'] = bb[f"BBL_{self.params['bb_length']}_{self.params['bb_std']}"]
        
        # Volume
        df['volume_sma'] = ta.sma(df['volume'], length=self.params['volume_sma_length'])
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.params['rsi_period'])
        
        return df
    
    def _detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime
        
        Returns:
            'trending_up', 'sideways', or 'trending_down'
        """
        latest = df.iloc[-1]
        lookback_period = self.params['regime_lookback']
        
        # Get recent data for analysis
        recent_df = df.iloc[-lookback_period:]
        
        close = latest['close']
        sma_fast = latest['sma_fast']
        sma_slow = latest['sma_slow']
        sma_200 = latest['sma_200']
        
        # Check for NaN
        if pd.isna([sma_fast, sma_slow, sma_200]).any():
            return 'sideways'  # Default to conservative
        
        # Calculate price trend (linear regression slope)
        prices = recent_df['close'].values
        x = np.arange(len(prices))
        if len(x) > 1:
            slope = np.polyfit(x, prices, 1)[0]
            slope_pct = (slope / close) * 100  # Daily % change
        else:
            slope_pct = 0
        
        # Calculate volatility (range as % of price)
        recent_high = recent_df['high'].max()
        recent_low = recent_df['low'].min()
        price_range_pct = ((recent_high - recent_low) / close) * 100
        
        # SMA alignment
        smas_aligned_up = (sma_fast > sma_slow > sma_200) and (close > sma_fast)
        smas_aligned_down = (sma_fast < sma_slow < sma_200) and (close < sma_fast)
        
        # Decision logic
        if smas_aligned_up and slope_pct > self.params['trending_slope_threshold']:
            return 'trending_up'
        elif smas_aligned_down and slope_pct < -self.params['trending_slope_threshold']:
            return 'trending_down'
        elif price_range_pct < self.params['sideways_range_threshold']:
            return 'sideways'
        else:
            # Mixed signals - check where price is relative to SMA 200
            if close > sma_200:
                return 'sideways'  # Potentially transitioning to uptrend
            else:
                return 'trending_down'  # Conservative approach
    
    def _entry_trending_up(self, df: pd.DataFrame) -> tuple[bool, str, Optional[float]]:
        """
        Entry logic for TRENDING UP markets
        Strategy: Breakout + Momentum
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = latest['close']
        kc_upper = latest['kc_upper']
        volume = latest['volume']
        volume_sma = latest['volume_sma']
        rsi = latest['rsi']
        atr = latest['atr']
        
        # Check for NaN
        if pd.isna([kc_upper, volume_sma, rsi, atr]).any():
            return False, "Indicators not ready", None
        
        # 1. KC Breakout (close above upper KC)
        kc_breakout = close > kc_upper
        if not kc_breakout:
            return False, "No KC breakout", None
        
        # 2. Volume confirmation
        volume_confirmed = volume > (self.params['volume_multiplier_trending'] * volume_sma)
        if not volume_confirmed:
            return False, f"Low volume {volume/volume_sma:.1f}x", None
        
        # 3. RSI in momentum zone (not overbought)
        if rsi < self.params['rsi_trending_min'] or rsi > self.params['rsi_trending_max']:
            return False, f"RSI {rsi:.0f} outside momentum zone", None
        
        # Stop loss
        stop_loss = close - (self.params['atr_stop_multiplier'] * atr)
        
        reason = f"TREND: KC breakout, Vol {volume/volume_sma:.1f}x, RSI {rsi:.0f}"
        return True, reason, stop_loss
    
    def _entry_sideways(self, df: pd.DataFrame) -> tuple[bool, str, Optional[float]]:
        """
        Entry logic for SIDEWAYS markets
        Strategy: Mean Reversion (buy dips)
        """
        latest = df.iloc[-1]
        
        close = latest['close']
        bb_lower = latest['bb_lower']
        bb_mid = latest['bb_mid']
        volume = latest['volume']
        volume_sma = latest['volume_sma']
        rsi = latest['rsi']
        atr = latest['atr']
        
        # Check for NaN
        if pd.isna([bb_lower, bb_mid, volume_sma, rsi, atr]).any():
            return False, "Indicators not ready", None
        
        # 1. Price near lower BB (oversold)
        near_lower_bb = close < (bb_lower * 1.02)  # Within 2% of lower BB
        if not near_lower_bb:
            return False, f"Price not near lower BB", None
        
        # 2. RSI oversold
        if rsi > self.params['rsi_sideways_buy']:
            return False, f"RSI {rsi:.0f} not oversold", None
        
        # 3. Strong volume (panic selling / capitulation)
        volume_confirmed = volume > (self.params['volume_multiplier_sideways'] * volume_sma)
        if not volume_confirmed:
            return False, f"Need panic volume {volume/volume_sma:.1f}x", None
        
        # Stop loss (below recent swing low)
        recent_low = df['low'].iloc[-10:].min()
        stop_loss = recent_low * 0.98  # 2% below recent low
        
        reason = f"RANGE: BB lower touch, RSI {rsi:.0f}, Vol {volume/volume_sma:.1f}x"
        return True, reason, stop_loss
    
    def _entry_trending_down(self, df: pd.DataFrame) -> tuple[bool, str, Optional[float]]:
        """
        Entry logic for TRENDING DOWN markets
        Strategy: Capital preservation (NO entries)
        """
        return False, "Trending down - no entries (capital preservation)", None
    
    def _exit_trending_up(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Exit logic for trending markets - let winners run longer"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        close = latest['close']
        sma_200 = latest['sma_200']
        sma_fast = latest['sma_fast']
        sma_slow = latest['sma_slow']
        prev_fast = prev['sma_fast']
        prev_slow = prev['sma_slow']
        
        # Only exit on STRONG reversal signals
        
        # Exit 1: Price breaks below SMA 200 (regime change)
        if close < sma_200:
            return True, f"Below SMA 200 (regime change)"
        
        # Exit 2: SMA bearish crossover CONFIRMED (both below)
        if sma_fast < sma_slow and prev_fast >= prev_slow:
            return True, f"SMA bearish crossover"
        
        # Otherwise, let it ride the trend
        return False, "Hold - trend intact"
    
    def _exit_sideways(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Exit logic for sideways markets - take quick profits"""
        latest = df.iloc[-1]
        
        close = latest['close']
        bb_mid = latest['bb_mid']
        bb_upper = latest['bb_upper']
        rsi = latest['rsi']
        
        # Exit 1: Price near BB midline (mean reversion complete)
        if close > bb_mid * 0.98:  # Within 2% of midline
            return True, f"Mean reversion to BB mid"
        
        # Exit 2: RSI overbought (take profits)
        if not pd.isna(rsi) and rsi > self.params['rsi_sideways_sell']:
            return True, f"RSI {rsi:.0f} overbought - take profit"
        
        # Exit 3: Price near upper BB (full reversion)
        if close > bb_upper * 0.98:
            return True, f"Full reversion to upper BB"
        
        return False, "Hold - waiting for mean reversion"
    
    def _exit_trending_down(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Exit logic for trending down - exit immediately"""
        return True, "Trending down detected - exit position"
    
    def generate_signal(self, historical_data: pd.DataFrame) -> TradingSignal:
        """
        Generate trading signal based on regime-adaptive strategy
        
        Process:
        1. Detect market regime (trending_up, sideways, trending_down)
        2. Apply regime-specific entry logic
        3. Apply regime-specific exit logic
        """
        if not self.validate_data(historical_data):
            logger.error("Invalid data format for Hybrid strategy")
            return TradingSignal(signal='hold', price=None, reason='invalid_data')
        
        if len(historical_data) < self.get_min_lookback():
            return TradingSignal(
                signal='hold', 
                price=None, 
                reason=f'insufficient_data (need {self.get_min_lookback()} days)'
            )
        
        # Ensure data is sorted
        data = historical_data.copy().sort_index()
        
        # Calculate all indicators
        df = self._calculate_indicators(data)
        
        latest_close = df['close'].iloc[-1]
        
        # Detect market regime
        regime = self._detect_market_regime(df)
        self._current_regime = regime
        
        logger.debug(f"Market regime detected: {regime}")
        
        # Check exit conditions first (regime-specific)
        if regime == 'trending_up':
            should_exit, exit_reason = self._exit_trending_up(df)
        elif regime == 'sideways':
            should_exit, exit_reason = self._exit_sideways(df)
        else:  # trending_down
            should_exit, exit_reason = self._exit_trending_down(df)
        
        if should_exit:
            return TradingSignal(
                signal='sell',
                price=latest_close,
                reason=f"[{regime.upper()}] {exit_reason}"
            )
        
        # Check entry conditions (regime-specific)
        if regime == 'trending_up':
            should_enter, entry_reason, stop_loss = self._entry_trending_up(df)
        elif regime == 'sideways':
            should_enter, entry_reason, stop_loss = self._entry_sideways(df)
        else:  # trending_down
            should_enter, entry_reason, stop_loss = self._entry_trending_down(df)
        
        if should_enter:
            logger.info(f"BUY signal: {entry_reason}")
            return TradingSignal(
                signal='buy',
                price=latest_close,
                reason=entry_reason
            )
        
        # Default: Hold
        return TradingSignal(
            signal='hold',
            price=None,
            reason=f'[{regime.upper()}] {entry_reason}'
        )
