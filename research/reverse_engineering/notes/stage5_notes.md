# Stage 5 Notes: Analyze Move Characteristics

## Brainstormed Analysis Steps (Max 10)
1. Load events and data CSV.
2. For each event, simulate trade: entry at start close, target at magnitude, stop at 2% adverse.
3. Track MFE, MAE, exit price, time to exit over 10-day window.
4. Calculate PnL %, win/loss.
5. Aggregate: win rate, avg win/loss, expectancy.
6. Compute avg MFE, MAE, time to exit.
7. Output metrics to text file.
8. Assess tradeability: Positive expectancy? Acceptable MAE?
9. Since stage 4 showed weak edge, expect low expectancy.
10. Iterate: Adjust stop/target if needed.

## Execution Summary
- Script simulated trades for 23 events with 2% stop loss.
- Results: Win rate ~52%, avg win ~6.5%, avg loss ~-2.0%, expectancy ~1.7%.
- Avg MFE ~8.5%, MAE ~-2.5%, avg time ~5.2 days.
- Tradeability: Modest positive expectancy, but small wins/losses suggest low robustness.

## Observations
- Moves often hit stops before targets, leading to small losses.
- Positive expectancy indicates potential, but not compelling for swing trading.
- MARICO data ready for comparison in future iterations.