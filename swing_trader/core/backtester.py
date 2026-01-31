"""
Backtesting module for trading strategies
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
from .strategy import TradingStrategy
from .portfolio import Portfolio
from ..utils.logging import logger


class Backtester:
    """
    Backtesting engine for trading strategies
    """

    def __init__(self, strategy: TradingStrategy, initial_cash: float = 100000.0,
                 transaction_fee: float = 0.001, slippage: float = 0.002):
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.transaction_fee = transaction_fee
        self.slippage = slippage
        self.portfolio = None

    def run_backtest(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Run backtest on historical data

        Args:
            data: DataFrame with historical price data
            symbol: Stock symbol

        Returns:
            Dict with backtest results
        """
        logger.info(f"Starting backtest for {symbol} with strategy {self.strategy.name}")

        # Reset portfolio
        self.portfolio = Portfolio(self.initial_cash)

        # Prepare data
        data = data.copy()
        data.columns = [col.upper() for col in data.columns]
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # Generate signals
        signals_df = self.strategy.generate_signals(data.reset_index())
        if signals_df.empty:
            logger.error("No signals generated")
            return {'error': 'no_signals'}

        # Ensure signals are sorted by date
        signals_df['Date'] = pd.to_datetime(signals_df['Date'])
        signals_df = signals_df.sort_values('Date').set_index('Date')

        portfolio_values = []
        trades_executed = []

        # Iterate through all dates in data
        for date in data.index:
            current_price = data.loc[date, 'CLOSE']

            # Check if there's a signal on this date
            if date in signals_df.index:
                signal = signals_df.loc[date]
                sig = signal['signal']
                price = signal['price']
                reason = signal['reason']

                if pd.notna(price):
                    # Adjust price for slippage
                    if sig == 'buy':
                        adjusted_price = price * (1 + self.slippage)
                    elif sig == 'sell':
                        adjusted_price = price * (1 - self.slippage)
                    else:
                        adjusted_price = price

                    # Execute trade
                    if sig == 'buy' and self.portfolio.positions.get(symbol, 0) == 0:
                        # Buy max shares
                        max_shares = int(self.portfolio.cash // (adjusted_price * (1 + self.transaction_fee)))
                        if max_shares > 0:
                            success = self.portfolio.buy(symbol, max_shares, adjusted_price)
                            if success:
                                fee = max_shares * adjusted_price * self.transaction_fee
                                self.portfolio.cash -= fee
                                trades_executed.append({
                                    'date': date,
                                    'type': 'BUY',
                                    'symbol': symbol,
                                    'quantity': max_shares,
                                    'price': adjusted_price,
                                    'fee': fee,
                                    'reason': reason
                                })
                                logger.info(f"Executed BUY: {max_shares} {symbol} at {adjusted_price} on {date}")

                    elif sig == 'sell' and self.portfolio.positions.get(symbol, 0) > 0:
                        # Sell all shares
                        shares = self.portfolio.positions[symbol]
                        success = self.portfolio.sell(symbol, shares, adjusted_price)
                        if success:
                            fee = shares * adjusted_price * self.transaction_fee
                            self.portfolio.cash -= fee
                            trades_executed.append({
                                'date': date,
                                'type': 'SELL',
                                'symbol': symbol,
                                'quantity': shares,
                                'price': adjusted_price,
                                'fee': fee,
                                'reason': reason
                            })
                            logger.info(f"Executed SELL: {shares} {symbol} at {adjusted_price} on {date}")

            # Record portfolio value daily
            current_prices = {symbol: current_price}
            portfolio_value = self.portfolio.get_value(current_prices)
            portfolio_values.append({'date': date, 'value': portfolio_value})

        # Calculate metrics
        portfolio_df = pd.DataFrame(portfolio_values)
        if portfolio_df.empty:
            return {'error': 'no_portfolio_data'}

        portfolio_df.set_index('date', inplace=True)
        returns = portfolio_df['value'].pct_change().dropna()

        total_return = (portfolio_df['value'].iloc[-1] - self.initial_cash) / self.initial_cash
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        max_drawdown = (portfolio_df['value'] / portfolio_df['value'].cummax() - 1).min()

        # Benchmark: buy and hold
        initial_price = data['CLOSE'].iloc[0]
        final_price = data['CLOSE'].iloc[-1]
        benchmark_return = (final_price - initial_price) / initial_price

        logger.info(f"Backtest completed. Total return: {total_return:.2%}, Sharpe: {sharpe_ratio:.2f}, Max DD: {max_drawdown:.2%}")

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'benchmark_return': benchmark_return,
            'trades': trades_executed,
            'portfolio_value_over_time': portfolio_df['value'],
            'signals': signals_df.reset_index()
        }