"""
Compare old vs new conditions to see if we reduced false positives enough
"""
import pandas as pd
import numpy as np
from pathlib import Path

def compare_conditions():
    data_path = Path('/home/kadam/data/me/swing-trader/data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv')
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.capitalize()
    df['Date'] = pd.to_datetime(df['Date'])
    
    total_days = len(df)
    
    # Calculate indicators
    df['SMA50'] = df['Close'].rolling(50).mean()
    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    df['RSI'] = calculate_rsi(df['Close'])
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    
    # Old conditions
    df['Vol_Spike_Old'] = df['Volume'] > 1.5 * df['Vol_Avg']
    df['RSI_Low_Old'] = df['RSI'] < 50
    df['Below_SMA'] = df['Close'] < df['SMA50']
    df['Any_Cond_Old'] = (df['Vol_Spike_Old'] | df['RSI_Low_Old'] | df['Below_SMA'])
    
    # New conditions
    df['Vol_Spike_New'] = df['Volume'] > 2.5 * df['Vol_Avg']
    df['RSI_Extreme_New'] = df['RSI'] < 30
    df['Confluence_New'] = ((df['Vol_Spike_New'].astype(int) + 
                             df['RSI_Extreme_New'].astype(int) + 
                             df['Below_SMA'].astype(int)) >= 2)
    
    # Identify big moves
    big_move_days = []
    for i in range(len(df) - 10):
        future_idx = min(i + 10, len(df) - 1)
        pct_change = abs((df.iloc[future_idx]['Close'] - df.iloc[i]['Close']) / df.iloc[i]['Close']) * 100
        if pct_change >= 10:
            big_move_days.append(i)
    
    df['Big_Move_Ahead'] = False
    df.loc[big_move_days, 'Big_Move_Ahead'] = True
    
    print("="*70)
    print("CONDITION COMPARISON: Old vs New")
    print("="*70)
    
    print("\nOLD CONDITIONS (Loose)")
    print("-"*70)
    old_cond_days = df['Any_Cond_Old'].sum()
    print(f"Days with conditions: {old_cond_days} ({old_cond_days/total_days*100:.1f}%)")
    old_cond_df = df[df['Any_Cond_Old']]
    if len(old_cond_df) > 0:
        tp_old = old_cond_df['Big_Move_Ahead'].sum()
        fp_old = len(old_cond_df) - tp_old
        precision_old = tp_old / len(old_cond_df) if len(old_cond_df) > 0 else 0
        print(f"True positives: {tp_old}")
        print(f"False positives: {fp_old}")
        print(f"False positive ratio: {fp_old/tp_old if tp_old > 0 else float('inf'):.1f}:1")
        print(f"Precision: {precision_old:.2%}")
        print(f"P(big move | conditions): {precision_old:.2%}")
    
    print("\nNEW CONDITIONS (Strict)")
    print("-"*70)
    new_cond_days = df['Confluence_New'].sum()
    print(f"Days with conditions: {new_cond_days} ({new_cond_days/total_days*100:.1f}%)")
    new_cond_df = df[df['Confluence_New']]
    if len(new_cond_df) > 0:
        tp_new = new_cond_df['Big_Move_Ahead'].sum()
        fp_new = len(new_cond_df) - tp_new
        precision_new = tp_new / len(new_cond_df) if len(new_cond_df) > 0 else 0
        print(f"True positives: {tp_new}")
        print(f"False positives: {fp_new}")
        print(f"False positive ratio: {fp_new/tp_new if tp_new > 0 else float('inf'):.1f}:1")
        print(f"Precision: {precision_new:.2%}")
        print(f"P(big move | conditions): {precision_new:.2%}")
    
    print("\nIMPROVEMENT")
    print("-"*70)
    if len(old_cond_df) > 0 and len(new_cond_df) > 0:
        signal_reduction = (1 - new_cond_days/old_cond_days) * 100
        precision_increase = (precision_new - precision_old) * 100
        print(f"Signal reduction: {signal_reduction:.1f}%")
        print(f"Precision increase: {precision_increase:+.2f} percentage points")
        print(f"Still not enough! Need precision >5% for viability")
    
    print("\nRECOMMENDATIONS FOR FURTHER IMPROVEMENT")
    print("-"*70)
    print("1. Increase volume threshold to 3.5x or 4x")
    print("2. Require RSI <25 (extreme panic)")
    print("3. Add momentum filter: recent close < 5-day low")
    print("4. Require ALL 3 conditions, not just 2")
    print("5. Add regime filter: only trade in specific market phases")

if __name__ == '__main__':
    compare_conditions()