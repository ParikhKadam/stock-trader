"""
Pydantic models for the swing trader application
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


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