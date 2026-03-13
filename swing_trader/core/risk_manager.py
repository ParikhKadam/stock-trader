"""
Risk management for trading operations
"""
import pandas as pd
from typing import Optional
from swing_trader.core.models import TradePlan, PortfolioState
from swing_trader.utils.logging import logger


class RiskManager:
    """
    Manages risk parameters and validates trade plans against risk limits
    """
    
    def __init__(
        self,
        max_risk_per_trade_pct: float = 0.02,
        max_total_risk_pct: float = 0.05,
        min_reward_to_risk: float = 2.0,
        min_position_value: float = 1000.0
    ):
        """
        Initialize risk manager
        
        Args:
            max_risk_per_trade_pct: Maximum risk per single trade (default 2%)
            max_total_risk_pct: Maximum total portfolio risk (default 5%)
            min_reward_to_risk: Minimum R:R ratio to accept trade
            min_position_value: Minimum position value in currency
        """
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_total_risk_pct = max_total_risk_pct
        self.min_reward_to_risk = min_reward_to_risk
        self.min_position_value = min_position_value
        
        logger.info(f"RiskManager initialized: max_risk_per_trade={max_risk_per_trade_pct:.1%}, "
                   f"max_total_risk={max_total_risk_pct:.1%}, min_R:R={min_reward_to_risk}")
    
    def calculate_position_size(
        self,
        capital: float,
        entry: float,
        stop: float,
        risk_pct: Optional[float] = None
    ) -> tuple[int, dict]:
        """
        Calculate position size based on risk parameters
        
        Args:
            capital: Available capital
            entry: Entry price
            stop: Stop loss price
            risk_pct: Override default risk percentage
            
        Returns:
            (position_size, metadata) tuple
        """
        if risk_pct is None:
            risk_pct = self.max_risk_per_trade_pct
        
        # Ensure risk percentage doesn't exceed limit
        risk_pct = min(risk_pct, self.max_risk_per_trade_pct)
        
        # Calculate risk per share
        risk_per_share = entry - stop
        
        if risk_per_share <= 0:
            logger.error(f"Invalid risk: entry={entry}, stop={stop}")
            return 0, {'error': 'Invalid entry/stop prices'}
        
        # Calculate max risk amount
        max_risk_amount = capital * risk_pct
        
        # Calculate position size
        position_size = int(max_risk_amount / risk_per_share)
        
        # Check affordability
        position_value = entry * position_size
        if position_value > capital:
            # Reduce position size to fit capital
            position_size = int(capital / entry)
            actual_risk_amount = position_size * risk_per_share
            actual_risk_pct = (actual_risk_amount / capital) * 100
        else:
            actual_risk_amount = max_risk_amount
            actual_risk_pct = risk_pct * 100
        
        # Check minimum position value
        if position_value < self.min_position_value:
            logger.warning(f"Position value ₹{position_value:.2f} below minimum ₹{self.min_position_value:.2f}")
        
        metadata = {
            'position_size': position_size,
            'position_value': position_value,
            'risk_amount': actual_risk_amount,
            'risk_pct': actual_risk_pct,
            'risk_per_share': risk_per_share,
            'affordable': position_value <= capital,
            'meets_minimum': position_value >= self.min_position_value
        }
        
        logger.debug(f"Position size calculated: {position_size} shares, "
                    f"value=₹{position_value:.2f}, risk=₹{actual_risk_amount:.2f} ({actual_risk_pct:.2f}%)")
        
        return position_size, metadata
    
    def validate_plan(
        self,
        plan: TradePlan,
        portfolio_state: Optional[PortfolioState] = None
    ) -> tuple[bool, str]:
        """
        Validate trade plan against risk parameters
        
        Args:
            plan: TradePlan to validate
            portfolio_state: Current portfolio state (optional)
            
        Returns:
            (is_valid, reason) tuple
        """
        # Check R:R ratio
        if plan.reward_to_risk < self.min_reward_to_risk:
            return False, f"R:R {plan.reward_to_risk:.2f} below minimum {self.min_reward_to_risk}"
        
        # Check position value
        position_value = plan.entry * plan.position_size
        if position_value < self.min_position_value:
            return False, f"Position value ₹{position_value:.2f} below minimum ₹{self.min_position_value:.2f}"
        
        # If portfolio state provided, check total risk
        if portfolio_state:
            # Calculate new total risk
            new_risk_amount = plan.risk_amount
            current_total_risk = sum(
                abs(pos.entry_price - pos.stop) * pos.quantity
                for pos in portfolio_state.active_positions.values()
            )
            
            total_risk = current_total_risk + new_risk_amount
            total_risk_pct = (total_risk / portfolio_state.equity) * 100
            
            if total_risk_pct > self.max_total_risk_pct * 100:
                return False, f"Total portfolio risk {total_risk_pct:.2f}% exceeds limit {self.max_total_risk_pct * 100:.2f}%"
        
        return True, "Plan validated"
    
    def check_market_alignment(
        self,
        df: pd.DataFrame,
        index_df: Optional[pd.DataFrame] = None,
        crash_threshold_pct: float = -7.0,
        lookback_days: int = 14
    ) -> tuple[bool, str]:
        """
        Check if broader market conditions support taking new trades
        
        Args:
            df: Symbol's price data
            index_df: Index/benchmark data (optional)
            crash_threshold_pct: Market decline threshold to avoid trades
            lookback_days: Days to check for market decline
            
        Returns:
            (is_aligned, reason) tuple
        """
        # If no index data, just check symbol's trend
        if index_df is None or len(index_df) < lookback_days:
            # Check if symbol is in strong downtrend
            if len(df) >= lookback_days:
                price_change_pct = ((df['close'].iloc[-1] - df['close'].iloc[-lookback_days]) / 
                                   df['close'].iloc[-lookback_days]) * 100
                
                if price_change_pct < crash_threshold_pct:
                    return False, f"Symbol in severe downtrend: {price_change_pct:+.1f}% over {lookback_days}d"
            
            return True, "No market data, symbol trend acceptable"
        
        # Check index decline
        index_change_pct = ((index_df['close'].iloc[-1] - index_df['close'].iloc[-lookback_days]) / 
                           index_df['close'].iloc[-lookback_days]) * 100
        
        if index_change_pct < crash_threshold_pct:
            return False, f"Market decline: {index_change_pct:+.1f}% over {lookback_days}d"
        
        return True, "Market conditions acceptable"
    
    def assess_gap_risk(
        self,
        plan: TradePlan,
        current_close: float
    ) -> tuple[str, str]:
        """
        Assess gap risk between current price and entry level
        
        Args:
            plan: TradePlan with entry price
            current_close: Current closing price
            
        Returns:
            (risk_level, message) tuple - risk_level: 'low'|'medium'|'high'
        """
        gap_pct = abs(current_close - plan.entry) / plan.entry * 100
        
        if gap_pct < 1.0:
            return 'low', f"Minimal gap risk: {gap_pct:.2f}%"
        elif gap_pct < 2.0:
            return 'medium', f"Moderate gap risk: {gap_pct:.2f}% - monitor overnight news"
        else:
            return 'high', f"High gap risk: {gap_pct:.2f}% - consider limit order adjustments"
