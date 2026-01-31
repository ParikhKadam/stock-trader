#!/usr/bin/env python3
"""
Parameter tuner v2 using Optuna for trading strategies.

Config-driven, extendable design for optimizing strategy parameters.
Supports parallel execution and multiple metrics.
"""
import sys
import os
import argparse
import json
import importlib
import pandas as pd
import optuna
from pathlib import Path
from typing import Dict, Any, Callable

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swing_trader.core import Backtester


def load_config(config_path: str) -> Dict[str, Any]:
    """Load tuning configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


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


def import_strategy_class(class_path: str):
    """Dynamically import strategy class from module path"""
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_objective(strategy_class, param_config: Dict[str, Any], data: pd.DataFrame,
                     metric: str, backtest_defaults: Dict[str, Any], symbol: str) -> Callable:
    """Create generic objective function for Optuna"""

    def objective(trial):
        # Suggest parameters based on config
        params = {}
        for param_name, param_spec in param_config.items():
            param_type = param_spec['type']
            if param_type == 'int':
                params[param_name] = trial.suggest_int(param_name, param_spec['low'], param_spec['high'])
            elif param_type == 'float':
                params[param_name] = trial.suggest_float(param_name, param_spec['low'], param_spec['high'])
            elif param_type == 'categorical':
                params[param_name] = trial.suggest_categorical(param_name, param_spec['choices'])

        # Instantiate strategy
        strategy = strategy_class(params)

        # Run backtest
        backtester = Backtester(strategy, **backtest_defaults)
        results = backtester.run_backtest(data, symbol=symbol)

        # Return selected metric
        if metric == 'sharpe':
            return results['sharpe_ratio']
        elif metric == 'total_return':
            return results['total_return']
        elif metric == 'max_drawdown':
            return -results['max_drawdown']  # Minimize drawdown (negative for maximization)
        else:
            raise ValueError(f"Unknown metric: {metric}")

    return objective


def main():
    parser = argparse.ArgumentParser(description='Tune strategy parameters using Optuna (v2)')
    parser.add_argument('csv_file', help='Path to CSV file with historical data')
    parser.add_argument('--config', default='configs/tuning_config.json',
                       help='Path to tuning config JSON file')
    parser.add_argument('--strategy', required=True,
                       help='Strategy name from config to tune')
    parser.add_argument('--metric', choices=['sharpe', 'total_return', 'max_drawdown'],
                       default='sharpe', help='Metric to optimize (default: sharpe)')
    parser.add_argument('--n_trials', type=int, default=50,
                       help='Number of optimization trials (default: 50)')
    parser.add_argument('--n_jobs', type=int, default=1,
                       help='Number of parallel jobs (default: 1)')
    parser.add_argument('--output_dir', default='tuning_results',
                       help='Output directory for results (default: tuning_results)')

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    if args.strategy not in config['strategies']:
        available = ', '.join(config['strategies'].keys())
        raise ValueError(f"Unknown strategy '{args.strategy}'. Available: {available}")

    strategy_config = config['strategies'][args.strategy]
    backtest_defaults = config['backtest_defaults']
    symbol = backtest_defaults.pop('symbol', 'CSV_DATA')

    # Load data
    data = load_csv_data(args.csv_file)

    # Import strategy class
    strategy_class = import_strategy_class(strategy_config['class'])

    # Create objective
    objective = create_objective(strategy_class, strategy_config['params'], data,
                                args.metric, backtest_defaults, symbol)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Create study
    direction = 'maximize' if args.metric != 'max_drawdown' else 'minimize'
    study = optuna.create_study(direction=direction)
    print(f"Starting optimization for {args.strategy} with {args.n_trials} trials, {args.n_jobs} parallel jobs...")
    print(f"Optimizing metric: {args.metric} ({direction})")

    # Optimize
    study.optimize(objective, n_trials=args.n_trials, n_jobs=args.n_jobs)

    # Results
    print("\n=== Optimization Results ===")
    print(f"Best params: {study.best_params}")
    print(f"Best {args.metric}: {study.best_value:.4f}")
    print(f"Number of trials: {len(study.trials)}")

    # Save results
    results_file = output_dir / f"optuna_results_{args.strategy}_{args.metric}.csv"
    df = study.trials_dataframe()
    df.to_csv(results_file, index=False)
    print(f"Full results saved to {results_file}")

    # Save best params
    best_params_file = output_dir / f"best_params_{args.strategy}_{args.metric}.json"
    with open(best_params_file, 'w') as f:
        json.dump(study.best_params, f, indent=2)
    print(f"Best params saved to {best_params_file}")


if __name__ == '__main__':
    main()