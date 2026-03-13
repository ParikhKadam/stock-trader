"""
Liquidity detection primitives for swing trading strategies
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Optional
from swing_trader.utils.logging import logger
from swing_trader.utils.indicators import calculate_body_strength, volume_ratio


def find_swing_lows(df: pd.DataFrame, order: int = 3) -> List[Tuple[pd.Timestamp, float]]:
    """
    Find swing lows (pivots) where the low is the minimum over 'order' bars on each side
    
    Args:
        df: DataFrame with 'low' column and datetime index
        order: Number of bars on each side to compare
        
    Returns:
        List of (timestamp, price) tuples for swing lows
    """
    if len(df) < (2 * order + 1):
        logger.debug(f"Insufficient data for swing low detection: {len(df)} < {2 * order + 1}")
        return []
    
    swing_lows = []
    
    # Check each potential pivot point (skip first and last 'order' bars)
    for i in range(order, len(df) - order):
        current_low = df['low'].iloc[i]
        
        # Get window of bars around current bar
        window_lows = df['low'].iloc[i - order:i + order + 1]
        
        # Check if current bar is the minimum in the window
        if current_low == window_lows.min():
            timestamp = df.index[i]
            swing_lows.append((timestamp, current_low))
    
    logger.debug(f"Found {len(swing_lows)} swing lows with order={order}")
    return swing_lows


def find_swing_highs(df: pd.DataFrame, order: int = 3) -> List[Tuple[pd.Timestamp, float]]:
    """
    Find swing highs (pivots) where the high is the maximum over 'order' bars on each side
    
    Args:
        df: DataFrame with 'high' column and datetime index
        order: Number of bars on each side to compare
        
    Returns:
        List of (timestamp, price) tuples for swing highs
    """
    if len(df) < (2 * order + 1):
        logger.debug(f"Insufficient data for swing high detection: {len(df)} < {2 * order + 1}")
        return []
    
    swing_highs = []
    
    for i in range(order, len(df) - order):
        current_high = df['high'].iloc[i]
        window_highs = df['high'].iloc[i - order:i + order + 1]
        
        if current_high == window_highs.max():
            timestamp = df.index[i]
            swing_highs.append((timestamp, current_high))
    
    logger.debug(f"Found {len(swing_highs)} swing highs with order={order}")
    return swing_highs


def detect_equal_levels(
    levels: List[Tuple[pd.Timestamp, float]], 
    tolerance_pct: float = 0.003,
    min_occurrences: int = 2
) -> Dict[float, List[Tuple[pd.Timestamp, float]]]:
    """
    Cluster price levels within tolerance to find equal lows/highs
    
    Args:
        levels: List of (timestamp, price) tuples
        tolerance_pct: Price tolerance as decimal (e.g., 0.003 = 0.3%)
        min_occurrences: Minimum number of touches to consider as equal level
        
    Returns:
        Dictionary mapping base_level -> list of (timestamp, price) tuples
    """
    if not levels:
        return {}
    
    # Sort by price
    sorted_levels = sorted(levels, key=lambda x: x[1])
    
    clusters = {}
    visited = set()
    
    for i, (ts1, price1) in enumerate(sorted_levels):
        if i in visited:
            continue
        
        # Start a new cluster with this price as base
        cluster = [(ts1, price1)]
        visited.add(i)
        
        # Find all prices within tolerance of this base price
        for j, (ts2, price2) in enumerate(sorted_levels):
            if j <= i or j in visited:
                continue
            
            # Check if within tolerance
            price_diff = abs(price2 - price1) / price1
            if price_diff <= tolerance_pct:
                cluster.append((ts2, price2))
                visited.add(j)
        
        # Only keep clusters with minimum occurrences
        if len(cluster) >= min_occurrences:
            # Use average price as the base level
            base_level = sum(p for _, p in cluster) / len(cluster)
            clusters[base_level] = cluster
    
    logger.debug(f"Found {len(clusters)} equal level clusters from {len(levels)} total levels")
    for base, touches in clusters.items():
        logger.debug(f"  Level {base:.2f}: {len(touches)} touches")
    
    return clusters


def detect_sweep(
    df: pd.DataFrame,
    equal_low_level: float,
    volume_threshold: float = 1.5,
    volume_period: int = 20
) -> Tuple[bool, Optional[Dict]]:
    """
    Detect if latest candle swept below equal low but closed above it
    with volume confirmation
    
    Args:
        df: DataFrame with OHLC and volume data
        equal_low_level: Price level of equal lows
        volume_threshold: Minimum volume ratio for confirmation
        volume_period: Period for average volume calculation
        
    Returns:
        (sweep_detected, metadata_dict) tuple
    """
    if len(df) < volume_period + 1:
        return False, None
    
    latest_candle = df.iloc[-1]
    
    # Check if low swept below level but close is above
    swept_below = latest_candle['low'] < equal_low_level
    closed_above = latest_candle['close'] > equal_low_level
    
    if not (swept_below and closed_above):
        return False, None
    
    # Calculate volume ratio
    vol_ratios = volume_ratio(df, period=volume_period)
    current_vol_ratio = vol_ratios.iloc[-1]
    
    # Check volume confirmation
    volume_confirmed = current_vol_ratio >= volume_threshold
    
    # Calculate body strength
    body_strength = calculate_body_strength(latest_candle)
    
    metadata = {
        'sweep_low': latest_candle['low'],
        'close_price': latest_candle['close'],
        'volume_ratio': current_vol_ratio,
        'volume_confirmed': volume_confirmed,
        'body_strength': body_strength,
        'timestamp': latest_candle.name if hasattr(latest_candle, 'name') else None
    }
    
    # Both price action AND volume must confirm
    sweep_detected = swept_below and closed_above and volume_confirmed
    
    logger.debug(f"Sweep check: swept={swept_below}, closed_above={closed_above}, "
                f"vol_ratio={current_vol_ratio:.2f}, confirmed={sweep_detected}")
    
    return sweep_detected, metadata


def detect_reclaim(
    df: pd.DataFrame,
    level: float,
    strength_threshold: float = 0.6,
    lookback: int = 3
) -> Tuple[bool, Optional[Dict]]:
    """
    Verify that price reclaimed above level with strong candle body
    
    Args:
        df: DataFrame with OHLC data
        level: Price level to check reclaim above
        strength_threshold: Minimum body strength (0-1) for confirmation
        lookback: Number of recent candles to check
        
    Returns:
        (reclaim_confirmed, metadata_dict) tuple
    """
    if len(df) < lookback:
        return False, None
    
    recent_candles = df.tail(lookback)
    
    reclaim_confirmed = False
    best_strength = 0.0
    reclaim_candle = None
    
    for idx, candle in recent_candles.iterrows():
        # Check if candle closed above level
        if candle['close'] > level:
            body_strength = calculate_body_strength(candle)
            
            # Strong bullish close
            if body_strength >= strength_threshold and candle['close'] > candle['open']:
                reclaim_confirmed = True
                if body_strength > best_strength:
                    best_strength = body_strength
                    reclaim_candle = candle
    
    if reclaim_confirmed and reclaim_candle is not None:
        metadata = {
            'reclaim_price': reclaim_candle['close'],
            'body_strength': best_strength,
            'is_bullish': reclaim_candle['close'] > reclaim_candle['open'],
            'timestamp': reclaim_candle.name if hasattr(reclaim_candle, 'name') else None
        }
        
        logger.debug(f"Reclaim confirmed: close={metadata['reclaim_price']:.2f}, "
                    f"strength={best_strength:.2f}")
        
        return True, metadata
    
    return False, None


def find_most_recent_equal_lows(
    df: pd.DataFrame,
    swing_order: int = 3,
    tolerance_pct: float = 0.003,
    min_occurrences: int = 2,
    recency_window: int = 60
) -> Optional[Dict]:
    """
    Find the most recent equal low pattern in the data
    
    Args:
        df: DataFrame with OHLC data
        swing_order: Order for swing low detection
        tolerance_pct: Tolerance for equal level clustering
        min_occurrences: Minimum touches required
        recency_window: Only consider swing lows within this many bars
        
    Returns:
        Dictionary with equal low info or None if not found
    """
    # Find all swing lows
    swing_lows = find_swing_lows(df, order=swing_order)
    
    if len(swing_lows) < min_occurrences:
        return None
    
    # Filter to recent swing lows only
    if recency_window and len(df) > recency_window:
        cutoff_date = df.index[-recency_window]
        swing_lows = [(ts, price) for ts, price in swing_lows if ts >= cutoff_date]
    
    # Find equal level clusters
    equal_level_clusters = detect_equal_levels(
        swing_lows,
        tolerance_pct=tolerance_pct,
        min_occurrences=min_occurrences
    )
    
    if not equal_level_clusters:
        return None
    
    # Get the cluster with the most recent touch
    most_recent_cluster = None
    most_recent_time = None
    
    for base_level, touches in equal_level_clusters.items():
        latest_touch_time = max(ts for ts, _ in touches)
        
        if most_recent_time is None or latest_touch_time > most_recent_time:
            most_recent_time = latest_touch_time
            most_recent_cluster = {
                'base_level': base_level,
                'touches': touches,
                'count': len(touches),
                'latest_touch': latest_touch_time
            }
    
    return most_recent_cluster


def calculate_current_range(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate current average trading range
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        period: Lookback period
        
    Returns:
        Average range over period
    """
    if len(df) < period:
        period = len(df)
    
    ranges = df['high'] - df['low']
    return ranges.tail(period).mean()
