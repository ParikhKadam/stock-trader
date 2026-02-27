# Stage 1 Notes: Define and Identify Significant Moves

## Brainstormed Analysis Steps (Max 10)
1. Select definition: Initially chose ATR expansion, but found only 6 events; switched to price_change (10%+ within 10 days) for more data points.
2. Validate definition: Price change is standard in swing trading (e.g., used in momentum studies); ATR was too restrictive for this dataset.
3. Prepare data: Load CSV, ensure datetime sorting, no additional calculations needed for price_change.
4. Scan data: Iterate through rows, check for 10%+ change over 10-day windows.
5. Record events: Capture start/end dates, direction, magnitude, duration (fixed at 10 days).
6. Handle overlaps: Events may overlap slightly; recorded all qualifying windows.
7. Output format: Saved to CSV with consistent columns.
8. Count events: 47 found with price_change - better sample size.
9. Review sample: Events span 2021-2025, mix of up/down moves.
10. Adjust if needed: If still low, could add monthly_range or expand to more stocks.

## Execution Summary
- Initial ATR run: 6 events, mostly 2024 up moves, avg magnitude 6.5%.
- Switched to price_change: 47 events, broader distribution.
- Script updated and re-run successfully.
- Data isolated in research/data/.

## Observations
- Price_change captures more volatility, including down moves in 2022-2023.
- Average magnitude: ~11% (higher than ATR).
- Events clustered around market events (e.g., 2022 corrections).
- Sufficient for Stage 2; can expand stocks later if needed.