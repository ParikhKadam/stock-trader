"""
Pydantic models for the swing trader application
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
import pandas as pd


class TradingSignal(BaseModel):
    """
    Standardized trading signal response
    """
    signal: str = Field(..., description="Trading signal: 'buy', 'sell', or 'hold'")
    price: Optional[float] = Field(None, description="Execution price (None for hold signals)")
    reason: str = Field(..., description="Reason for the signal")

    def __str__(self) -> str:
        return f"Signal({self.signal}, price={self.price}, reason='{self.reason}')"


class Trade(BaseModel):
    """Model for a single executed trade"""
    date: str  # ISO format datetime string
    type: str  # 'BUY' or 'SELL'
    symbol: str
    quantity: int
    price: float
    fee: float
    reason: str


class BacktestResults(BaseModel):
    """Model for backtest results"""
    total_return: float = Field(..., description="Total portfolio return as decimal")
    sharpe_ratio: float = Field(..., description="Sharpe ratio (annualized)")
    max_drawdown: float = Field(..., description="Maximum drawdown as decimal")
    benchmark_return: float = Field(..., description="Buy-and-hold benchmark return as decimal")
    trades: List[Trade] = Field(default_factory=list, description="List of executed trades")
    portfolio_value_over_time: List[float] = Field(..., description="Portfolio values over time")
    signals: Optional[Dict[str, Any]] = Field(None, description="Trading signals")
    pending_plans_count: Optional[int] = Field(None, description="Number of pending trade plans")
    fill_rate: Optional[float] = Field(None, description="Percentage of plans that filled")
    avg_days_to_fill: Optional[float] = Field(None, description="Average days for plan to fill")
    expired_plan_count: Optional[int] = Field(None, description="Number of expired plans")


class TradePlan(BaseModel):
    """Model for a pending trade plan with expiry and invalidation logic"""
    symbol: str = Field(..., description="Trading symbol")
    entry: float = Field(..., description="Entry price level")
    stop: float = Field(..., description="Stop loss price")
    target: float = Field(..., description="Target price")
    position_size: int = Field(..., description="Number of shares/units")
    expiry_days: int = Field(default=5, description="Days until plan expires")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Plan creation timestamp")
    status: str = Field(default="pending", description="Plan status: pending/filled/expired/cancelled")
    invalidation_reason: Optional[str] = Field(None, description="Reason for invalidation if cancelled")
    filled_at: Optional[datetime] = Field(None, description="Timestamp when plan was filled")
    
    @field_validator('entry', 'stop', 'target')
    @classmethod
    def validate_positive_prices(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return v
    
    @field_validator('position_size')
    @classmethod
    def validate_position_size(cls, v):
        if v <= 0:
            raise ValueError("Position size must be positive")
        return v
    
    def model_post_init(self, __context):
        """Validate price relationships after initialization"""
        if self.entry <= self.stop:
            raise ValueError(f"Entry ({self.entry}) must be greater than stop ({self.stop})")
        if self.target <= self.entry:
            raise ValueError(f"Target ({self.target}) must be greater than entry ({self.entry})")
    
    @property
    def reward_to_risk(self) -> float:
        """Calculate reward-to-risk ratio"""
        risk = self.entry - self.stop
        reward = self.target - self.entry
        return reward / risk if risk > 0 else 0.0
    
    @property
    def risk_amount(self) -> float:
        """Total risk amount in currency"""
        return (self.entry - self.stop) * self.position_size
    
    def is_expired(self, current_date: datetime = None) -> bool:
        """Check if plan has expired"""
        if self.status != "pending":
            return False
        current = current_date or datetime.utcnow()
        return (current - self.created_at).days >= self.expiry_days
    
    def is_valid(self, current_data: pd.Series) -> bool:
        """Check if plan is still structurally valid (no invalidation conditions)"""
        if self.status != "pending":
            return False
        
        # Check if price broke significantly above entry before triggering
        # This would invalidate the setup (missed opportunity)
        if current_data['close'] > self.entry * 1.02:  # 2% above entry
            return False
        
        return True


class Position(BaseModel):
    """Model for an active trading position"""
    symbol: str = Field(..., description="Trading symbol")
    entry_date: datetime = Field(..., description="Position entry timestamp")
    entry_price: float = Field(..., description="Position entry price")
    quantity: int = Field(..., description="Number of shares/units held")
    current_price: float = Field(..., description="Current market price")
    stop: float = Field(..., description="Stop loss price")
    target: float = Field(..., description="Target price")
    
    @property
    def cost_basis(self) -> float:
        """Total cost of position"""
        return self.entry_price * self.quantity
    
    @property
    def current_value(self) -> float:
        """Current market value"""
        return self.current_price * self.quantity
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss"""
        return (self.current_price - self.entry_price) * self.quantity
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized profit/loss as percentage"""
        return ((self.current_price - self.entry_price) / self.entry_price) * 100
    
    @property
    def days_held(self) -> int:
        """Number of days position has been held"""
        return (datetime.utcnow() - self.entry_date).days
    
    def should_exit(self, current_data: pd.Series, max_days: int = 30) -> tuple[bool, str]:
        """
        Check if position should be exited
        Returns: (should_exit, reason)
        """
        # Stop loss hit
        if current_data['low'] <= self.stop:
            return True, "Stop loss hit"
        
        # Target hit
        if current_data['high'] >= self.target:
            return True, "Target reached"
        
        # Time-based exit (stagnation)
        if self.days_held >= max_days:
            progress_pct = abs(self.unrealized_pnl_pct)
            if progress_pct < 5:  # Less than 5% progress in max_days
                return True, f"Stagnation: {self.days_held} days with minimal movement"
        
        return False, ""


class PortfolioState(BaseModel):
    """Model for overall portfolio state"""
    cash: float = Field(..., description="Available cash")
    equity: float = Field(..., description="Total equity (cash + positions)")
    active_positions: Dict[str, Position] = Field(default_factory=dict, description="Active positions by symbol")
    
    @property
    def total_risk_pct(self) -> float:
        """Total portfolio risk as percentage"""
        if self.equity <= 0:
            return 0.0
        
        total_risk = sum(
            abs(pos.entry_price - pos.stop) * pos.quantity 
            for pos in self.active_positions.values()
        )
        return (total_risk / self.equity) * 100
    
    @property
    def position_count(self) -> int:
        """Number of active positions"""
        return len(self.active_positions)
    
    def has_position(self, symbol: str) -> bool:
        """Check if symbol has active position"""
        return symbol in self.active_positions


class LiquiditySwingState(BaseModel):
    """Model for liquidity swing strategy state"""
    equal_low_count: int = Field(..., description="Number of equal lows detected")
    equal_low_level: Optional[float] = Field(None, description="Price level of equal lows")
    sweep_detected: bool = Field(default=False, description="Whether liquidity sweep was detected")
    reclaim_confirmed: bool = Field(default=False, description="Whether price reclaimed above sweep level")
    compression_detected: bool = Field(default=False, description="Whether price compression was detected")
    current_range_size: float = Field(..., description="Current price range (high - low)")
    avg_volume_20d: float = Field(..., description="20-day average volume")
    volume_spike_ratio: float = Field(default=1.0, description="Current volume / average volume")
    sweep_low: Optional[float] = Field(None, description="Lowest point during sweep")
    reclaim_body_strength: Optional[float] = Field(None, description="Candle body strength on reclaim (0-1)")
    compression_score: Optional[float] = Field(None, description="Compression strength (recent ATR / past ATR)")
    
    def is_tradeable(self) -> bool:
        """Check if state meets minimum criteria for trade setup"""
        return (
            self.equal_low_count >= 2 and
            self.sweep_detected and
            self.reclaim_confirmed and
            self.compression_detected
        )
    
    def confidence_score(self) -> float:
        """
        Calculate setup confidence score (0-1)
        Higher is better
        """
        score = 0.0
        
        # Equal lows contribution (max 0.3)
        if self.equal_low_count >= 2:
            score += min(0.1 * self.equal_low_count, 0.3)
        
        # Volume spike contribution (max 0.3)
        if self.volume_spike_ratio > 1.5:
            score += min((self.volume_spike_ratio - 1.0) * 0.2, 0.3)
        
        # Reclaim strength contribution (max 0.2)
        if self.reclaim_body_strength:
            score += self.reclaim_body_strength * 0.2
        
        # Compression contribution (max 0.2)
        if self.compression_score:
            compression_strength = 1.0 - self.compression_score  # Lower ATR ratio = stronger compression
            score += min(compression_strength, 0.2)
        
        return min(score, 1.0)