# Liquidity Swing Strategy - Quick Start

## Installation

Framework is already set up in your workspace. All dependencies should be installed via `uv`.

## Test the Strategy (30 seconds)

```bash
# Quick test on ITC data
uv run python scripts/run_strategy.py \
  data/ITC/ITC_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 500000
```

**Expected output:**
- Strategy loads successfully
- State building logs show detection activity
- Results show 0-3 trades (conservative is correct)
- Backtest completes in ~30 seconds

## Run on Multiple Stocks

```bash
# Test on different stocks to see variety of setups
for stock in RELIANCE ITC BRITANNIA HINDUNILVR MARICO; do
  echo "=== $stock ==="
  uv run python scripts/run_strategy.py \
    data/$stock/${stock}_2021-01-31_to_2026-01-31.csv \
    liquidity_swing \
    --cash 500000 2>&1 | grep -A 10 "=== Results ===" 
  echo ""
done
```

## Adjust Sensitivity

### More Permissive (to see if logic works)
```bash
uv run python scripts/run_strategy.py \
  data/RELIANCE/RELIANCE_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 1000000 \
  --params "equal_level_tolerance=0.006,volume_spike_min=1.2,compression_threshold=0.80,min_reward_risk=1.5"
```

### More Conservative (higher quality)
```bash
uv run python scripts/run_strategy.py \
  data/RELIANCE/RELIANCE_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 1000000 \
  --params "equal_level_tolerance=0.002,volume_spike_min=2.0,compression_threshold=0.70,min_reward_risk=2.5"
```

## Understand What's Happening

### Check Detection Logs
```bash
# Run with full logs to see state building
uv run python scripts/run_strategy.py \
  data/ITC/ITC_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 500000 2>&1 | grep "State built"
```

**Look for patterns:**
- "equal lows at X" - Did it find consolidation zones?
- "sweep=True" - Did price hunt stops?
- "reclaim=True" - Did it recover?
- "compression=True" - Was volatility contracting?
- "tradeable=True" - Did ALL conditions align?

### Examine State Programmatically
```python
import pandas as pd
from swing_trader.core.liquidity import LiquiditySwingStateBuilder

# Load data
df = pd.read_csv('data/ITC/ITC_2021-01-31_to_2026-01-31.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

# Build state for last 60 days
recent = df.tail(60)
builder = LiquiditySwingStateBuilder()
state = builder.build(recent)

print(f"Equal lows: {state.equal_low_count} @ {state.equal_low_level}")
print(f"Compression: {state.compression_detected} (score: {state.compression_score:.2f})")
print(f"Sweep: {state.sweep_detected} (low: {state.sweep_low})")
print(f"Reclaim: {state.reclaim_confirmed} (strength: {state.reclaim_body_strength:.1%})")
print(f"Tradeable: {state.is_tradeable()}")
print(f"Confidence: {state.confidence_score():.0%}")
```

## Save Results for Analysis

```bash
mkdir -p results

# Run on BRITANNIA and save all output
uv run python scripts/run_strategy.py \
  data/BRITANNIA/BRITANNIA_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 500000 \
  --output results/britannia_liquidity

# Files created:
# - results/britannia_liquidity_signals.csv
# - results/britannia_liquidity_trades.csv
# - results/britannia_liquidity_portfolio.csv
```

## Interpret Results

### Zero Trades is NORMAL
- Strategy is designed to be **extremely selective**
- Requires ALL 4 conditions simultaneously
- Better to miss trades than take false setups
- Historical data may not have many perfect setups

### What to Look For Instead
1. **State building works**: Logs show detection happening
2. **Conditions trigger individually**: Equal lows found, compression detected, etc.
3. **Parameters affect output**: Relaxing thresholds increases signals
4. **Logic is sound**: When signal fires, it matches your mental model

### Success Metrics
- ✅ Strategy loads without errors
- ✅ State builder processes data
- ✅ Individual conditions detected (even if not all together)
- ✅ When signal generated, setup makes sense
- ✅ R:R ratio always ≥ 2.0
- ❌ Number of trades (misleading for liquidity strategy)

## Common Issues

### "No signals on any stock"
```bash
# Check if detection is finding components
uv run python -c "
import pandas as pd
from swing_trader.core.liquidity import find_swing_lows, detect_equal_levels

df = pd.read_csv('data/ITC/ITC_2021-01-31_to_2026-01-31.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

lows = find_swing_lows(df.tail(60), order=3)
print(f'Swing lows found: {len(lows)}')

if lows:
    equal = detect_equal_levels(lows, tolerance_pct=0.003)
    print(f'Equal level clusters: {len(equal)}')
    for level, touches in equal.items():
        print(f'  {level:.2f}: {len(touches)} touches')
"
```

### "Want to see a signal"
Use very permissive parameters:
```bash
uv run python scripts/run_strategy.py \
  data/RELIANCE/RELIANCE_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 1000000 \
  --params "equal_level_tolerance=0.01,volume_spike_min=1.0,compression_threshold=0.95,min_reward_risk=1.2"
```

This almost guarantees some signals for testing purposes (not for actual trading).

## Next Steps

1. **Run on all stocks** - See which setups occur
2. **Review state logs** - Understand what's being detected
3. **Compare to charts** - Visually verify equal lows / compressions
4. **Tune parameters** - Find balance for your risk tolerance
5. **Add tests** - Validate edge cases in detection logic

## Development Tasks

If you want to enhance the framework:

### High Priority
- [ ] Visual plot generator (mark equal lows, sweeps on charts)
- [ ] Unit tests for detection primitives
- [ ] Trade plan backtester (limit orders + expiry)

### Medium Priority
- [ ] Multi-timeframe support (weekly trend filter)
- [ ] Parameter optimization harness
- [ ] Performance analytics dashboard

### Low Priority
- [ ] Real-time monitoring mode
- [ ] Event calendar integration (earnings filter)
- [ ] Multi-symbol portfolio backtester

## Questions?

Refer to:
- [Full documentation](liquidity_framework.md)
- [Strategy source](../swing_trader/core/strategies/liquidity_swing.py)
- [Detection logic](../swing_trader/core/liquidity/detectors.py)

## Philosophy Reminder

> "The goal is NOT to generate signals. The goal is to detect rare, high-conviction setups where operators have created a structural edge. Most days should produce NO signals. This is correct behavior."

If you're getting trades on every stock weekly, **reduce sensitivity**. Quality > quantity.
