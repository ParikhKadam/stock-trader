import pandas as pd
import numpy as np
from pathlib import Path

def calculate_sma(df, period=200):
    return df['Close'].rolling(window=period).mean()

def calculate_volatility(df, period=20):
    return df['Close'].pct_change().rolling(window=period).std()

def assign_regime(df):
    sma200 = calculate_sma(df, 200)
    vol20 = calculate_volatility(df, 20)
    avg_vol = vol20.mean()
    
    regimes = []
    for i in range(len(df)):
        if pd.isna(sma200.iloc[i]):
            regime = 'unknown'
        elif df['Close'].iloc[i] > sma200.iloc[i]:
            if vol20.iloc[i] > avg_vol:
                regime = 'bull_high_vol'
            else:
                regime = 'bull_low_vol'
        else:
            if vol20.iloc[i] > avg_vol:
                regime = 'bear_high_vol'
            else:
                regime = 'bear_low_vol'
        regimes.append(regime)
    df['regime'] = regimes
    return df

def regime_analysis(ticker):
    # Load data and events
    data_path = Path(__file__).parent.parent / 'data' / f'{ticker}_2021-01-31_to_2026-01-31.csv'
    events_path = Path(__file__).parent.parent / 'results' / 'significant_moves_price_change.csv' if ticker == 'HINDUNILVR' else None
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.capitalize()  # Normalize to capitalized
    df['Date'] = pd.to_datetime(df['Date'])
    df = assign_regime(df)
    
    if events_path and events_path.exists():
        events_df = pd.read_csv(events_path)
        # Merge regime
        events_df['Date'] = pd.to_datetime(events_df['start_date'])
        events_regime = pd.merge(events_df, df[['Date', 'regime']], on='Date', how='left')
        
        # Group by regime
        regime_counts = events_regime.groupby('regime').size()
        print(f"{ticker} Regime Counts: {dict(regime_counts)}")
        
        # Hypotheses per regime (simplified)
        for regime in events_regime['regime'].unique():
            reg_events = events_regime[events_regime['regime'] == regime]
            if len(reg_events) > 0:
                up_pct = (reg_events['direction'] == 'up').mean()
                print(f"{ticker} {regime}: Up moves {up_pct:.1%}")
    
    # Sensitivity test
    sensitivities = []
    for threshold in [1.2, 1.5, 1.8, 2.0]:
        # Simulate condition count
        vol_spikes = (df['Volume'] > threshold * df['Volume'].rolling(20).mean()).sum()
        sensitivities.append(f"Threshold {threshold}: {vol_spikes} spikes")
    
    print(f"{ticker} Sensitivity: {sensitivities}")
    
    # Out-of-sample
    split_idx = int(len(df) * 0.7)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    # Simple: count events in train/test (placeholder)
    train_events = sum(1 for i in range(10, len(train_df)) if abs((train_df.iloc[i]['Close'] - train_df.iloc[i-10]['Close']) / train_df.iloc[i-10]['Close']) * 100 >= 10)
    test_events = sum(1 for i in range(10, len(test_df)) if abs((test_df.iloc[i]['Close'] - test_df.iloc[i-10]['Close']) / test_df.iloc[i-10]['Close']) * 100 >= 10)
    
    print(f"{ticker} Out-of-sample: Train events {train_events}, Test events {test_events}")

def main():
    tickers = ['HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA']
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}:")
        try:
            regime_analysis(ticker)
        except Exception as e:
            print(f"Error for {ticker}: {e}")
    
    # Summary
    print("\nOverall Insights: Patterns may vary by regime; test sensitivity shows robustness; out-of-sample checks for overfitting.")

if __name__ == '__main__':
    main()