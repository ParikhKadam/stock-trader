import pandas as pd
from pathlib import Path
from collections import Counter

def quantify_patterns(pre_conditions_df):
    """
    Aggregate patterns and create hypotheses.
    """
    # Use pre_conditions_df directly (direction already included)
    merged = pre_conditions_df
    
    # Calculate overall frequencies
    total_events = len(merged)
    frequencies = {}
    for col in ['price_broke_monthly_high', 'price_broke_monthly_low', 'volume_spike', 'rsi_divergence', 'price_above_sma50', 'price_below_sma50']:
        freq = merged[col].sum() / total_events
        frequencies[col] = freq
    
    # Frequencies by direction
    up_moves = merged[merged['direction'] == 'up']
    down_moves = merged[merged['direction'] == 'down']
    
    up_freq = {col: up_moves[col].sum() / len(up_moves) if len(up_moves) > 0 else 0 for col in frequencies.keys()}
    down_freq = {col: down_moves[col].sum() / len(down_moves) if len(down_moves) > 0 else 0 for col in frequencies.keys()}
    
    # Identify clusters (combinations of conditions)
    clusters = []
    for _, row in merged.iterrows():
        cluster = []
        if row['volume_spike']: cluster.append('volume_spike')
        if row['rsi_divergence']: cluster.append('rsi_divergence')
        if row['price_below_sma50']: cluster.append('below_sma50')
        if row['price_above_sma50']: cluster.append('above_sma50')
        if row['price_broke_monthly_low']: cluster.append('broke_prev_low')
        clusters.append(tuple(sorted(cluster)))
    
    cluster_counts = Counter(clusters)
    total_clusters = sum(cluster_counts.values())
    cluster_freq = {k: v / total_clusters for k, v in cluster_counts.items()}
    
    # Form hypotheses: Prioritize clusters with >30% frequency and associate with direction
    hypotheses = []
    for cluster, freq in cluster_freq.items():
        if freq > 0.3:  # Threshold for significance
            cluster_events = [merged.iloc[i] for i, c in enumerate(clusters) if c == cluster]
            up_count = sum(1 for e in cluster_events if e['direction'] == 'up')
            down_count = sum(1 for e in cluster_events if e['direction'] == 'down')
            total_cluster = len(cluster_events)
            if total_cluster > 0:
                up_pct = up_count / total_cluster
                down_pct = down_count / total_cluster
                if up_pct > 0.5:
                    hypotheses.append(f"Hypothesis: If {', '.join(cluster)}, then up move likely (occurs in {up_pct:.1%} of such clusters, overall freq {freq:.1%}).")
                elif down_pct > 0.5:
                    hypotheses.append(f"Hypothesis: If {', '.join(cluster)}, then down move likely (occurs in {down_pct:.1%} of such clusters, overall freq {freq:.1%}).")
                else:
                    hypotheses.append(f"Hypothesis: {', '.join(cluster)} cluster appears in {freq:.1%} of events, mixed directions.")
    
    return frequencies, up_freq, down_freq, cluster_freq, hypotheses

def main():
    # Load data
    pre_conditions_path = Path(__file__).parent.parent / 'results' / 'pre_move_conditions.csv'
    pre_conditions_df = pd.read_csv(pre_conditions_path)
    
    # Quantify
    frequencies, up_freq, down_freq, cluster_freq, hypotheses = quantify_patterns(pre_conditions_df)
    
    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'quantified_patterns.txt'
    with open(output_path, 'w') as f:
        f.write("Overall Frequencies:\n")
        for k, v in frequencies.items():
            f.write(f"{k}: {v:.1%}\n")
        f.write("\nUp Move Frequencies:\n")
        for k, v in up_freq.items():
            f.write(f"{k}: {v:.1%}\n")
        f.write("\nDown Move Frequencies:\n")
        for k, v in down_freq.items():
            f.write(f"{k}: {v:.1%}\n")
        f.write("\nTop Clusters (>20% freq):\n")
        for k, v in sorted(cluster_freq.items(), key=lambda x: x[1], reverse=True):
            if v > 0.2:
                f.write(f"{k}: {v:.1%}\n")
        f.write("\nHypotheses:\n")
        for h in hypotheses:
            f.write(f"{h}\n")
    
    print(f"Quantified patterns and hypotheses saved to {output_path}")

if __name__ == '__main__':
    main()