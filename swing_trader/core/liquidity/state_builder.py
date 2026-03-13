"""
State builder for liquidity swing trading strategy
"""
import pandas as pd
from typing import Optional
from swing_trader.core.models import LiquiditySwingState
from swing_trader.core.liquidity.detectors import (
    find_most_recent_equal_lows,
    detect_sweep,
    detect_reclaim,
    calculate_current_range,
)
from swing_trader.utils.indicators import (
    detect_compression,
    calculate_compression_score,
    volume_ratio,
)
from swing_trader.utils.logging import logger


class LiquiditySwingStateBuilder:
    """
    Builds LiquiditySwingState from OHLCV data
    Orchestrates all liquidity detection primitives
    """
    
    def __init__(
        self,
        swing_order: int = 3,
        equal_level_tolerance: float = 0.003,
        compression_window: int = 10,
        compression_threshold: float = 0.75,
        volume_lookback: int = 20,
        volume_spike_min: float = 1.5,
        reclaim_strength_min: float = 0.6
    ):
        """
        Initialize state builder with detection parameters
        
        Args:
            swing_order: Order for swing low/high detection (bars on each side)
            equal_level_tolerance: Price tolerance for equal levels (0.003 = 0.3%)
            compression_window: Lookback window for compression detection
            compression_threshold: ATR ratio threshold for compression (0.75 = 25% contraction)
            volume_lookback: Period for average volume calculation
            volume_spike_min: Minimum volume ratio for sweep confirmation
            reclaim_strength_min: Minimum candle body strength for reclaim
        """
        self.swing_order = swing_order
        self.equal_level_tolerance = equal_level_tolerance
        self.compression_window = compression_window
        self.compression_threshold = compression_threshold
        self.volume_lookback = volume_lookback
        self.volume_spike_min = volume_spike_min
        self.reclaim_strength_min = reclaim_strength_min
        
        self.min_data_required = max(30, volume_lookback + 10)
        
        logger.debug(f"LiquiditySwingStateBuilder initialized with params: "
                    f"swing_order={swing_order}, tolerance={equal_level_tolerance}, "
                    f"compression={compression_threshold}, volume_spike={volume_spike_min}")
    
    def build(self, df: pd.DataFrame) -> Optional[LiquiditySwingState]:
        """
        Build liquidity swing state from DataFrame
        
        Args:
            df: DataFrame with OHLCV data and datetime index
            
        Returns:
            LiquiditySwingState or None if insufficient data
        """
        # Validate sufficient data
        if len(df) < self.min_data_required:
            logger.warning(f"Insufficient data for state building: {len(df)} < {self.min_data_required}")
            return None
        
        logger.debug(f"Building liquidity state from {len(df)} bars")
        
        # Step 1: Find equal lows
        equal_low_data = self._find_equal_lows(df)
        
        # Step 2: Check for sweep
        sweep_detected, sweep_metadata = self._check_sweep(df, equal_low_data)
        
        # Step 3: Check for reclaim
        reclaim_confirmed, reclaim_metadata = self._check_reclaim(df, equal_low_data)
        
        # Step 4: Check for compression
        compression_detected, compression_score = self._check_compression(df)
        
        # Step 5: Calculate volume metrics
        volume_metrics = self._calculate_volume_metrics(df)
        
        # Step 6: Calculate current range
        current_range = calculate_current_range(df, period=20)
        
        # Build state object
        state = LiquiditySwingState(
            equal_low_count=equal_low_data['count'],
            equal_low_level=equal_low_data['level'],
            sweep_detected=sweep_detected,
            reclaim_confirmed=reclaim_confirmed,
            compression_detected=compression_detected,
            current_range_size=current_range,
            avg_volume_20d=volume_metrics['avg_volume'],
            volume_spike_ratio=volume_metrics['current_ratio'],
            sweep_low=sweep_metadata.get('sweep_low') if sweep_metadata else None,
            reclaim_body_strength=reclaim_metadata.get('body_strength') if reclaim_metadata else None,
            compression_score=compression_score
        )
        
        level_str = f"{equal_low_data['level']:.2f}" if equal_low_data['level'] is not None else "None"
        logger.info(f"State built: {equal_low_data['count']} equal lows at {level_str}, "
                   f"sweep={sweep_detected}, reclaim={reclaim_confirmed}, "
                   f"compression={compression_detected}, tradeable={state.is_tradeable()}")
        
        return state
    
    def _find_equal_lows(self, df: pd.DataFrame) -> dict:
        """Find equal low pattern"""
        equal_low_cluster = find_most_recent_equal_lows(
            df,
            swing_order=self.swing_order,
            tolerance_pct=self.equal_level_tolerance,
            min_occurrences=2,
            recency_window=60
        )
        
        if equal_low_cluster:
            return {
                'count': equal_low_cluster['count'],
                'level': equal_low_cluster['base_level'],
                'touches': equal_low_cluster['touches']
            }
        else:
            # No equal lows found - use most recent swing low as fallback
            logger.debug("No equal low pattern found")
            return {
                'count': 0,
                'level': None,
                'touches': []
            }
    
    def _check_sweep(self, df: pd.DataFrame, equal_low_data: dict) -> tuple:
        """Check if sweep of equal low occurred"""
        if equal_low_data['level'] is None:
            return False, None
        
        sweep_detected, metadata = detect_sweep(
            df,
            equal_low_level=equal_low_data['level'],
            volume_threshold=self.volume_spike_min,
            volume_period=self.volume_lookback
        )
        
        return sweep_detected, metadata
    
    def _check_reclaim(self, df: pd.DataFrame, equal_low_data: dict) -> tuple:
        """Check if price reclaimed above equal low level"""
        if equal_low_data['level'] is None:
            return False, None
        
        reclaim_confirmed, metadata = detect_reclaim(
            df,
            level=equal_low_data['level'],
            strength_threshold=self.reclaim_strength_min,
            lookback=3
        )
        
        return reclaim_confirmed, metadata
    
    def _check_compression(self, df: pd.DataFrame) -> tuple:
        """Check if price is in compression"""
        is_compressed = detect_compression(
            df,
            lookback=self.compression_window,
            compression_threshold=self.compression_threshold
        )
        
        compression_score = calculate_compression_score(
            df,
            lookback=self.compression_window
        )
        
        return is_compressed, compression_score
    
    def _calculate_volume_metrics(self, df: pd.DataFrame) -> dict:
        """Calculate volume-related metrics"""
        if len(df) < self.volume_lookback:
            return {
                'avg_volume': 0,
                'current_ratio': 1.0
            }
        
        avg_vol = df['volume'].tail(self.volume_lookback).mean()
        
        vol_ratios = volume_ratio(df, period=self.volume_lookback)
        current_ratio = vol_ratios.iloc[-1] if not vol_ratios.empty else 1.0
        
        return {
            'avg_volume': avg_vol,
            'current_ratio': current_ratio
        }
