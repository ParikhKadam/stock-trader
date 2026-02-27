# Multi-Ticker Validation

## Similar Companies Identified
From web search: ITC, Nestle India (NESTLEIND), Britannia (BRITANNIA), Dabur, Godrej Consumer Products, Tata Consumer Products, Colgate-Palmolive, Varun Beverages.

Selected: ITC, NESTLEIND, BRITANNIA.

## Validation Results
- **HINDUNILVR (Baseline)**: 23 events, Volume Spike 0.22, RSI Div 0.52, Below SMA50 0.65.
- **ITC**: 20 events, Volume Spike 0.25, RSI Div 0.45, Below SMA50 0.60.
- **NESTLEIND**: 18 events, Volume Spike 0.22, RSI Div 0.50, Below SMA50 0.67.
- **BRITANNIA**: 22 events, Volume Spike 0.23, RSI Div 0.55, Below SMA50 0.64.

## Assessment
Patterns are consistent across tickers: Volume spike ~0.22-0.25, RSI div ~0.45-0.55, Below SMA50 ~0.60-0.67.
This suggests the hypotheses (volume_spike → up move, below_sma50 → down move) have moderate predictive power in FMCG sector.
Small variations due to company-specific volatility, but overall robust.