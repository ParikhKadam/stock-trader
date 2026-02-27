import pandas as pd
import numpy as np
from pathlib import Path

def analyze_move_characteristics(events_df, data_df):
    """
    Analyze tradeability: MAE, MFE, expectancy, etc.
    """
    results = []
    
    for _, event in events_df.iterrows():
        start_date = pd.to_datetime(event['start_date'])
        direction = event['direction']
        magnitude_pct = event['magnitude_pct']
        
        # Find the data range for the move (10 days)
        start_idx = data_df[data_df['Date'] == start_date].index
        if len(start_idx) == 0:
            continue
        start_idx = start_idx[0]
        end_idx = min(start_idx + 10, len(data_df) - 1)
        
        move_data = data_df.iloc[start_idx:end_idx + 1]
        entry_price = move_data.iloc[0]['Close']
        
        # Simulate trade
        if direction == 'up':
            target_price = entry_price * (1 + magnitude_pct / 100)
            stop_price = entry_price * 0.98  # 2% stop
            exit_condition = lambda p: p >= target_price or p <= stop_price
        else:
            target_price = entry_price * (1 - magnitude_pct / 100)
            stop_price = entry_price * 1.02  # 2% stop
            exit_condition = lambda p: p <= target_price or p >= stop_price
        
        # Track excursion
        max_price = entry_price
        min_price = entry_price
        exit_price = None
        time_to_exit = None
        
        for i, (_, row) in enumerate(move_data.iterrows()):
            price = row['Close']
            max_price = max(max_price, price)
            min_price = min(min_price, price)
            if exit_condition(price):
                exit_price = price
                time_to_exit = i + 1  # days
                break
        
        if exit_price is None:
            # Didn't hit target/stop in 10 days
            exit_price = move_data.iloc[-1]['Close']
            time_to_exit = 10
        
        # Calculate metrics
        if direction == 'up':
            mfe = (max_price - entry_price) / entry_price * 100
            mae = (min_price - entry_price) / entry_price * 100
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            mfe = (entry_price - min_price) / entry_price * 100
            mae = (entry_price - max_price) / entry_price * 100
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        win = pnl_pct > 0
        results.append({
            'direction': direction,
            'magnitude_pct': magnitude_pct,
            'pnl_pct': pnl_pct,
            'win': win,
            'mfe': mfe,
            'mae': mae,
            'time_to_exit': time_to_exit
        })
    
    return pd.DataFrame(results)

def main():
    # Load data
    events_path = Path(__file__).parent.parent / 'results' / 'significant_moves_price_change.csv'
    data_path = Path(__file__).parent.parent / 'data' / 'HINDUNILVR_2021-01-31_to_2026-01-31.csv'
    events_df = pd.read_csv(events_path)
    data_df = pd.read_csv(data_path)
    data_df['Date'] = pd.to_datetime(data_df['Date'])
    
    # Analyze
    characteristics_df = analyze_move_characteristics(events_df, data_df)
    
    # Calculate summary metrics
    total_trades = len(characteristics_df)
    win_rate = characteristics_df['win'].mean()
    avg_win = characteristics_df[characteristics_df['win']]['pnl_pct'].mean()
    avg_loss = characteristics_df[~characteristics_df['win']]['pnl_pct'].mean()
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if not pd.isna(avg_win) and not pd.isna(avg_loss) else 0
    avg_mfe = characteristics_df['mfe'].mean()
    avg_mae = characteristics_df['mae'].mean()
    avg_time = characteristics_df['time_to_exit'].mean()
    
    # Save
    output_path = Path(__file__).parent.parent / 'results' / 'move_characteristics.txt'
    with open(output_path, 'w') as f:
        f.write("Move Characteristics Analysis:\n")
        f.write(f"Total Trades: {total_trades}\n")
        f.write(f"Win Rate: {win_rate:.1%}\n")
        f.write(f"Avg Win: {avg_win:.2f}%\n")
        f.write(f"Avg Loss: {avg_loss:.2f}%\n")
        f.write(f"Expectancy: {expectancy:.2f}%\n")
        f.write(f"Avg MFE: {avg_mfe:.2f}%\n")
        f.write(f"Avg MAE: {avg_mae:.2f}%\n")
        f.write(f"Avg Time to Exit: {avg_time:.1f} days\n")
    
    print(f"Analysis saved to {output_path}")

if __name__ == '__main__':
    main()