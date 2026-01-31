#!/usr/bin/env python3
"""
Test script for backtesting the SMA strategy
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from swing_trader.core import SimpleMovingAverageStrategy, Backtester

def main():
    # Load sample data
    data_path = 'data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv'
    data = pd.read_csv(data_path)
    data['Date'] = pd.to_datetime(data['Date'])
    data.set_index('Date', inplace=True)

    # Create strategy
    strategy = SimpleMovingAverageStrategy({'short_window': 20, 'long_window': 50})

    # Create backtester
    backtester = Backtester(strategy, initial_cash=100000)

    # Run backtest
    results = backtester.run_backtest(data, 'HINDUNILVR')

    print("Backtest Results:")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Benchmark Return: {results['benchmark_return']:.2%}")
    print(f"Number of Trades: {len(results['trades'])}")

    # Show signals
    signals = results['signals']
    print(f"\nNumber of Signals: {len(signals)}")
    buy_signals = signals[signals['signal'] == 'buy']
    sell_signals = signals[signals['signal'] == 'sell']
    print(f"Buy Signals: {len(buy_signals)}, Sell Signals: {len(sell_signals)}")
    if not buy_signals.empty:
        print("First Buy Signal:", buy_signals.iloc[0])
    if not sell_signals.empty:
        print("First Sell Signal:", sell_signals.iloc[0])

    # Show first few trades
    if results['trades']:
        print("\nFirst 5 Trades:")
        for trade in results['trades'][:5]:
            print(f"{trade['date'].date()}: {trade['type']} {trade['quantity']} @ {trade['price']:.2f}")

if __name__ == "__main__":
    main()