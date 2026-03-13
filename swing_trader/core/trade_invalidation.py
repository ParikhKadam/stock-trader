"""
Trade plan and position invalidation rules
Structural conditions that void a setup
"""
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional
from swing_trader.core.models import TradePlan, Position
from swing_trader.utils.logging import logger


class InvalidationRules:
    """
    Checks structural invalidation conditions for trade plans and positions
    These are conditions that void the original setup thesis
    """
    
    def __init__(
        self,
        price_breach_threshold_pct: float = 0.02,
        volatility_expansion_threshold: float = 2.0,
        stagnation_days: int = 10,
        stagnation_progress_min_pct: float = 5.0
    ):
        """
        Initialize invalidation rules
        
        Args:
            price_breach_threshold_pct: % above entry that invalidates setup (default 2%)
            volatility_expansion_threshold: ATR expansion multiplier for invalidation
            stagnation_days: Days of no progress before invalidation
            stagnation_progress_min_pct: Minimum progress % to avoid stagnation flag
        """
        self.price_breach_threshold_pct = price_breach_threshold_pct
        self.volatility_expansion_threshold = volatility_expansion_threshold
        self.stagnation_days = stagnation_days
        self.stagnation_progress_min_pct = stagnation_progress_min_pct
        
        logger.debug(f"InvalidationRules initialized: price_breach={price_breach_threshold_pct:.1%}, "
                    f"vol_expansion={volatility_expansion_threshold}x, stagnation={stagnation_days}d")
    
    def check_plan_invalidation(
        self,
        plan: TradePlan,
        current_data: pd.Series,
        historical_data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, str]:
        """
        Check if a pending trade plan should be invalidated
        
        Args:
            plan: TradePlan to check
            current_data: Current bar data
            historical_data: Full historical data for context (optional)
            
        Returns:
            (is_invalid, reason) tuple
        """
        # Can only invalidate pending plans
        if plan.status != "pending":
            return False, ""
        
        # Check 1: Price moved significantly above entry level
        # This means we "missed" the entry and setup is compromised
        if current_data['close'] > plan.entry * (1 + self.price_breach_threshold_pct):
            breach_pct = ((current_data['close'] - plan.entry) / plan.entry) * 100
            reason = f"Price breached {breach_pct:.1f}% above entry - setup invalidated"
            logger.warning(reason)
            return True, reason
        
        # Check 2: Price strongly violated below stop before entry triggered
        # This suggests the setup was wrong
        if current_data['close'] < plan.stop * 0.98:  # 2% below stop
            reason = f"Price collapsed below stop level before entry - setup failed"
            logger.warning(reason)
            return True, reason
        
        # Check 3: Volatility explosion (if historical data available)
        if historical_data is not None and len(historical_data) >= 20:
            from swing_trader.utils.indicators import calculate_atr
            
            atr_series = calculate_atr(historical_data, period=14)
            if not atr_series.empty:
                current_atr = atr_series.iloc[-1]
                avg_atr = atr_series.iloc[-20:-1].mean()
                
                if current_atr > avg_atr * self.volatility_expansion_threshold:
                    reason = f"Volatility spike: ATR {current_atr:.2f} vs avg {avg_atr:.2f}"
                    logger.warning(reason)
                    return True, reason
        
        return False, ""
    
    def check_position_invalidation(
        self,
        position: Position,
        current_data: pd.Series,
        current_date: datetime
    ) -> Tuple[bool, str]:
        """
        Check if an active position should be invalidated (emergency exit)
        
        Args:
            position: Active position
            current_data: Current bar data
            current_date: Current date
            
        Returns:
            (is_invalid, reason) tuple
        """
        # Check 1: Gap down below stop
        # If price gaps significantly below stop, exit immediately at market
        if current_data['open'] < position.stop * 0.98:  # 2% below stop
            gap_pct = ((position.stop - current_data['open']) / position.stop) * 100
            reason = f"Gap down {gap_pct:.1f}% below stop - emergency exit"
            logger.error(reason)
            return True, reason
        
        # Check 2: Massive volume spike with price decline
        # Could indicate panic selling or major news
        if 'volume' in current_data and hasattr(position, 'entry_volume'):
            if (current_data['volume'] > position.entry_volume * 3 and
                current_data['close'] < position.entry_price):
                reason = "Panic volume detected with price decline"
                logger.warning(reason)
                return True, reason
        
        # Check 3: Stagnation - not moving toward target for extended period
        days_held = (current_date - position.entry_date).days
        if days_held >= self.stagnation_days:
            progress_pct = abs(position.unrealized_pnl_pct)
            
            if progress_pct < self.stagnation_progress_min_pct:
                reason = f"Stagnation: {days_held} days with only {progress_pct:.1f}% progress"
                logger.info(reason)
                return True, reason
        
        # Check 4: Break of structure - price closing below entry after being profitable
        # This suggests trend reversal
        if (position.unrealized_pnl > 0 and  # Was profitable
            current_data['close'] < position.entry_price * 0.99):  # Now below entry
            reason = "Break of structure: profitable trade reversed below entry"
            logger.warning(reason)
            return True, reason
        
        return False, ""
    
    def should_adjust_stop(
        self,
        position: Position,
        current_data: pd.Series
    ) -> Tuple[bool, Optional[float], str]:
        """
        Check if stop should be trailed/adjusted
        
        Args:
            position: Active position
            current_data: Current bar data
            
        Returns:
            (should_adjust, new_stop_price, reason) tuple
        """
        # Trail stop to break-even once trade is 1R profitable
        risk_amount = position.entry_price - position.stop
        target_for_trail = position.entry_price + risk_amount  # 1R profit
        
        if current_data['high'] >= target_for_trail:
            # Move stop to break-even (entry price)
            if position.stop < position.entry_price:
                new_stop = position.entry_price
                reason = "Trailing stop to break-even after 1R profit"
                logger.info(reason)
                return True, new_stop, reason
        
        # Could add more sophisticated trailing logic here
        # e.g., trail by ATR, by swing lows, etc.
        
        return False, None, ""
