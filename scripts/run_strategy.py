#!/usr/bin/env python3
"""
Execute a trading strategy on a CSV file

This script loads historical data from a CSV file and runs a specified trading strategy
to generate signals and simulate trades.
"""
import sys
import os
import argparse
import pandas as pd
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swing_trader.core import (
    SimpleMovingAverageStrategy,
    RSIStrategy,
    Backtester
)


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV data"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} rows from {csv_path}")

        # Check for date column
        date_col = None
        for col in df.columns:
            if col.lower() in ['date', 'datetime', 'timestamp']:
                date_col = col
                break

        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)
            print(f"Set '{date_col}' as index")
        else:
            print("Warning: No date column found, using default index")

        # Normalize column names to snakecase for consistency
        df.columns = [col.lower() for col in df.columns]
        print(f"Normalized column names to snakecase: {list(df.columns)}")

        return df

    except Exception as e:
        raise ValueError(f"Error loading CSV: {e}")


def get_strategy_class(strategy_name: str):
    """Get strategy class by name"""
    strategies = {
        'sma': SimpleMovingAverageStrategy,
        'rsi': RSIStrategy,
    }

    strategy_name = strategy_name.lower()
    if strategy_name not in strategies:
        available = ', '.join(strategies.keys())
        raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {available}")

    return strategies[strategy_name]


def parse_strategy_params(params_str: str) -> dict:
    """Parse strategy parameters from string like 'param1=value1,param2=value2'"""
    if not params_str:
        return {}

    params = {}
    for param in params_str.split(','):
        if '=' not in param:
            raise ValueError(f"Invalid parameter format: {param}. Use 'key=value'")
        key, value = param.split('=', 1)

        # Try to convert to appropriate type
        try:
            # Try int
            if '.' not in value:
                params[key.strip()] = int(value)
            else:
                params[key.strip()] = float(value)
        except ValueError:
            params[key.strip()] = value.strip()

    return params


def run_strategy_analysis(data: pd.DataFrame, strategy_name: str, strategy_params: dict,
                         initial_cash: float = 100000.0):
    """Run strategy analysis on the data"""

    # Create strategy
    strategy_class = get_strategy_class(strategy_name)
    strategy = strategy_class(params=strategy_params)

    print(f"\n=== Strategy Analysis ===")
    print(f"Strategy: {strategy.name}")
    print(f"Parameters: {strategy.params}")
    print(f"Min lookback: {strategy.get_min_lookback()} days")
    print(f"Data range: {data.index.min()} to {data.index.max()}")
    print(f"Data points: {len(data)}")

    # Create backtester
    backtester = Backtester(strategy, initial_cash=initial_cash)

    # Run backtest
    print("\nRunning backtest...")
    results = backtester.run_backtest(data, "CSV_DATA")

    # Print results
    print("\n=== Results ===")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Benchmark Return: {results['benchmark_return']:.2%}")
    print(f"Number of Trades: {len(results['trades'])}")
    print(f"Number of Signals: {len(results['signals'])}")
    print(f"Number of Trades: {len(results['trades'])}")
    print(f"Number of Signals: {len(results['signals'])}")

    # Show signals summary
    signals_df = results['signals']
    if not signals_df.empty:
        buy_signals = signals_df[signals_df['signal'] == 'buy']
        sell_signals = signals_df[signals_df['signal'] == 'sell']
        print(f"Buy Signals: {len(buy_signals)}, Sell Signals: {len(sell_signals)}")

        if len(buy_signals) > 0:
            print(f"First Buy: {buy_signals.iloc[0]['Date']} - {buy_signals.iloc[0]['reason']}")
        if len(sell_signals) > 0:
            print(f"First Sell: {sell_signals.iloc[0]['Date']} - {sell_signals.iloc[0]['reason']}")

    # Show first few trades
    trades = results['trades']
    if trades:
        print("\nFirst 5 Trades:")
        for i, trade in enumerate(trades[:5]):
            print(f"{trade['date'].strftime('%Y-%m-%d')}: {trade['type']} {trade['quantity']} @ {trade['price']:.2f}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Execute a trading strategy on CSV data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_strategy.py data.csv sma
  python run_strategy.py data.csv rsi --params "rsi_period=21,overbought=75,oversold=25"
  python run_strategy.py data.csv sma --cash 50000
        """
    )

    parser.add_argument('csv_file', help='Path to CSV file with historical data')
    parser.add_argument('strategy', choices=['sma', 'rsi'],
                       help='Strategy to run (sma=Simple Moving Average, rsi=RSI)')

    parser.add_argument('--params', default='',
                       help='Strategy parameters as comma-separated key=value pairs')
    parser.add_argument('--cash', type=float, default=100000.0,
                       help='Initial cash amount (default: 100000)')
    parser.add_argument('--output', help='Output results to CSV file')

    args = parser.parse_args()

    try:
        # Load data
        data = load_csv_data(args.csv_file)

        # Parse parameters
        strategy_params = parse_strategy_params(args.params)

        # Run analysis
        results = run_strategy_analysis(data, args.strategy, strategy_params, args.cash)

        # Save results if requested
        if args.output:
            # Save signals
            signals_df = results['signals']
            if not signals_df.empty:
                signals_df.to_csv(f"{args.output}_signals.csv", index=False)
                print(f"\nSignals saved to {args.output}_signals.csv")

            # Save trades
            trades_df = pd.DataFrame(results['trades'])
            if not trades_df.empty:
                trades_df.to_csv(f"{args.output}_trades.csv", index=False)
                print(f"Trades saved to {args.output}_trades.csv")

            # Save portfolio value
            portfolio_df = results['portfolio_value_over_time']
            portfolio_df.to_csv(f"{args.output}_portfolio.csv")
            print(f"Portfolio values saved to {args.output}_portfolio.csv")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()