"""
Analyze Bollinger Band conditions vs original conditions
"""
import pandas as pd
import pandas_ta_classic as ta
from pathlib import Path

def analyze_bb_precision():
    data_path = Path('/home/kadam/data/me/swing-trader/data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv')
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.capitalize()
    df['Date'] = pd.to_datetime(df['Date'])
    
    total_days = len(df)
    
    # Calculate Bollinger Bands
    bb = ta.bbands(df['Close'], length=20, std=2.0)
    df['bb_lower'] = bb['BBL_20_2.0']
    df['bb_middle'] = bb['BBM_20_2.0']
    df['bb_upper'] = bb['BBU_20_2.0']
    
    # Additional indicators
    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    df['RSI'] = calculate_rsi(df['Close'])
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    
    # Old conditions (V3)
    df['Vol_Spike_Old'] = df['Volume'] > 2.0 * df['Vol_Avg']
    df['RSI_Low_Old'] = df['RSI'] < 30
    df['Old_Signal'] = df['Vol_Spike_Old'] & df['RSI_Low_Old']
    
    # New BB conditions
    df['At_BB_Lower'] = (df['Close'] - df['bb_lower']) / df['bb_lower'] <= 0.002
    df['Vol_Spike_BB'] = df['Volume'] > 1.5 * df['Vol_Avg']
    df['RSI_OK_BB'] = (df['RSI'] < 40) | df['RSI'].isna()
    df['BB_Signal'] = df['At_BB_Lower'] & df['Vol_Spike_BB'] & df['RSI_OK_BB']
    
    # Identify big moves (actually let's look at ANY profitable move >2%)
    df['Future_Return_2d'] = df['Close'].shift(-2) / df['Close'] - 1
    df['Future_Return_5d'] = df['Close'].shift(-5) / df['Close'] - 1
    df['Future_Return_10d'] = df['Close'].shift(-10) / df['Close'] - 1
    
    # Any profitable move
    df['Profitable_2d'] = df['Future_Return_2d'] > 0.02
    df['Profitable_5d'] = df['Future_Return_5d'] > 0.02
    df['Profitable_10d'] = df['Future_Return_10d'] > 0.02
    
    print("="*70)
    print("BOLLINGER BAND PRECISION ANALYSIS")
    print("="*70)
    
    print("\nOLD CONDITIONS (V3: RSI<30 + 2x Volume)")
    print("-"*70)
    old_signals = df['Old_Signal'].sum()
    print(f"Total signals: {old_signals} ({old_signals/total_days*100:.1f}% of days)")
    
    if old_signals > 0:
        old_df = df[df['Old_Signal']]
        prof_2d = old_df['Profitable_2d'].sum()
        prof_5d = old_df['Profitable_5d'].sum()
        prof_10d = old_df['Profitable_10d'].sum()
        
        print(f"Profitable in 2 days (>2%): {prof_2d}/{old_signals} = {prof_2d/old_signals:.1%}")
        print(f"Profitable in 5 days (>2%): {prof_5d}/{old_signals} = {prof_5d/old_signals:.1%}")
        print(f"Profitable in 10 days (>2%): {prof_10d}/{old_signals} = {prof_10d/old_signals:.1%}")
    
    print("\nNEW CONDITIONS (V4: At BB Lower + 1.5x Volume + RSI<40)")
    print("-"*70)
    bb_signals = df['BB_Signal'].sum()
    print(f"Total signals: {bb_signals} ({bb_signals/total_days*100:.1f}% of days)")
    
    if bb_signals > 0:
        bb_df = df[df['BB_Signal']]
        prof_2d = bb_df['Profitable_2d'].sum()
        prof_5d = bb_df['Profitable_5d'].sum()
        prof_10d = bb_df['Profitable_10d'].sum()
        
        print(f"Profitable in 2 days (>2%): {prof_2d}/{bb_signals} = {prof_2d/bb_signals:.1%}")
        print(f"Profitable in 5 days (>2%): {prof_5d}/{bb_signals} = {prof_5d/bb_signals:.1%}")
        print(f"Profitable in 10 days (>2%): {prof_10d}/{bb_signals} = {prof_10d/bb_signals:.1%}")
        
        print("\nBB Band Statistics at Signal Times:")
        print(f"Avg distance from lower band: {((bb_df['Close'] - bb_df['bb_lower']) / bb_df['bb_lower']).mean():.2%}")
        print(f"Avg BB width: {((bb_df['bb_upper'] - bb_df['bb_lower']) / bb_df['bb_middle'] * 100).mean():.1f}%")
    
    print("\nCOMPARISON: BB Lower Band Only")
    print("-"*70)
    bb_lower_only = df['At_BB_Lower'].sum()
    print(f"Days at BB lower: {bb_lower_only} ({bb_lower_only/total_days*100:.1f}%)")
    
    if bb_lower_only > 0:
        bb_only_df = df[df['At_BB_Lower']]
        prof_2d = bb_only_df['Profitable_2d'].sum()
        prof_5d = bb_only_df['Profitable_5d'].sum()
        prof_10d = bb_only_df['Profitable_10d'].sum()
        
        print(f"Profitable in 2 days (>2%): {prof_2d}/{bb_lower_only} = {prof_2d/bb_lower_only:.1%}")
        print(f"Profitable in 5 days (>2%): {prof_5d}/{bb_lower_only} = {prof_5d/bb_lower_only:.1%}")
        print(f"Profitable in 10 days (>2%): {prof_10d}/{bb_lower_only} = {prof_10d/bb_lower_only:.1%}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    if bb_signals > 0 and old_signals > 0:
        print("✓ BB provides statistical threshold (2 std dev)")
        print("✓ Reduces subjectivity of RSI thresholds")
        print("✓ Automatically adjusts to volatility regime")
        
        old_precision_5d = prof_5d / old_signals if old_signals > 0 else 0
        bb_precision_5d = (bb_df['Profitable_5d'].sum() / bb_signals) if bb_signals > 0 else 0
        
        if bb_precision_5d > old_precision_5d:
            print(f"✓ BB precision better: {bb_precision_5d:.1%} vs {old_precision_5d:.1%}")
        else:
            print(f"✗ Still similar precision, but BB is more principled")

if __name__ == '__main__':
    analyze_bb_precision()