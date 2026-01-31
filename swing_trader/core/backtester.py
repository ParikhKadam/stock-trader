"""
Backtesting module for trading strategies
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from .strategy import TradingStrategy, TradingSignal
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

        # Reset portfolio and strategy state
        self.portfolio = Portfolio(self.initial_cash)
        self.strategy.reset_state()

        # Prepare data
        data = self._prepare_data(data)

        # Generate signals
        signals = self._generate_signals(data)

        # Execute backtest
        portfolio_values, trades_executed = self._execute_backtest(data, signals, symbol)

        # Calculate metrics
        metrics = self._calculate_metrics(portfolio_values, data)

        # Prepare results
        results = self._prepare_results(metrics, trades_executed, portfolio_values, signals)

        logger.info(f"Backtest completed. Total return: {metrics['total_return']:.2%}, Sharpe: {metrics['sharpe_ratio']:.2f}, Max DD: {metrics['max_drawdown']:.2%}")

        return results

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and validate data for backtesting

        Args:
            data: Raw DataFrame with historical price data

        Returns:
            Prepared DataFrame
        """
        data = data.copy()
        data.columns = [col.upper() for col in data.columns]
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        data.index.name = 'Date'
        return data

    def _generate_signals(self, data: pd.DataFrame) -> Dict:
        """
        Generate trading signals for each date

        Args:
            data: Prepared DataFrame

        Returns:
            Dict of TradingSignal objects keyed by date
        """
        min_lookback = self.strategy.get_min_lookback()
        dates = data.index
        signals = {}  # date -> TradingSignal for t+1

        # Generate signals for each t (predicting t+1)
        for i in range(min_lookback, len(dates) - 1):  # Up to second last date
            t = dates[i]
            historical_data = data.iloc[:i+1].reset_index()  # Data up to t
            signal = self.strategy.generate_signal(historical_data)
            if signal.signal != 'hold':
                signals[dates[i+1]] = signal  # Signal for t+1

        return signals

    def _execute_backtest(self, data: pd.DataFrame, signals: Dict, symbol: str) -> tuple:
        """
        Execute the backtest by processing signals and tracking portfolio

        Args:
            data: Prepared DataFrame
            signals: Dict of TradingSignal objects
            symbol: Stock symbol

        Returns:
            Tuple of (portfolio_values list, trades_executed list)
        """
        portfolio_values = []
        trades_executed = []
        dates = data.index

        # Execute signals and track portfolio
        for date in dates:
            current_price = data.loc[date, 'CLOSE']

            # Execute signal if available for this date
            if date in signals:
                signal_obj = signals[date]
                sig = signal_obj.signal
                price = signal_obj.price
                reason = signal_obj.reason

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

        return portfolio_values, trades_executed

    def _calculate_metrics(self, portfolio_values: list, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate performance metrics

        Args:
            portfolio_values: List of portfolio values over time
            data: Prepared DataFrame

        Returns:
            Dict of metrics
        """
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

        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'benchmark_return': benchmark_return
        }

    def _prepare_results(self, metrics: Dict[str, float], trades_executed: list,
                        portfolio_values: list, signals: Dict) -> Dict[str, Any]:
        """
        Prepare final results dictionary

        Args:
            metrics: Calculated metrics
            trades_executed: List of executed trades
            portfolio_values: List of portfolio values
            signals: Dict of TradingSignal objects

        Returns:
            Dict with complete backtest results
        """
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df.set_index('date', inplace=True)

        # Convert signals to DataFrame
        if signals:
            signals_data = []
            for date, signal in signals.items():
                signals_data.append({
                    'Date': date,
                    'signal': signal.signal,
                    'price': signal.price,
                    'reason': signal.reason
                })
            signals_df = pd.DataFrame(signals_data)
        else:
            signals_df = pd.DataFrame()

        return {
            'total_return': metrics['total_return'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'max_drawdown': metrics['max_drawdown'],
            'benchmark_return': metrics['benchmark_return'],
            'trades': trades_executed,
            'portfolio_value_over_time': portfolio_df['value'],
            'signals': signals_df
        }