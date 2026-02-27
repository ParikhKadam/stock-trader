import pandas as pd
import numpy as np
from pathlib import Path

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_conditions(df):
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    df['Vol_Spike'] = df['Volume'] > 1.5 * df['Vol_Avg']
    df['Below_SMA50'] = df['Close'] < df['SMA50']
    df['RSI_Low'] = df['RSI'] < 50
    return df

def validate_hypotheses(ticker, sector):
    data_path = Path('/home/kadam/data/me/swing-trader/data') / ticker / f'{ticker}_2021-01-31_to_2026-01-31.csv'
    if not data_path.exists():
        return f"{ticker}: No data"
    
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.capitalize()
    df['Date'] = pd.to_datetime(df['Date'])
    df = check_conditions(df)
    
    # Find big moves: 10%+ in 10 days
    big_moves = []
    for i in range(10, len(df)):
        if abs((df.iloc[i]['Close'] - df.iloc[i-10]['Close']) / df.iloc[i-10]['Close']) * 100 >= 10:
            direction = 'up' if df.iloc[i]['Close'] > df.iloc[i-10]['Close'] else 'down'
            big_moves.append((i-10, direction))
    
    # Check pre-conditions 3-7 days before
    vol_spike_count = 0
    rsi_low_count = 0
    below_sma_count = 0
    total_conditions = 0
    up_moves_with_conditions = 0
    
    for start_idx, direction in big_moves:
        if direction == 'up':
            # Check 3-7 days before
            pre_start = max(0, start_idx - 7)
            pre_end = start_idx - 3
            if pre_end < 0:
                continue
            pre_df = df.iloc[pre_start:pre_end+1]
            if len(pre_df) == 0:
                continue
            
            has_vol_spike = pre_df['Vol_Spike'].any()
            has_rsi_low = pre_df['RSI_Low'].any()
            has_below_sma = pre_df['Below_SMA50'].any()
            
            if has_vol_spike:
                vol_spike_count += 1
            if has_rsi_low:
                rsi_low_count += 1
            if has_below_sma:
                below_sma_count += 1
            
            if has_vol_spike or has_rsi_low or has_below_sma:
                total_conditions += 1
                up_moves_with_conditions += 1
    
    total_up_moves = len([d for _, d in big_moves if d == 'up'])
    if total_up_moves == 0:
        return f"{ticker} ({sector}): No up moves"
    
    vol_pct = vol_spike_count / total_up_moves if total_up_moves > 0 else 0
    rsi_pct = rsi_low_count / total_up_moves
    sma_pct = below_sma_count / total_up_moves
    cond_pct = up_moves_with_conditions / total_up_moves
    
    return f"{ticker} ({sector}): Up moves {total_up_moves}, Vol spike {vol_pct:.1%}, RSI low {rsi_pct:.1%}, Below SMA {sma_pct:.1%}, Any condition {cond_pct:.1%}"

def main():
    sectors = {
        'FMCG': ['HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA'],
        'IT': ['TCS', 'INFY', 'WIPRO'],
        'Banking': ['HDFCBANK', 'ICICIBANK', 'SBIN'],
        'Pharma': ['SUNPHARMA', 'DRREDDY', 'CIPLA'],
        'Auto': ['MARUTI', 'BAJAJ-AUTO']
    }
    
    results = []
    for sector, tickers in sectors.items():
        for ticker in tickers:
            result = validate_hypotheses(ticker, sector)
            results.append(result)
            print(result)
    
    # Summary
    print("\nCross-Sector Validation Summary:")
    print("Hypotheses: Volume spike, RSI <50, Below SMA50 precede up moves.")
    print("FMCG showed ~20-25% frequency; check if similar across sectors.")

if __name__ == '__main__':
    main()