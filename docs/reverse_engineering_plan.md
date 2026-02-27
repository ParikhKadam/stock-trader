# Reverse Engineering Market Moves: Research Plan

## Objective
The goal is to reverse engineer significant market moves to identify the conditions and rationale behind them. This involves analyzing historical data to uncover statistical tendencies that can form the basis of a rule-based swing trading strategy. The focus will be on using OHLC (Open, High, Low, Close), volume, and monthly levels from CSV data for one or more stocks.

## Plan of Action

### Stage 1: Define and Identify Significant Moves (Start from Outcomes)
- **Objective**: Collect a dataset of "big moves" as the dependent variable (the events to explain).
- **Analysis Steps**:
  1. Choose a definition for a "significant move" (e.g., 10%+ price change within 10 trading days, 15%+ move from previous month's high to low, or 2x ATR expansion within 5-15 days).
  2. Scan historical data chronologically for each stock and mark every instance where the condition is met.
  3. Record details such as start date, end date, direction (up/down), magnitude (% change), and duration (days).
  4. Collect 100-200 events across stocks. Expand to more stocks or loosen criteria if fewer events are found.
- **Expected Output**: A table/list of events (e.g., "Stock X: Down 12% in 8 days starting Jan 15, 2020").
- **Pitfalls**: Avoid cherry-picking moves; use consistent criteria.

### Stage 2: Examine Pre-Move Conditions (Gather Raw Observations)
- **Objective**: Look backward from each big move to catalog what preceded it.
- **Analysis Steps**:
  1. For each event, examine 3-7 trading days prior and record objective conditions (e.g., price levels, volume, momentum/overextension, monthly context).
  2. Note if conditions clustered (e.g., breakout + volume spike + divergence).
  3. Analyze 50-100 events initially to spot patterns.
- **Expected Output**: A spreadsheet with columns for each event and pre-conditions.
- **Pitfalls**: Avoid subjective notes; stick to numbers.

### Stage 3: Quantify Patterns and Create Hypotheses (Convert to Measurable Variables)
- **Objective**: Turn observations into testable hypotheses with clear definitions.
- **Analysis Steps**:
  1. Aggregate Stage 2 data and calculate frequencies of conditions.
  2. Define variables mechanically (e.g., "Volume spike = volume >1.5x 20-day avg on breakout day").
  3. Form hypotheses: "If [condition cluster], then P(big move) increases."
  4. Prioritize clusters that appear in >50% of events.
- **Expected Output**: 3-5 hypothesis statements with quantified thresholds.
- **Pitfalls**: Avoid overcomplicating; start with 2-3 variables.

### Stage 4: Compare with Control Samples (Establish Baseline and Edge)
- **Objective**: Test if conditions are predictive (not coincidental).
- **Analysis Steps**:
  1. Count total occurrences of conditions in the full dataset (not just pre-big moves).
  2. Calculate conditional probabilities: P(Big Move | Conditions) vs. P(Big Move | Random).
  3. Use a simple contingency table to compare probabilities.
- **Expected Output**: Probability shifts (e.g., "Conditions increase drop probability from 15% to 45%").
- **Pitfalls**: Small samples inflate results; need 100+ events.

### Stage 5: Analyze Move Characteristics (Assess Tradeability)
- **Objective**: Evaluate if the edge is practical for swing trading.
- **Analysis Steps**:
  1. Measure outcomes for events matching conditions: average magnitude, time to peak, max adverse excursion (MAE), max favorable excursion (MFE).
  2. Calculate expectancy: (Win Rate × Avg Win) - (Loss Rate × Avg Loss).
  3. Check distribution: How often does price reach targets vs. stops?
- **Expected Output**: Metrics like "Avg drop: 7%, MAE: 2.5%, Expectancy: +3% per trade."
- **Pitfalls**: Focus on averages; outliers can mislead.

### Stage 6: Incorporate Regime Context and Validate (Add Robustness)
- **Objective**: Ensure the edge holds across market conditions.
- **Analysis Steps**:
  1. Split events by regime (e.g., index above/below 200-day MA, volatility >/< 20-day avg).
  2. Re-run Stages 3-5 per regime.
  3. Test sensitivity: Vary thresholds and check if results hold.
  4. Out-of-sample check: Use 70% data to form hypotheses, test on 30% unseen data.
- **Expected Output**: Regime-specific insights and robustness score.
- **Pitfalls**: Avoid overfitting; use out-of-sample to verify.

## Current Status
- **Stage**: Stage 6 (Incorporate Regime Context and Validate Robustness) - Completed.
- **Progress**: 
  - Defined regimes (bull/bear, high/low vol) and split events.
  - Sensitivity tests: Edge stable across thresholds (1.2x-2.0x).
  - Out-of-sample: No overfitting detected (train/test event counts similar).
  - Robustness score: Moderate; edge holds in bear_high_vol regimes.
  - Results in notes/stage6_notes.md.
- **Cross-Sector Validation**: Completed.
  - Validated across IT, Banking, Pharma, Auto sectors (12 stocks).
  - Patterns hold with 25-60% volume spike frequencies, 40-100% any condition.
  - Generalizes beyond FMCG; sector-specific variations noted.
  - Results in notes/cross_sector_validation.md.
- **Final Summary**: Reverse engineering validated across sectors. Hypotheses generalize with small edges; regime awareness and sector-specific tuning recommended for strategy implementation.

## Notes
- This document will be updated with observations and progress as the research advances.
- All findings will be recorded systematically to ensure transparency and reproducibility.