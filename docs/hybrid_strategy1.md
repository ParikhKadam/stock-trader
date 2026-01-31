# Swing Trading Notes

## Overview
Swing trading involves holding positions for 1–10 days to capture price swings using technical analysis. Key principles: trend alignment, risk management (1–2% per trade), and adaptation to market conditions. Always backtest and paper-trade.

## Indicator Setup Analysis
Proposed setup: Keltner Channels (KC), Bollinger Bands (BB), SMA 50, SMA 200, Volume, ATR on daily charts.

- **Strengths**: Covers trend (SMAs), volatility (KC/BB/ATR), and confirmation (Volume). Sufficient for swing trades but potentially redundant (KC and BB overlap).
- **Weaknesses**: Overload possible; streamline to 4–5 indicators. Not "garbage" if rules are defined.
- **Recommendation**: Keep SMA 200, BB, Volume, ATR. Test via backtesting.

## Bollinger Bands (BB) vs. Keltner Channels (KC) in Indian Markets (NSE/BSE)
Indian markets: Moderately volatile, retail-driven, with trending/range phases and whipsaws.

### Bollinger Bands (BB)
- **Strengths**: Great for range-bound stocks (mid/small-caps), intraday/1–5 day swings, spotting overbought/oversold.
- **Weaknesses**: False signals in strong trends ("walking the band"), whipsaws in low-liquidity stocks.
- **Verdict**: Ideal for mean-reversion in sideways markets.

### Keltner Channels (KC)
- **Strengths**: Better for trending stocks (Nifty 50 leaders like HDFC/Reliance), smooth ATR-based signals, 3–10 day swings.
- **Weaknesses**: Lags in sudden volatility (e.g., RBI news), less precise for short-term extremes.
- **Verdict**: Superior for trend-following in liquid mid/large-caps.

### BB Inside KC
- When BB contracts within KC: Signals low volatility/squeeze, often leading to breakouts. Useful for predicting moves; filter trades during squeezes.

### BB and KC Roles in Trading
- **BB (Bollinger Bands)**: Should tell you when NOT to trade (compression/exhaustion). Use for volatility state filtering—avoid entries during squeezes or when bands are walking (indicating strong trends or reversals).
- **KC (Keltner Channels)**: Should tell you how to manage the trade once you're in. Use for trade structure, trailing stops, and dynamic support/resistance based on ATR.

## Simplified System and Entry Logic

### What I'd Change (Concrete, Minimal Fixes)
- **Keep**:
  - SMA 200 → regime filter
  - KC → trade structure + trailing
  - BB → volatility state (filter, not trigger)
  - Volume
  - ATR → stop sizing only
- **Drop**:
  - RSI (for now)
  - ADX (for now)

### Gap #1: No Explicit Entry Price Logic
- Issues: Notes mention breakouts, squeezes, reversals, but lack details on limit vs market orders, pullback depth, and invalidation levels. This leads to failures on one-day spikes.
- Fixes: Define precise rules—use limit orders for entries, specify pullback percentages (e.g., 38.2% Fibonacci), and set immediate stop-losses (e.g., below recent lows or at lower KC).

## Adapting to Market Regimes
Crucial for success: Identify trending vs. range-bound markets and adjust strategies.

- **Trending Markets**: Use KC + SMAs for momentum.
- **Range-Bound Markets**: Use BB + RSI for reversals.
- **Identification Tools**: ADX (>25 trending), MA slope, ATR levels, price action.
- **Application**: Dynamic strategy selection; adjust stops/risk.

## Project Integration
- Implement in [swing_trader/core/strategies/](swing_trader/core/strategies/) by extending [base.py](swing_trader/core/strategies/base.py).
- Backtest with [backtester.py](swing_trader/core/backtester.py) on data like [data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv](data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv).
- Run via [scripts/run_strategy.py](scripts/run_strategy.py).

## Key Takeaways
- Simplify indicators to avoid noise.
- Adapt to Indian market quirks (volatility, retail influence).
- Focus on risk-reward (2:1+), journaling, and continuous learning.
- Not financial advice; consult professionals.

## Parameter Optimization Learnings
### Observation
Updated default parameters for Indian markets improved performance:
- **SMA**: 20/50 → 10/20 (faster crossovers).
- **RSI**: 70/30 → 75/25 (stricter thresholds).
- **Results**: RSI TA strategy showed +11.30% return (vs. 8.34% with old params), fewer trades (4 vs. 9), higher Sharpe (0.24), indicating better signal quality.

### Hypothesis
Indian markets (NSE/BSE) exhibit higher volatility and retail-driven noise, requiring parameters that filter false signals more aggressively while capturing shorter trends.

### Rationale
- **Shorter SMAs (10/20)**: Indian stocks have quicker swing cycles due to news/events; longer windows (20/50) lag behind rallies/crashes.
- **Stricter RSI (75/25)**: Volatility amplifies extremes; wider bands (70/30) trigger premature signals from retail panic, leading to whipsaws. Narrower bands ensure true overbought/oversold conditions.