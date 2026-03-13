"""
Position tracking and lifecycle management
"""
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple
from swing_trader.core.models import Position, TradePlan, Trade
from swing_trader.utils.logging import logger


class PositionTracker:
    """
    Tracks a single position through its lifecycle:
    - Entry from trade plan
    - Updates with current price
    - Exit detection (stop/target/time-based)
    - Trade record generation
    """
    
    def __init__(self):
        """Initialize position tracker"""
        self.position: Optional[Position] = None
        self.trade_history = []
        self.entry_fee_pct = 0.001  # 0.1%
        self.exit_fee_pct = 0.001  # 0.1%
    
    @property
    def is_active(self) -> bool:
        """Check if position is currently active"""
        return self.position is not None
    
    def open_position(
        self,
        plan: TradePlan,
        fill_price: float,
        fill_date: datetime
    ) -> Position:
        """
        Open a position from a filled trade plan
        
        Args:
            plan: TradePlan that triggered
            fill_price: Actual fill price
            fill_date: Fill timestamp
            
        Returns:
            Created Position
        """
        if self.is_active:
            logger.warning(f"Attempted to open position while {self.position.symbol} is active")
            raise ValueError("Cannot open position - already have active position")
        
        position = Position(
            symbol=plan.symbol,
            entry_date=fill_date,
            entry_price=fill_price,
            quantity=plan.position_size,
            current_price=fill_price,
            stop=plan.stop,
            target=plan.target
        )
        
        self.position = position
        
        # Record entry trade
        entry_fee = fill_price * plan.position_size * self.entry_fee_pct
        entry_trade = Trade(
            date=fill_date.isoformat(),
            type='BUY',
            symbol=plan.symbol,
            quantity=plan.position_size,
            price=fill_price,
            fee=entry_fee,
            reason=f"Liquidity sweep entry @ {fill_price:.2f}"
        )
        self.trade_history.append(entry_trade)
        
        logger.info(f"Position opened: {plan.symbol} x{plan.position_size} @ {fill_price:.2f}")
        
        return position
    
    def update_position(self, current_data: pd.Series) -> None:
        """
        Update position with current market data
        
        Args:
            current_data: Current bar with OHLC data
        """
        if not self.is_active:
            return
        
        self.position.current_price = current_data['close']
    
    def should_exit(
        self,
        current_data: pd.Series,
        max_days: int = 30,
        stagnation_threshold_pct: float = 5.0
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Check if position should be exited
        
        Args:
            current_data: Current bar with OHLC data
            max_days: Maximum days to hold position
            stagnation_threshold_pct: Minimum progress % before triggering time exit
            
        Returns:
            (should_exit, reason, exit_price) tuple
        """
        if not self.is_active:
            return False, "", None
        
        # Update position first
        self.update_position(current_data)
        
        # Check stop loss hit
        if current_data['low'] <= self.position.stop:
            return True, "Stop loss hit", self.position.stop
        
        # Check target hit
        if current_data['high'] >= self.position.target:
            return True, "Target reached", self.position.target
        
        # Check time-based exit (stagnation)
        if self.position.days_held >= max_days:
            progress_pct = abs(self.position.unrealized_pnl_pct)
            if progress_pct < stagnation_threshold_pct:
                reason = f"Stagnation: {self.position.days_held} days with {progress_pct:.1f}% progress"
                return True, reason, current_data['close']
        
        return False, "", None
    
    def close_position(
        self,
        exit_price: float,
        exit_date: datetime,
        reason: str
    ) -> Trade:
        """
        Close the active position
        
        Args:
            exit_price: Exit price
            exit_date: Exit timestamp
            reason: Reason for exit
            
        Returns:
            Exit Trade record
        """
        if not self.is_active:
            raise ValueError("No active position to close")
        
        # Calculate P&L
        entry_cost = self.position.entry_price * self.position.quantity
        exit_value = exit_price * self.position.quantity
        gross_pnl = exit_value - entry_cost
        
        # Calculate fees
        exit_fee = exit_price * self.position.quantity * self.exit_fee_pct
        entry_fee = self.position.entry_price * self.position.quantity * self.entry_fee_pct
        total_fees = entry_fee + exit_fee
        
        net_pnl = gross_pnl - total_fees
        pnl_pct = (net_pnl / entry_cost) * 100
        
        # Record exit trade
        exit_trade = Trade(
            date=exit_date.isoformat(),
            type='SELL',
            symbol=self.position.symbol,
            quantity=self.position.quantity,
            price=exit_price,
            fee=exit_fee,
            reason=reason
        )
        self.trade_history.append(exit_trade)
        
        logger.info(
            f"Position closed: {self.position.symbol} @ {exit_price:.2f}, "
            f"P&L: ₹{net_pnl:.2f} ({pnl_pct:+.2f}%), held {self.position.days_held} days, "
            f"reason: {reason}"
        )
        
        # Clear position
        self.position = None
        
        return exit_trade
    
    def get_position_summary(self) -> Optional[dict]:
        """
        Get current position summary
        
        Returns:
            Dictionary with position details or None if no active position
        """
        if not self.is_active:
            return None
        
        return {
            'symbol': self.position.symbol,
            'entry_date': self.position.entry_date,
            'entry_price': self.position.entry_price,
            'current_price': self.position.current_price,
            'quantity': self.position.quantity,
            'unrealized_pnl': self.position.unrealized_pnl,
            'unrealized_pnl_pct': self.position.unrealized_pnl_pct,
            'days_held': self.position.days_held,
            'stop': self.position.stop,
            'target': self.position.target,
        }
