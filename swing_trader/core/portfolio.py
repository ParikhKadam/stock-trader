"""
Portfolio management module
"""
from typing import Dict, List
import pandas as pd
from ..utils.logging import logger


class Portfolio:
    """
    Simple portfolio class for managing positions
    """

    def __init__(self, initial_cash: float = 100000.0):
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.trades: List[Dict] = []  # trade history

    def buy(self, symbol: str, quantity: int, price: float) -> bool:
        """Buy shares"""
        cost = quantity * price
        if cost > self.cash:
            logger.warning(f"Insufficient cash for {symbol}: need {cost}, have {self.cash}")
            return False

        self.cash -= cost
        self.positions[symbol] = self.positions.get(symbol, 0) + quantity
        self.trades.append({
            'type': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'timestamp': pd.Timestamp.now()
        })
        logger.info(f"Bought {quantity} {symbol} at {price}")
        return True

    def sell(self, symbol: str, quantity: int, price: float) -> bool:
        """Sell shares"""
        if self.positions.get(symbol, 0) < quantity:
            logger.warning(f"Insufficient shares for {symbol}: have {self.positions.get(symbol, 0)}, need {quantity}")
            return False

        proceeds = quantity * price
        self.cash += proceeds
        self.positions[symbol] -= quantity
        if self.positions[symbol] == 0:
            del self.positions[symbol]

        self.trades.append({
            'type': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'timestamp': pd.Timestamp.now()
        })
        logger.info(f"Sold {quantity} {symbol} at {price}")
        return True

    def get_value(self, current_prices: Dict[str, float]) -> float:
        """Get total portfolio value"""
        position_value = sum(
            qty * current_prices.get(symbol, 0)
            for symbol, qty in self.positions.items()
        )
        return self.cash + position_value

    def get_positions(self) -> Dict[str, int]:
        """Get current positions"""
        return self.positions.copy()