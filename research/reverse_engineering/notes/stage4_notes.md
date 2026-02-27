# Stage 4 Notes: Compare with Control Samples

## Brainstormed Analysis Steps (Max 10)
1. Define control: All trading days in dataset as baseline for random occurrence.
2. For each hypothesis, identify the key condition (e.g., below_sma50).
3. Scan full dataset to count condition occurrences and associated big moves.
4. Calculate baseline P(big move) = events / total days.
5. Calculate conditional P(big move | condition).
6. Compute edge = conditional - baseline.
7. Download new ticker data (RELIANCE) and copy to research/data/.
8. For new ticker, calculate baseline (no events yet, so 0%).
9. Output probabilities and edges to text file.
10. Validate: Ensure fair comparison; note small sample limitations.

## Execution Summary
- Downloaded MARICO data (2021-2026) instead of RELIANCE; copied to research/data/.
- MARICO baseline: To be calculated (no events identified yet; run Stages 1-3 for full comparison).
- HINDUNILVR results as before; MARICO ready for cross-validation.

## Observations
- Edges are small (+0.2-0.4%), indicating conditions are common but not highly predictive.
- Small sample (23 events) limits significance; need more data/tickers.
- Next: Run Stages 1-3 on RELIANCE for cross-validation.