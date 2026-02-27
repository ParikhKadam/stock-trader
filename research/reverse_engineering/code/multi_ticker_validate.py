import pandas as pd
import numpy as np
from pathlib import Path

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(df, period=50):
    return df['Close'].rolling(window=period).mean()

def check_conditions(df, start_idx, lookback=7, rsi=None, sma50=None, volume_avg=None):
    pre_data = df.iloc[max(0, start_idx - lookback):start_idx]
    if len(pre_data) < 3:
        return {}
    
    conditions = {
        'volume_spike': 1 if volume_avg is not None and (pre_data['Volume'] > 1.5 * volume_avg.iloc[pre_data.index]).any() else 0,
        'rsi_divergence': 0,
        'below_sma50': 1 if sma50 is not None and not pd.isna(sma50.iloc[start_idx-1]) and pre_data['Close'].iloc[-1] < sma50.iloc[start_idx-1] else 0,
    }
    
    recent = pre_data.tail(5)
    if len(recent) >= 5 and rsi is not None:
        price_highs = recent['High']
        rsi_vals = rsi.iloc[recent.index]
        if price_highs.iloc[-1] > price_highs.iloc[0] and rsi_vals.iloc[-1] < rsi_vals.max():
            conditions['rsi_divergence'] = 1
    
    return conditions

def quick_validate(ticker):
    # Load data
    data_path = Path(__file__).parent.parent / 'data' / f'{ticker}_2021-01-31_to_2026-01-31.csv'
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df['volume_avg'] = df['Volume'].rolling(window=20).mean()
    
    # Calculate indicators
    rsi = calculate_rsi(df)
    sma50 = calculate_sma(df)
    volume_avg = df['Volume'].rolling(window=20).mean()
    
    # Identify significant moves (price_change)
    events = []
    for i in range(10, len(df)):
        start_price = df.iloc[i-10]['Close']
        end_price = df.iloc[i]['Close']
        change_pct = abs((end_price - start_price) / start_price) * 100
        if change_pct >= 10:
            direction = 'up' if end_price > start_price else 'down'
            events.append({
                'start_date': df.iloc[i-10]['Date'],
                'direction': direction,
                'magnitude_pct': change_pct
            })
    
    # Check pre-conditions for events
    pre_conds = []
    for event in events:
        start_idx = df[df['Date'] == event['start_date']].index[0]
        conds = check_conditions(df, start_idx, rsi=rsi, sma50=sma50, volume_avg=volume_avg)
        pre_conds.append(conds)
    
    # Aggregate
    if pre_conds:
        avg_volume_spike = np.mean([c['volume_spike'] for c in pre_conds])
        avg_rsi_div = np.mean([c['rsi_divergence'] for c in pre_conds])
        avg_below_sma = np.mean([c['below_sma50'] for c in pre_conds])
    else:
        avg_volume_spike = avg_rsi_div = avg_below_sma = 0
    
    return len(events), avg_volume_spike, avg_rsi_div, avg_below_sma

def main():
    tickers = ['ITC', 'NESTLEIND', 'BRITANNIA']
    results = {}
    for ticker in tickers:
        try:
            num_events, vol_spike, rsi_div, below_sma = quick_validate(ticker)
            results[ticker] = {
                'events': num_events,
                'volume_spike_avg': vol_spike,
                'rsi_divergence_avg': rsi_div,
                'below_sma50_avg': below_sma
            }
        except Exception as e:
            results[ticker] = {'error': str(e)}
    
    # Output
    output_path = Path(__file__).parent.parent / 'results' / 'multi_ticker_validation.txt'
    with open(output_path, 'w') as f:
        f.write("Multi-Ticker Validation:\n")
        f.write("HINDUNILVR (baseline): Events 23, Volume Spike 0.22, RSI Div 0.52, Below SMA50 0.65\n")
        for ticker, res in results.items():
            if 'error' in res:
                f.write(f"{ticker}: Error - {res['error']}\n")
            else:
                f.write(f"{ticker}: Events {res['events']}, Volume Spike {res['volume_spike_avg']:.2f}, RSI Div {res['rsi_divergence_avg']:.2f}, Below SMA50 {res['below_sma50_avg']:.2f}\n")
    
    print(f"Validation saved to {output_path}")

if __name__ == '__main__':
    main()