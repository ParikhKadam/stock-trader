"""
Technical indicator utilities for swing trading strategies
"""
import pandas as pd
import numpy as np
from typing import Optional
from swing_trader.utils.logging import logger


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: Lookback period for ATR calculation
        
    Returns:
        Series with ATR values
    """
    if len(df) < period:
        logger.warning(f"Insufficient data for ATR calculation: {len(df)} < {period}")
        return pd.Series(index=df.index, dtype=float)
    
    # Calculate True Range components
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))
    low_close = abs(df['low'] - df['close'].shift(1))
    
    # True Range is the maximum of the three
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # ATR is the moving average of True Range
    atr = true_range.rolling(window=period).mean()
    
    return atr


def detect_compression(
    df: pd.DataFrame, 
    lookback: int = 10, 
    compression_threshold: float = 0.75,
    atr_period: int = 14
) -> bool:
    """
    Detect price compression by comparing recent ATR to longer-term ATR
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of recent days to compare
        compression_threshold: Ratio threshold (e.g., 0.75 means recent ATR < 75% of past ATR)
        atr_period: Period for ATR calculation
        
    Returns:
        True if compression detected, False otherwise
    """
    if len(df) < atr_period + lookback:
        logger.debug(f"Insufficient data for compression detection: {len(df)} < {atr_period + lookback}")
        return False
    
    # Calculate ATR
    atr = calculate_atr(df, period=atr_period)
    
    if atr.isna().all():
        return False
    
    # Recent ATR (mean of last 'lookback' days)
    recent_atr = atr.tail(lookback).mean()
    
    # Past ATR (mean of all data before recent period)
    past_atr = atr.iloc[:-lookback].mean()
    
    if past_atr == 0 or pd.isna(recent_atr) or pd.isna(past_atr):
        return False
    
    # Check if recent ATR is significantly smaller than past ATR
    atr_ratio = recent_atr / past_atr
    is_compressed = atr_ratio < compression_threshold
    
    logger.debug(f"Compression check: recent_atr={recent_atr:.2f}, past_atr={past_atr:.2f}, "
                f"ratio={atr_ratio:.2f}, threshold={compression_threshold}, compressed={is_compressed}")
    
    return is_compressed


def calculate_compression_score(
    df: pd.DataFrame,
    lookback: int = 10,
    atr_period: int = 14
) -> Optional[float]:
    """
    Calculate compression score (recent ATR / past ATR)
    Lower values indicate stronger compression
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of recent days to compare
        atr_period: Period for ATR calculation
        
    Returns:
        Compression score or None if insufficient data
    """
    if len(df) < atr_period + lookback:
        return None
    
    atr = calculate_atr(df, period=atr_period)
    
    if atr.isna().all():
        return None
    
    recent_atr = atr.tail(lookback).mean()
    past_atr = atr.iloc[:-lookback].mean()
    
    if past_atr == 0 or pd.isna(recent_atr) or pd.isna(past_atr):
        return None
    
    return recent_atr / past_atr


def calculate_bollinger_width(
    df: pd.DataFrame, 
    period: int = 20, 
    num_std: float = 2.0
) -> pd.Series:
    """
    Calculate Bollinger Band width as percentage of price
    
    Args:
        df: DataFrame with 'close' column
        period: Lookback period for moving average and std dev
        num_std: Number of standard deviations for bands
        
    Returns:
        Series with Bollinger Band width as percentage
    """
    if len(df) < period:
        logger.warning(f"Insufficient data for Bollinger Band calculation: {len(df)} < {period}")
        return pd.Series(index=df.index, dtype=float)
    
    # Calculate middle band (SMA)
    middle_band = df['close'].rolling(window=period).mean()
    
    # Calculate standard deviation
    std = df['close'].rolling(window=period).std()
    
    # Calculate upper and lower bands
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)
    
    # Width as percentage of middle band
    width = ((upper_band - lower_band) / middle_band) * 100
    
    return width


def volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Calculate volume ratio (current volume / average volume)
    
    Args:
        df: DataFrame with 'volume' column
        period: Lookback period for average volume
        
    Returns:
        Series with volume ratios
    """
    if len(df) < period:
        logger.warning(f"Insufficient data for volume ratio calculation: {len(df)} < {period}")
        return pd.Series(index=df.index, dtype=float)
    
    avg_volume = df['volume'].rolling(window=period).mean()
    
    # Avoid division by zero
    ratio = df['volume'] / avg_volume.replace(0, np.nan)
    
    return ratio


def calculate_range_ratio(
    df: pd.DataFrame,
    recent_period: int = 5,
    comparison_period: int = 20
) -> Optional[float]:
    """
    Calculate recent range relative to historical range
    Lower values indicate tighter ranges (compression)
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        recent_period: Number of recent days for range calculation
        comparison_period: Historical period for comparison
        
    Returns:
        Range ratio or None if insufficient data
    """
    if len(df) < comparison_period:
        return None
    
    # Calculate daily ranges
    daily_range = df['high'] - df['low']
    
    # Recent average range
    recent_range = daily_range.tail(recent_period).mean()
    
    # Historical average range
    hist_range = daily_range.tail(comparison_period).mean()
    
    if hist_range == 0 or pd.isna(recent_range) or pd.isna(hist_range):
        return None
    
    return recent_range / hist_range


def calculate_body_strength(candle: pd.Series) -> float:
    """
    Calculate candle body strength (0 to 1)
    1.0 = body spans full high-low range
    0.0 = doji (no body)
    
    Args:
        candle: Series with 'open', 'high', 'low', 'close'
        
    Returns:
        Body strength ratio
    """
    full_range = candle['high'] - candle['low']
    
    if full_range == 0:
        return 0.0
    
    body = abs(candle['close'] - candle['open'])
    
    return body / full_range


def is_bullish_candle(candle: pd.Series) -> bool:
    """Check if candle is bullish (close > open)"""
    return candle['close'] > candle['open']


def is_hammer_pattern(candle: pd.Series, min_body_ratio: float = 0.3) -> bool:
    """
    Detect hammer/pin bar pattern (bullish reversal)
    Long lower wick, small body near top
    
    Args:
        candle: Series with OHLC data
        min_body_ratio: Minimum body size relative to full range
        
    Returns:
        True if hammer pattern detected
    """
    full_range = candle['high'] - candle['low']
    
    if full_range == 0:
        return False
    
    body = abs(candle['close'] - candle['open'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    
    # Long lower wick (at least 2x body)
    # Small upper wick
    # Body in upper portion
    has_long_lower_wick = lower_wick > (body * 2)
    has_small_upper_wick = upper_wick < (body * 0.5)
    body_in_upper_half = (max(candle['open'], candle['close']) - candle['low']) / full_range > 0.6
    
    return has_long_lower_wick and has_small_upper_wick and body_in_upper_half
