#!/usr/bin/env python3
"""
Parameter tuner v2 using Optuna for trading strategies.

Config-driven, extendable design for optimizing strategy parameters.
Supports parallel execution and multiple metrics.

USAGE EXAMPLES:
===============

1. Basic usage with default settings:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy sma_ta

2. Optimize for maximum Sharpe ratio (default):
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy rsi_ta --metric sharpe

3. Optimize for maximum total return:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy sma_ta --metric total_return

4. Minimize maximum drawdown:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy bb_ta --metric max_drawdown

5. Run with more trials and parallel processing:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy rsi_ta --n_trials 100 --n_jobs 4

6. Use custom config file:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --config my_config.json --strategy custom_strategy

7. Save results to custom directory:
   uv run python scripts/parameter_tuner_v2.py data/stock_data.csv --strategy sma_ta --output_dir my_results

ARGUMENTS:
==========
- csv_file: Path to CSV file with OHLCV data (required)
- --config: Path to tuning config JSON file (default: configs/tuning_config.json)
- --strategy: Strategy name from config file (required)
- --metric: Optimization metric: sharpe, total_return, or max_drawdown (default: sharpe)
- --n_trials: Number of optimization trials (default: 50)
- --n_jobs: Number of parallel jobs (default: 1)
- --output_dir: Directory to save results (default: tuning_results)

OUTPUT FILES:
=============
- optuna_results_{strategy}_{metric}.csv: All trial results
- best_params_{strategy}_{metric}.json: Best parameters found
- Console output: Optimization summary and detailed backtest results
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
from tabulate import tabulate

# Add the project root to Python path for importing swing_trader modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from swing_trader.core import Backtester


def load_config(config_path: str) -> Dict[str, Any]:
    """Load tuning configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load and validate CSV data for backtesting"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")

    # Find and set date column as index for time series operations
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

    # Normalize column names to lowercase for consistent access
    df.columns = [col.lower() for col in df.columns]
    print(f"Normalized column names: {list(df.columns)}")

    return df


def import_strategy_class(class_path: str):
    """Dynamically import strategy class from module path"""
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def create_objective(
    strategy_class,
    param_config: Dict[str, Any],
    data: pd.DataFrame,
    metric: str,
    backtest_defaults: Dict[str, Any],
    symbol: str
) -> Callable:
    """
    Create Optuna objective function for parameter optimization.

    The objective function:
    1. Suggests parameter values based on config
    2. Creates strategy instance with suggested params
    3. Runs backtest and returns optimization metric
    """
    def objective(trial):
        # Build parameter dictionary from Optuna suggestions
        params = {}

        for name, spec in param_config.items():
            if spec['type'] == 'int':
                params[name] = trial.suggest_int(name, spec['low'], spec['high'])
            elif spec['type'] == 'float':
                params[name] = trial.suggest_float(name, spec['low'], spec['high'])
            elif spec['type'] == 'categorical':
                params[name] = trial.suggest_categorical(name, spec['choices'])

        # Initialize strategy with suggested parameters
        strategy = strategy_class(params)

        # Run backtest with strategy
        backtester = Backtester(strategy, **backtest_defaults)
        results = backtester.run_backtest(data, symbol=symbol)

        # Return metric for optimization (negative for minimization)
        if metric == 'sharpe':
            return results.sharpe_ratio
        elif metric == 'total_return':
            return results.total_return
        elif metric == 'max_drawdown':
            return -results.max_drawdown  # Minimize drawdown
        else:
            raise ValueError(f"Unknown metric: {metric}")

    return objective


def main():
    """Main function to run parameter tuning"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Tune strategy parameters using Optuna (v2)',
        epilog="""
Examples:
  %(prog)s data/stock.csv --strategy rsi_ta
  %(prog)s data/stock.csv --strategy sma_ta --metric total_return --n_trials 100
  %(prog)s data/stock.csv --strategy rsi_ta --metric max_drawdown --n_jobs 4
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_file', help='Path to CSV file with OHLCV historical data')
    parser.add_argument('--config', default='configs/tuning_config.json',
                       help='Path to tuning configuration JSON file (default: configs/tuning_config.json)')
    parser.add_argument('--strategy', required=True,
                       help='Strategy name from config file (e.g., rsi_ta, sma_ta)')
    parser.add_argument('--metric', choices=['sharpe', 'total_return', 'max_drawdown'],
                       default='sharpe', help='Optimization metric (default: sharpe)')
    parser.add_argument('--n_trials', type=int, default=50,
                       help='Number of optimization trials (default: 50)')
    parser.add_argument('--n_jobs', type=int, default=1,
                       help='Number of parallel jobs for optimization (default: 1)')
    parser.add_argument('--output_dir', default='tuning_results',
                       help='Directory to save optimization results (default: tuning_results)')

    args = parser.parse_args()

    # Load configuration from JSON file
    config = load_config(args.config)

    # Validate strategy exists in config
    if args.strategy not in config['strategies']:
        raise ValueError(
            f"Unknown strategy '{args.strategy}'. "
            f"Available: {', '.join(config['strategies'].keys())}"
        )

    # Extract strategy and backtest configuration
    strategy_config = config['strategies'][args.strategy]
    backtest_defaults = config['backtest_defaults'].copy()
    symbol = backtest_defaults.pop('symbol', 'CSV_DATA')

    # Load and prepare historical data
    data = load_csv_data(args.csv_file)

    # Dynamically import the strategy class
    strategy_class = import_strategy_class(strategy_config['class'])

    # Create Optuna objective function
    objective = create_objective(
        strategy_class,
        strategy_config['params'],
        data,
        args.metric,
        backtest_defaults,
        symbol
    )

    # Create output directory for results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Create Optuna study with appropriate direction
    direction = 'maximize' if args.metric != 'max_drawdown' else 'minimize'
    study = optuna.create_study(direction=direction)

    print(
        f"Starting optimization for {args.strategy} | "
        f"metric={args.metric} | trials={args.n_trials} | jobs={args.n_jobs}"
    )

    # Run optimization with specified trials and parallel jobs
    # Fixed: Single optimize call to respect n_trials exactly
    study.optimize(objective, n_trials=args.n_trials, n_jobs=args.n_jobs)

    # Display optimization results
    print("\n=== Optimization Results ===")
    print(f"Best params: {study.best_params}")
    print(f"Best {args.metric}: {study.best_value:.4f}")
    print(f"Number of trials: {len(study.trials)}")

    # Run full backtest with best parameters for detailed results
    print("\n=== Full Backtest Results for Best Params ===")
    strategy = strategy_class(study.best_params)
    backtester = Backtester(strategy, **backtest_defaults)
    best_results = backtester.run_backtest(data, symbol=symbol)

    # Create table with comprehensive results
    table_data = [
        ["Best Params", str(study.best_params)],
        ["Total Return", f"{best_results.total_return:.2%}"],
        ["Sharpe Ratio", f"{best_results.sharpe_ratio:.4f}"],
        ["Max Drawdown", f"{best_results.max_drawdown:.2%}"],
        ["Benchmark Return", f"{best_results.benchmark_return:.2%}"],
        ["Number of Trades", len(best_results.trades)],
        ["Portfolio Values Count", len(best_results.portfolio_value_over_time)],
        ["Signals Count", len(best_results.signals) if best_results.signals else 0],
    ]

    print(tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))

    # Save results to files
    results_file = output_dir / f"optuna_results_{args.strategy}_{args.metric}.csv"
    study.trials_dataframe().to_csv(results_file, index=False)

    best_params_file = output_dir / f"best_params_{args.strategy}_{args.metric}.json"
    with open(best_params_file, 'w') as f:
        json.dump(study.best_params, f, indent=2)

    print(f"\nResults saved to {output_dir}")


# Run the parameter tuner when script is executed directly
# Usage: uv run python scripts/parameter_tuner_v2.py <csv_file> --strategy <strategy_name> [options]
if __name__ == '__main__':
    main()
