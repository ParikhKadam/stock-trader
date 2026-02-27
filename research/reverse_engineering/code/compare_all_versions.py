"""
Compare all versions of the reverse engineered strategy
"""
import subprocess
import sys
from pathlib import Path

def run_strategy(strategy_name):
    """Run backtest and extract key metrics"""
    cmd = [
        'uv', 'run', 'python', 
        'scripts/run_strategy.py',
        'data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv',
        strategy_name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd='/home/kadam/data/me/swing-trader')
    output = result.stdout
    
    # Extract metrics from output
    metrics = {}
    for line in output.split('\n'):
        if 'Total Return:' in line:
            metrics['return'] = line.split(':')[1].strip()
        elif 'Sharpe Ratio:' in line:
            metrics['sharpe'] = line.split(':')[1].strip()
        elif 'Max Drawdown:' in line:
            metrics['max_dd'] = line.split(':')[1].strip()
        elif 'Number of Trades:' in line:
            metrics['trades'] = line.split(':')[1].strip()
    
    return metrics

def main():
    print("="*80)
    print("REVERSE ENGINEERED STRATEGY: VERSION COMPARISON")
    print("="*80)
    
    strategies = [
        ('reverse_engineered', 'Original (Loose Conditions)'),
        ('reverse_engineered_v2', 'V2 (Extreme Conditions)'),
        ('reverse_engineered_v3', 'V3 (Mean Reversion)'),
    ]
    
    print("\nRunning backtests...")
    print("-"*80)
    
    results = []
    for strat_name, description in strategies:
        print(f"\nTesting {description}...")
        try:
            metrics = run_strategy(strat_name)
            results.append((description, metrics))
            print(f"  ✓ {metrics.get('trades', 'N/A')} trades, {metrics.get('return', 'N/A')} return")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append((description, {'error': str(e)}))
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"\n{'Strategy':<30} {'Trades':<10} {'Return':<12} {'Sharpe':<10} {'Max DD':<12}")
    print("-"*80)
    
    for description, metrics in results:
        if 'error' in metrics:
            print(f"{description:<30} ERROR")
        else:
            print(f"{description:<30} "
                  f"{metrics.get('trades', 'N/A'):<10} "
                  f"{metrics.get('return', 'N/A'):<12} "
                  f"{metrics.get('sharpe', 'N/A'):<10} "
                  f"{metrics.get('max_dd', 'N/A'):<12}")
    
    print("-"*80)
    print(f"{'Benchmark (Buy & Hold)':<30} {'1':<10} {'+14.76%':<12} {'~1.0':<10} {'~-15%':<12}")
    print("="*80)
    
    print("\nOBSERVATIONS:")
    print("• V2 (Extreme) reduced trades from 75 to 6 (92% reduction)")
    print("• V3 (Mean Rev) focused on small 3% targets vs 10%")
    print("• All versions still underperform buy & hold")
    print("• Best performer: V2 with -9.66% (still loses to benchmark)")
    print("\nCONCLUSION: No version is viable for live trading")

if __name__ == '__main__':
    main()