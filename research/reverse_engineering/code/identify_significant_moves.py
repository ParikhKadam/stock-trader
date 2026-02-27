import pandas as pd
import numpy as np
from pathlib import Path

def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift(1))
    low_close = np.abs(df['Low'] - df['Close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

def identify_significant_moves(df, definition='atr_expansion'):
    """
    Identify significant moves based on chosen definition.
    
    Options:
    - 'price_change': 10%+ change within 10 trading days
    - 'monthly_range': 15%+ move from previous month's high to low
    - 'atr_expansion': 2x ATR expansion within 5-15 days
    """
    events = []
    
    if definition == 'price_change':
        # 10%+ change within 10 days
        for i in range(10, len(df)):
            start_price = df.iloc[i-10]['Close']
            end_price = df.iloc[i]['Close']
            change_pct = abs((end_price - start_price) / start_price) * 100
            if change_pct >= 10:
                direction = 'up' if end_price > start_price else 'down'
                events.append({
                    'start_date': df.iloc[i-10]['Date'],
                    'end_date': df.iloc[i]['Date'],
                    'direction': direction,
                    'magnitude_pct': change_pct,
                    'duration_days': 10
                })
    
    elif definition == 'monthly_range':
        # Group by month and find moves from monthly high to low >=15%
        df['Date'] = pd.to_datetime(df['Date'])
        df['Month'] = df['Date'].dt.to_period('M')
        
        for month, group in df.groupby('Month'):
            if len(group) < 5:  # Skip months with too few days
                continue
            monthly_high = group['High'].max()
            monthly_low = group['Low'].min()
            range_pct = ((monthly_high - monthly_low) / monthly_low) * 100
            if range_pct >= 15:
                # Find the actual move period within the month
                high_idx = group['High'].idxmax()
                low_idx = group['Low'].idxmin()
                start_date = min(high_idx, low_idx)
                end_date = max(high_idx, low_idx)
                duration = (group.loc[end_date, 'Date'] - group.loc[start_date, 'Date']).days
                direction = 'down' if group.loc[low_idx, 'Date'] > group.loc[high_idx, 'Date'] else 'up'
                events.append({
                    'start_date': group.loc[start_date, 'Date'],
                    'end_date': group.loc[end_date, 'Date'],
                    'direction': direction,
                    'magnitude_pct': range_pct,
                    'duration_days': duration
                })
    
    elif definition == 'atr_expansion':
        # 2x ATR expansion within 5-15 days
        df['ATR'] = calculate_atr(df)
        for i in range(15, len(df)):
            # Check expansion over windows of 5-15 days
            for window in range(5, 16):
                if i - window < 0:
                    continue
                start_idx = i - window
                end_idx = i
                start_atr = df.iloc[start_idx]['ATR']
                end_atr = df.iloc[end_idx]['ATR']
                if start_atr > 0 and (end_atr / start_atr) >= 2:
                    start_price = df.iloc[start_idx]['Close']
                    end_price = df.iloc[end_idx]['Close']
                    change_pct = abs((end_price - start_price) / start_price) * 100
                    direction = 'up' if end_price > start_price else 'down'
                    events.append({
                        'start_date': df.iloc[start_idx]['Date'],
                        'end_date': df.iloc[end_idx]['Date'],
                        'direction': direction,
                        'magnitude_pct': change_pct,
                        'duration_days': window
                    })
                    break  # Take the first qualifying window
    
    return events

def main():
    # Load data
    data_path = Path(__file__).parent.parent / 'data' / 'MARICO_2021-01-31_to_2026-01-31.csv'
    df = pd.read_csv(data_path)
    
    # Choose definition
    definition = 'price_change'  # Can be changed to 'price_change' or 'monthly_range'
    
    # Identify events
    events = identify_significant_moves(df, definition)
    
    # Save results
    results_df = pd.DataFrame(events)
    output_path = Path(__file__).parent.parent / 'results' / f'significant_moves_{definition}_marico.csv'
    results_df.to_csv(output_path, index=False)
    
    print(f"Found {len(events)} significant moves using {definition} definition.")
    print(f"Results saved to {output_path}")

if __name__ == '__main__':
    main()