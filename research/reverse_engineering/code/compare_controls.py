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
    """Check pre-conditions for a given start_idx (day before event)."""
    pre_data = df.iloc[max(0, start_idx - lookback):start_idx]
    if len(pre_data) < 3:
        return {}
    
    conditions = {
        'broke_prev_low': 0,  # Simplified, as per previous
        'volume_spike': 1 if volume_avg is not None and (pre_data['Volume'] > 1.5 * volume_avg.iloc[pre_data.index]).any() else 0,
        'rsi_divergence': 0,
        'below_sma50': 1 if sma50 is not None and not pd.isna(sma50.iloc[start_idx-1]) and pre_data['Close'].iloc[-1] < sma50.iloc[start_idx-1] else 0,
    }
    
    # RSI divergence
    recent = pre_data.tail(5)
    if len(recent) >= 5 and rsi is not None:
        price_highs = recent['High']
        rsi_vals = rsi.iloc[recent.index]
        if price_highs.iloc[-1] > price_highs.iloc[0] and rsi_vals.iloc[-1] < rsi_vals.max():
            conditions['rsi_divergence'] = 1
    
    return conditions

def calculate_probabilities(df, events_df, hypotheses):
    """
    For each hypothesis, calculate P(big move | condition) and baseline P(big move).
    """
    total_days = len(df)
    big_move_days = len(events_df)
    baseline_prob = big_move_days / total_days
    
    results = []
    for hypo in hypotheses:
        # Parse hypothesis (simple parsing)
        if 'below_sma50' in hypo and 'down move' in hypo:
            condition = 'below_sma50'
            expected_direction = 'down'
        elif 'volume_spike' in hypo and 'up move' in hypo:
            condition = 'volume_spike'
            expected_direction = 'up'
        else:
            continue  # Skip unparsed
        
    # Pre-calculate indicators
    rsi = calculate_rsi(df)
    sma50 = calculate_sma(df)
    volume_avg = df['Volume'].rolling(window=20).mean()
    
    # For each potential start_idx
    for idx in range(7, len(df)):
        conds = check_conditions(df, idx, rsi=rsi, sma50=sma50, volume_avg=volume_avg)
        if conds.get(condition, 0) == 1:
            condition_count += 1
            event_start = df.iloc[idx]['Date']
            if any(pd.to_datetime(events_df['start_date']) == event_start):
                move_direction = events_df[pd.to_datetime(events_df['start_date']) == event_start]['direction'].iloc[0]
                if move_direction == expected_direction:
                    conditional_big_moves += 1
        
        conditional_prob = conditional_big_moves / condition_count if condition_count > 0 else 0
        edge = conditional_prob - baseline_prob
        
        results.append({
            'hypothesis': hypo,
            'baseline_prob': baseline_prob,
            'conditional_prob': conditional_prob,
            'condition_count': condition_count,
            'edge': edge
        })
    
    return results

def main():
    # Hypotheses from Stage 3
    hypotheses = [
        "If below_sma50, then down move likely",
        "If volume_spike, then up move likely"
    ]
    
    # HINDUNILVR
    data_path = Path(__file__).parent.parent / 'data' / 'HINDUNILVR_2021-01-31_to_2026-01-31.csv'
    events_path = Path(__file__).parent.parent / 'results' / 'significant_moves_price_change.csv'
    df = pd.read_csv(data_path)
    df['Date'] = pd.to_datetime(df['Date'])
    df['volume_avg'] = df['Volume'].rolling(window=20).mean()
    events_df = pd.read_csv(events_path)
    
    results_hin = calculate_probabilities(df, events_df, hypotheses)
    
    # RELIANCE
    data_path_rel = Path(__file__).parent.parent / 'data' / 'RELIANCE_2021-01-31_to_2026-01-31.csv'
    df_rel = pd.read_csv(data_path_rel)
    df_rel['Date'] = pd.to_datetime(df_rel['Date'])
    df_rel['volume_avg'] = df_rel['Volume'].rolling(window=20).mean()
    # For RELIANCE, need to run Stages 1-3, but for now, assume no events or calculate baseline
    # Since no events for RELIANCE yet, calculate baseline only
    total_days_rel = len(df_rel)
    baseline_prob_rel = 0  # No events identified yet
    
    # Output
    output_path = Path(__file__).parent.parent / 'results' / 'control_comparison.txt'
    with open(output_path, 'w') as f:
        f.write("Control Comparison for HINDUNILVR:\n")
        for res in results_hin:
            f.write(f"Hypothesis: {res['hypothesis']}\n")
            f.write(f"Baseline P(Big Move): {res['baseline_prob']:.1%}\n")
            f.write(f"Conditional P(Big Move | Condition): {res['conditional_prob']:.1%}\n")
            f.write(f"Condition Occurrences: {res['condition_count']}\n")
            f.write(f"Edge: {res['edge']:.1%}\n\n")
        f.write("RELIANCE Baseline (no events identified yet): P(Big Move) = 0%\n")
    
    print(f"Control comparison saved to {output_path}")

if __name__ == '__main__':
    main()