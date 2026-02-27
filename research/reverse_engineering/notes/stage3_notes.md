# Stage 3 Notes: Quantify Patterns and Create Hypotheses

## Brainstormed Analysis Steps (Max 10)
1. Load pre_conditions.csv and events.csv.
2. Aggregate overall frequencies for each condition (e.g., % with volume_spike=1).
3. Calculate frequencies by direction (up/down moves).
4. Identify condition clusters (e.g., volume_spike + below_sma50).
5. Count cluster frequencies and associations with direction.
6. Form hypotheses: If cluster X, then direction Y likely (based on >60% association).
7. Prioritize: Focus on clusters >30% overall frequency.
8. Output to text file with frequencies and hypotheses.
9. Validate: Ensure hypotheses are data-driven and falsifiable.
10. Iterate: If too few hypotheses, lower thresholds or add more conditions.

## Execution Summary
- Script processed 23 events, aggregated frequencies and clusters.
- Top clusters: ('below_sma50',) ~43%, ('volume_spike', 'below_sma50') ~22%.
- Generated 3 hypotheses based on direction associations.
- No errors; output saved to quantified_patterns.txt.

## Observations
- Key patterns: Volume spikes in ~52% overall, RSI divergence in ~26%, below SMA50 in ~65%.
- Up moves: Higher volume spikes (~63%), above SMA50 (~37%).
- Down moves: All below SMA50 (100%), no volume spikes (0%), RSI divergence ~25%.
- Top clusters: ('below_sma50',) ~43%, ('volume_spike', 'below_sma50') ~22%, ('below_sma50', 'rsi_divergence') ~9%.
- Hypotheses: 3 generated, e.g., below_sma50 predicts down moves in 67% of cases; volume_spike + below_sma50 predicts up in 67%.
- Data suggests regime filter: Below SMA50 for down, volume + above SMA for up.
- Iteration: Lowered thresholds to >20% for clusters and >50% for direction to capture patterns.