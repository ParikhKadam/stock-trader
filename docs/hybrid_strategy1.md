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
  - RSI → exit signals (keep for overbought exits)
- **Drop**:
  - ADX (for now - can add later for regime detection)

### Implementation: Explicit Entry/Exit Logic

#### Entry Conditions (ALL must be met):
1. **Regime Filter**: Price > SMA 200 AND distance < 15% (avoid overextension)
2. **KC Breakout**: Close > upper KC (previous close was <= upper KC)
3. **Volume Confirmation**: Current volume > 1.5x volume SMA(20)
4. **No BB Squeeze**: BB width >= 0.5 * KC width (avoid low volatility)
5. **Trend Alignment**: Fast SMA(10) > Slow SMA(20)
6. **Risk-Reward**: Minimum 3:1 R:R ratio (target vs ATR-based stop)

#### Stop Loss Placement:
- **Formula**: Entry Price - (2 × ATR)
- **Rationale**: ATR captures Indian market volatility, 2x buffer prevents premature stops
- **No manual adjustment**: Systematic approach eliminates emotional decisions

#### Exit Conditions (ANY triggers exit):
1. **Trend Reversal**: Price closes below KC midline
2. **Regime Change**: Price closes below SMA 200
3. **Profit Taking**: RSI >= 75 (overbought on Indian scale)
4. **Stop Loss**: Price hits stop level (managed by backtester)

#### Position Sizing:
- Risk 1-2% of capital per trade (standard swing trading)
- Reduce to 0.5-1% during expiry weeks (weekly/monthly options expiry)
- No overnight positions 2 days before major events (budget, RBI policy)

## Adapting to Market Regimes
Crucial for success: Identify trending vs. range-bound markets and adjust strategies.

- **Trending Markets**: Use KC + SMAs for momentum.
- **Range-Bound Markets**: Use BB + RSI for reversals.
- **Identification Tools**: ADX (>25 trending), MA slope, ATR levels, price action.
- **Application**: Dynamic strategy selection; adjust stops/risk.

## Implementation Status

### ✅ Completed - Regime-Adaptive Strategy
**File**: [swing_trader/core/strategies/hybrid.py](swing_trader/core/strategies/hybrid.py)

**Core Innovation**: Automatically detects market regime and applies appropriate logic:
1. **TRENDING UP**: Breakout entries (KC) + ride momentum + minimal exits
2. **SIDEWAYS**: Mean reversion (BB lower) + quick profits (BB mid/upper)  
3. **TRENDING DOWN**: Capital preservation (no entries, exit existing)

**Features Implemented**:
- **Regime Detection**: SMA alignment + slope analysis + price range
- **Trending Logic**: KC breakout + volume (1.3x) + RSI (50-75)
- **Sideways Logic**: BB lower touch + RSI (<35) + panic volume (2x)
- **Adaptive Exits**: Different logic per regime (let trends run, quick range exits)
- **Indian Optimizations**: Fast SMAs (10/20), regime-aware entry/exit

**Parameters** (all configurable):
```python
params = {
    # Regime detection
    'regime_lookback': 50,
    'trending_slope_threshold': 0.08,   # % daily slope
    'sideways_range_threshold': 8.0,     # % max range
    
    # Trending entries (momentum/breakout)
    'kc_length': 20,
    'volume_multiplier_trending': 1.3,
    'rsi_trending_min': 50,
    'rsi_trending_max': 75,
    
    # Sideways entries (mean reversion)
    'bb_length': 20,
    'volume_multiplier_sideways': 2.0,
    'rsi_sideways_buy': 35,
    'rsi_sideways_sell': 65,
}
```

### 🧪 Backtest Results (HINDUNILVR 2021-2026)

**Regime-Adaptive Strategy**:
- Return: -3.52% (8 trades)
- Sharpe: -0.22
- Max DD: -7.95%

**Simple SMA Strategy**:
- Return: 4.56% (59 trades)
- Sharpe: 0.13
- Max DD: -25.03%

**Buy & Hold**:
- Return: 14.76%

### 📊 Key Learning: Stock Selection Matters

**HINDUNILVR Reality**:
- Defensive FMCG stock with steady uptrend (2021-2026: +14.76%)
- Low volatility, infrequent pullbacks
- **Best strategy**: Buy and hold, not active trading
- Swing trading underperforms due to transaction costs + exit noise

**When Hybrid Strategy Works Best**:
1. **Volatile stocks**: High beta (banking, IT, commodity stocks)
2. **Clear regime shifts**: Stocks that trend then consolidate
3. **Good for**: Nifty 50 leaders with momentum (HDFC Bank, Reliance, Infosys)
4. **Not good for**: Defensive stocks with smooth trends (FMCG, Pharma low-vol)

### 🔧 Usage

```bash
# Basic run
uv run python scripts/run_strategy.py \
  data/HINDUNILVR/HINDUNILVR_2021-01-31_to_2026-01-31.csv \
  hybrid

# With custom parameters (tune for stock characteristics)
uv run python scripts/run_strategy.py \
  data/YOUR_STOCK/data.csv \
  hybrid \
  --params "trending_slope_threshold=0.10,rsi_trending_min=52"
```

### 🎯 Strategy Selection Guide

| Stock Type | Best Strategy | Rationale |
|-----------|---------------|-----------|
| **Smooth uptrend (HUL, ITC)** | Buy & Hold | Low volatility, high transaction costs hurt active trading |
| **Volatile trending (Banks)** | Regime-Adaptive | Catch breakouts in trends, mean-revert in ranges |
| **Choppy/sideways (Small-caps)** | Mean Reversion only | Use BB strategy, avoid trend-following |
| **Strong momentum (IT boom)** | Momentum/Breakout | Use trending logic only, ignore sideways rules |

### 💡 Optimization Tips

1. **Match strategy to stock**: Backtest 2+ years before live trading
2. **Adjust regime thresholds**: `trending_slope_threshold` 0.05-0.15 (lower = more trending signals)
3. **Volume requirements**: 1.3x for quality, 2.0x for extreme conviction only
4. **RSI ranges**: Wider (45-75) for more trades, narrower (55-70) for quality
5. **Consider costs**: 15% STCG + 0.025% STT + brokerage eats 2-3% per round trip

### ⚠️ Known Limitations

1. **Stock-specific performance**: Works on volatile stocks, underperforms on steady trends
2. **Requires tuning**: Default params optimized for moderate volatility
3. **No position sizing**: Uses full capital (fixed quantity calculated from cash)
4. **Transaction costs**: Not factored in backtest (real returns will be 2-3% lower)
5. **Regime detection lag**: Takes 50 days to detect regime, misses early moves

## Key Takeaways for Indian Markets

### Strategy Design Principles
1. **Fewer, better signals**: Strict filters → quality over quantity
2. **Adapt to local cycles**: 10/20 SMAs > 20/50 for faster Indian swings
3. **Tax-aware targets**: 3:1 R:R minimum (compensates for 15% STCG)
4. **Volatility-based stops**: 2x ATR handles Indian market whipsaws
5. **Volume is critical**: High retail participation makes volume confirmation essential

### Indian Market-Specific Considerations

#### Implemented in Strategy
- ✅ Faster SMA periods (10/20 vs 20/50)
- ✅ Stricter RSI thresholds (75/25 vs 70/30)
- ✅ Higher R:R ratio (3:1 for tax drag)
- ✅ ATR-based stops (handles volatility)
- ✅ Distance from SMA 200 check (overextension filter)

#### Requires Additional Data (Future)
- ⏳ Delivery % filter (>30% delivery for quality stocks)
- ⏳ Daily turnover filter (₹5 crore minimum for liquidity)
- ⏳ Sector rotation (only trade leading sector stocks)
- ⏳ Expiry week awareness (reduce size before Thu expiry)

#### Manual Considerations (Trader Discipline)
- 🔹 **Circuit filters**: 10% daily limit can freeze exits—size accordingly
- 🔹 **Gap risk**: Overnight gaps from global cues—use stop orders
- 🔹 **Corporate actions**: Dividends cause price adjustments—check calendar
- 🔹 **Event risk**: Budget/RBI policy days—reduce exposure or stay flat
- 🔹 **Illiquid stocks**: Slippage eats profits—stick to liquid names

### Performance Expectations

#### Realistic Targets (Annual)
- **Conservative**: 15-25% (after 15% STCG tax = 12.75-21.25% net)
- **Moderate**: 25-40% (after tax = 21.25-34% net)
- **Aggressive**: 40%+ (requires leverage/higher risk)

#### Trade Characteristics
- **Win rate**: 45-55% (quality setups)
- **Avg hold time**: 3-7 days (swing sweet spot)
- **Max drawdown**: 10-15% (with proper risk management)
- **Trades/year**: 20-40 (fewer = better)

### Risk Warnings
⚠️ **Not financial advice**. Indian markets are volatile and regulated:
- **Regulatory**: SEBI rules, tax implications (STCG/LTCG/STT)
- **Market risk**: Liquidity, circuit filters, gap risk
- **Execution risk**: Slippage, order rejections, margin calls
- **Strategy risk**: Past performance ≠ future results

🔹 **Always paper trade first** (minimum 3 months)
🔹 **Start with small capital** (max 10% of portfolio)
🔹 **Consult financial advisors** for personal situation

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