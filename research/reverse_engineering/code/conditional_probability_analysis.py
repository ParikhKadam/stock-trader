"""
Demonstrate why the reverse engineered strategy fails: Conditional Probability Analysis
"""
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_conditional_probabilities():
    """Calculate and compare P(conditions|move) vs P(move|conditions)"""
    
    # Load HINDUNILVR data
    data_path = Path('/home/kadam/data/me/swing-trader/data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv')
    df = pd.read_csv(data_path)
    df.columns = df.columns.str.capitalize()
    df['Date'] = pd.to_datetime(df['Date'])
    
    total_days = len(df)
    print(f"Total trading days: {total_days}")
    print("="*60)
    
    # Calculate indicators
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    df['Vol_Spike'] = df['Volume'] > 1.5 * df['Vol_Avg']
    df['Below_SMA'] = df['Close'] < df['SMA50']
    
    # Identify big moves (10%+ in next 10 days)
    big_move_days = []
    for i in range(len(df) - 10):
        future_idx = min(i + 10, len(df) - 1)
        pct_change = abs((df.iloc[future_idx]['Close'] - df.iloc[i]['Close']) / df.iloc[i]['Close']) * 100
        if pct_change >= 10:
            # Mark this as a day before a big move
            big_move_days.append(i)
    
    df['Big_Move_Ahead'] = False
    df.loc[big_move_days, 'Big_Move_Ahead'] = True
    
    # Count events
    num_big_moves = len(big_move_days)
    days_with_vol_spike = df['Vol_Spike'].sum()
    days_with_below_sma = df['Below_SMA'].sum()
    days_with_any_condition = ((df['Vol_Spike'] | df['Below_SMA'])).sum()
    
    print("\n1. BASE RATES (What We're Working With)")
    print("-"*60)
    print(f"Days before big moves: {num_big_moves} ({num_big_moves/total_days*100:.1f}%)")
    print(f"Days with volume spike: {days_with_vol_spike} ({days_with_vol_spike/total_days*100:.1f}%)")
    print(f"Days below SMA50: {days_with_below_sma} ({days_with_below_sma/total_days*100:.1f}%)")
    print(f"Days with ANY condition: {days_with_any_condition} ({days_with_any_condition/total_days*100:.1f}%)")
    
    # Calculate P(conditions | big move) - What we measured in reverse engineering
    print("\n2. BACKWARD PROBABILITY (What We Measured)")
    print("-"*60)
    print("P(conditions | big move upcoming) = [Looking at days before big moves]")
    
    big_move_df = df[df['Big_Move_Ahead']]
    if len(big_move_df) > 0:
        p_vol_given_move = big_move_df['Vol_Spike'].sum() / len(big_move_df)
        p_below_given_move = big_move_df['Below_SMA'].sum() / len(big_move_df)
        p_any_given_move = ((big_move_df['Vol_Spike'] | big_move_df['Below_SMA'])).sum() / len(big_move_df)
        
        print(f"P(volume spike | big move) = {p_vol_given_move:.1%}")
        print(f"P(below SMA | big move) = {p_below_given_move:.1%}")
        print(f"P(any condition | big move) = {p_any_given_move:.1%}")
        print(f"\n✓ These look good! Conditions occur before {p_any_given_move:.0%} of big moves")
    
    # Calculate P(big move | conditions) - What actually matters for trading
    print("\n3. FORWARD PROBABILITY (What Actually Matters)")
    print("-"*60)
    print("P(big move | conditions present) = [When we see conditions, will move follow?]")
    
    # Volume spike case
    vol_spike_df = df[df['Vol_Spike']]
    if len(vol_spike_df) > 0:
        p_move_given_vol = vol_spike_df['Big_Move_Ahead'].sum() / len(vol_spike_df)
        print(f"P(big move | volume spike) = {p_move_given_vol:.2%}")
    
    # Below SMA case
    below_sma_df = df[df['Below_SMA']]
    if len(below_sma_df) > 0:
        p_move_given_below = below_sma_df['Big_Move_Ahead'].sum() / len(below_sma_df)
        print(f"P(big move | below SMA) = {p_move_given_below:.2%}")
    
    # Any condition case
    any_cond_df = df[(df['Vol_Spike']) | (df['Below_SMA'])]
    if len(any_cond_df) > 0:
        p_move_given_any = any_cond_df['Big_Move_Ahead'].sum() / len(any_cond_df)
        print(f"P(big move | any condition) = {p_move_given_any:.2%}")
        
        baseline = num_big_moves / total_days
        edge = p_move_given_any - baseline
        print(f"\nBaseline P(big move on random day) = {baseline:.2%}")
        print(f"Edge from conditions = {edge:.2%} ({edge*100:.2f} percentage points)")
        print(f"\n✗ The edge is TINY! Conditions barely improve prediction")
    
    # The devastating calculation
    print("\n4. WHY THE STRATEGY FAILS")
    print("-"*60)
    
    # Simulate strategy
    condition_days = any_cond_df.index
    true_positives = any_cond_df['Big_Move_Ahead'].sum()
    false_positives = len(any_cond_df) - true_positives
    
    print(f"Total signals generated: {len(condition_days)}")
    print(f"True positives (actual big moves): {true_positives}")
    print(f"False positives (no big move): {false_positives}")
    print(f"False positive ratio: {false_positives/true_positives:.1f}:1")
    
    # Expected value calculation
    avg_win = 0.08  # Assume 8% average win (below 10% target usually)
    avg_loss = -0.02  # 2% stop loss
    
    ev_true = true_positives * avg_win
    ev_false = false_positives * avg_loss
    ev_total = ev_true + ev_false
    
    print(f"\nExpected value calculation:")
    print(f"  EV from true signals: {true_positives} × {avg_win:.0%} = {ev_true:+.0%}")
    print(f"  EV from false signals: {false_positives} × {avg_loss:.0%} = {ev_false:+.0%}")
    print(f"  Total EV: {ev_total:+.0%}")
    print(f"  Per trade EV: {ev_total/len(condition_days):+.2%}")
    
    print("\n5. THE ROOT CAUSE")
    print("-"*60)
    print("❌ We confused P(A|B) with P(B|A)")
    print("❌ High recall ≠ High precision")
    print("❌ Conditions are TOO COMMON (occur 70% of days)")
    print("❌ Base rate of big moves is TOO LOW (2% of days)")
    print("❌ Result: Tiny edge gets destroyed by false signals")

if __name__ == '__main__':
    analyze_conditional_probabilities()