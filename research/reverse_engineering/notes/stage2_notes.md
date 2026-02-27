# Stage 2 Notes: Examine Pre-Move Conditions

## Brainstormed Analysis Steps (Max 10)
1. Load events CSV from Stage 1 and original data CSV.
2. For each event, identify start_date and extract 3-7 days prior data.
3. Calculate indicators: RSI(14), SMA(50), 20-day volume average, monthly highs/lows.
4. Define conditions mechanically: e.g., broke monthly high if pre-data high > monthly high.
5. Check volume spike: any pre-day volume >1.5x 20-day avg.
6. RSI divergence: price higher high but RSI lower high in last 5 pre-days.
7. Price vs SMA50: above/below on last pre-day.
8. Monthly context: start/mid/end based on day of month.
9. Output to CSV with columns for each condition.
10. Validate: Spot-check 3-5 events manually for accuracy.

## Execution Summary
- Script processed 23 events, output 23 rows of pre-conditions.
- Indicators calculated: RSI, SMA50, volume avg.
- Conditions checked: monthly breaks, volume spikes, RSI divergence, SMA position, monthly context.
- No errors; data alignment handled.

## Observations
- After correction: Broke prev monthly high ~0.22, low ~0.48, volume spike ~0.52.
- Patterns: More low breaks (48%), suggesting moves from previous month lows. RSI divergence ~26%, below SMA50 ~65%.
- Clustering: Down moves often with low breaks + divergence; up moves with volume spikes.
- Validated: Pre-conditions are strictly from days before event start; previous month levels used for liquidity context.