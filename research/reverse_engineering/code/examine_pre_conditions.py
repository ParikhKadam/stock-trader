import pandas as pd
import numpy as np
from pathlib import Path

def calculate_rsi(df, period=14):
    """Calculate RSI"""
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(df, period=50):
    """Calculate Simple Moving Average"""
    return df['Close'].rolling(window=period).mean()

def examine_pre_conditions(events_df, data_df):
    """
    For each event, examine 3-7 days prior and record conditions.
    """
    pre_conditions = []
    
    # Prepare data with indicators
    data_df['Date'] = pd.to_datetime(data_df['Date'])
    data_df = data_df.sort_values('Date')
    data_df['RSI'] = calculate_rsi(data_df)
    data_df['SMA50'] = calculate_sma(data_df)
    data_df['Volume_Avg_20'] = data_df['Volume'].rolling(window=20).mean()
    
    # Group by month for monthly highs/lows
    data_df['Month'] = data_df['Date'].dt.to_period('M')
    monthly_highs = data_df.groupby('Month')['High'].max()
    monthly_lows = data_df.groupby('Month')['Low'].min()
    
    for _, event in events_df.iterrows():
        start_date = pd.to_datetime(event['start_date'])
        
        # Look back 3-7 days
        lookback_days = 7
        pre_data = data_df[data_df['Date'] < start_date].tail(lookback_days)
        
        if len(pre_data) < 3:
            continue  # Skip if not enough data
        
        # Record conditions
        conditions = {
            'event_start': event['start_date'],
            'direction': event['direction'],
            'magnitude_pct': event['magnitude_pct'],
            'pre_days': len(pre_data),
            'price_broke_monthly_high': 0,
            'price_broke_monthly_low': 0,
            'volume_spike': 0,
            'rsi_divergence': 0,
            'price_above_sma50': 0,
            'price_below_sma50': 0,
            'atr_expansion': 0,  # Placeholder, can add ATR if needed
            'monthly_context': 'mid_month'  # e.g., start, mid, end
        }
        
        # Get monthly high/low for the PREVIOUS month
        prev_month = (start_date - pd.offsets.MonthBegin(1)).to_period('M')
        monthly_high = monthly_highs.get(prev_month, np.nan)
        monthly_low = monthly_lows.get(prev_month, np.nan)
        
        # Check if price broke monthly high/low in pre-days
        if not pd.isna(monthly_high):
            conditions['price_broke_monthly_high'] = 1 if pre_data['High'].max() > monthly_high else 0
        if not pd.isna(monthly_low):
            conditions['price_broke_monthly_low'] = 1 if pre_data['Low'].min() < monthly_low else 0
        
        # Volume spike: any day >1.5x 20-day avg
        conditions['volume_spike'] = 1 if (pre_data['Volume'] > 1.5 * pre_data['Volume_Avg_20']).any() else 0
        
        # RSI divergence: simple check - if price higher high but RSI lower high in last 5 days
        recent = pre_data.tail(5)
        if len(recent) >= 5:
            price_highs = recent['High']
            rsi_vals = recent['RSI']
            if price_highs.iloc[-1] > price_highs.iloc[0] and rsi_vals.iloc[-1] < rsi_vals.max():
                conditions['rsi_divergence'] = 1
        
        # Price vs SMA50
        last_close = pre_data['Close'].iloc[-1]
        last_sma = pre_data['SMA50'].iloc[-1]
        if not pd.isna(last_sma):
            conditions['price_above_sma50'] = 1 if last_close > last_sma else 0
            conditions['price_below_sma50'] = 1 if last_close < last_sma else 0
        
        # Monthly context
        day_of_month = start_date.day
        if day_of_month <= 5:
            conditions['monthly_context'] = 'start'
        elif day_of_month >= 25:
            conditions['monthly_context'] = 'end'
        else:
            conditions['monthly_context'] = 'mid'
        
        pre_conditions.append(conditions)
    
    return pd.DataFrame(pre_conditions)

def main():
    # Load events
    events_path = Path(__file__).parent.parent / 'results' / 'significant_moves_price_change.csv'
    events_df = pd.read_csv(events_path)
    
    # Load data
    data_path = Path(__file__).parent.parent / 'data' / 'HINDUNILVR_2021-01-31_to_2026-01-31.csv'
    data_df = pd.read_csv(data_path)
    
    # Examine pre-conditions
    pre_conditions_df = examine_pre_conditions(events_df, data_df)
    
    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'pre_move_conditions_marico.csv'
    pre_conditions_df.to_csv(output_path, index=False)
    
    print(f"Examined pre-conditions for {len(pre_conditions_df)} events.")
    print(f"Results saved to {output_path}")

if __name__ == '__main__':
    main()