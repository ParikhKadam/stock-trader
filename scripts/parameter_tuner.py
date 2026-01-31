#!/usr/bin/env python3
"""
Parameter tuner using Optuna for trading strategies.

Optimizes strategy parameters by running backtests and maximizing Sharpe ratio.
Supports parallel execution.
"""
import sys
import os
import argparse
import pandas as pd
import optuna
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swing_trader.core import (
    RSITAStrategy,
    SimpleMovingAverageTAStrategy,
    Backtester
)


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV data"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

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


def objective_rsi(trial, data: pd.DataFrame):
    """Objective function for RSI TA strategy optimization"""
    rsi_period = trial.suggest_int('rsi_period', 10, 20)
    overbought = trial.suggest_int('overbought', 70, 85)
    oversold = trial.suggest_int('oversold', 15, 30)

    strategy = RSITAStrategy({
        'rsi_period': rsi_period,
        'overbought': overbought,
        'oversold': oversold
    })

    backtester = Backtester(strategy, initial_cash=100000.0)
    results = backtester.run_backtest(data, symbol="CSV_DATA")

    # Return Sharpe ratio (higher is better)
    return results['sharpe_ratio']


def objective_sma(trial, data: pd.DataFrame):
    """Objective function for SMA TA strategy optimization"""
    short_window = trial.suggest_int('short_window', 5, 15)
    long_window = trial.suggest_int('long_window', 15, 30)

    strategy = SimpleMovingAverageTAStrategy({
        'short_window': short_window,
        'long_window': long_window
    })

    backtester = Backtester(strategy, initial_cash=100000.0)
    results = backtester.run_backtest(data, symbol="CSV_DATA")

    # Return Sharpe ratio
    return results['sharpe_ratio']


def main():
    parser = argparse.ArgumentParser(description='Tune strategy parameters using Optuna')
    parser.add_argument('csv_file', help='Path to CSV file with historical data')
    parser.add_argument('strategy', choices=['rsi_ta', 'sma_ta'],
                       help='Strategy to tune')
    parser.add_argument('--n_trials', type=int, default=50,
                       help='Number of optimization trials (default: 50)')
    parser.add_argument('--n_jobs', type=int, default=1,
                       help='Number of parallel jobs (default: 1)')

    args = parser.parse_args()

    # Load data
    data = load_csv_data(args.csv_file)

    # Select objective
    if args.strategy == 'rsi_ta':
        objective = lambda trial: objective_rsi(trial, data)
    elif args.strategy == 'sma_ta':
        objective = lambda trial: objective_sma(trial, data)

    # Create study
    study = optuna.create_study(direction='maximize')
    print(f"Starting optimization for {args.strategy} with {args.n_trials} trials, {args.n_jobs} parallel jobs...")

    # Optimize
    study.optimize(objective, n_trials=args.n_trials, n_jobs=args.n_jobs)

    # Results
    print("\n=== Optimization Results ===")
    print(f"Best params: {study.best_params}")
    print(f"Best Sharpe ratio: {study.best_value:.4f}")
    print(f"Number of trials: {len(study.trials)}")

    # Save to CSV
    df = study.trials_dataframe()
    output_file = f"optuna_results_{args.strategy}.csv"
    df.to_csv(output_file, index=False)
    print(f"Full results saved to {output_file}")


if __name__ == '__main__':
    main()