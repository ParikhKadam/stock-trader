# Liquidity Swing Trading Framework

## Overview

A complete liquidity-based swing trading system that exploits operator vs retail dynamics through systematic detection of:
- **Equal lows** (retail stop clusters)
- **Price compression** (accumulation phase)  
- **Liquidity sweeps** (stop hunts with rejection)
- **Strong reclaims** (operator re-entry)

## Architecture

```
Data (CSV) → StateBuilder → LiquiditySwingState → Strategy → TradingSignal
                                                            ↓
                                                      Backtester
                                                            ↓
                                                  Risk Manager → Position Tracker
```

### Core Components

#### 1. **Data Models** (`swing_trader/core/models.py`)
- `TradePlan`: Trade plans with entry/stop/target and expiry logic
- `Position`: Active position tracking with P&L
- `LiquiditySwingState`: Strategy-specific market state
- `PortfolioState`: Portfolio-level risk tracking

#### 2. **Liquidity Detection** (`swing_trader/core/liquidity/`)
- **`detectors.py`**: Primitives for swing lows, equal levels, sweeps, reclaims
- **`state_builder.py`**: Orchestrates detection into unified state

#### 3. **Strategy** (`swing_trader/core/strategies/liquidity_swing.py`)
- Conservative parameters (0.3% equal level tolerance)
- Requires ALL conditions: equal lows + compression + sweep + reclaim
- Minimum 2:1 reward-to-risk ratio
- Position sizing based on fixed risk percentage

#### 4. **Risk Management** (`swing_trader/core/`)
- **`risk_manager.py`**: Position sizing, R:R validation, market alignment
- **`trade_invalidation.py`**: Structural invalidation rules
- **`position_tracker.py`**: Position lifecycle management

#### 5. **Technical Indicators** (`swing_trader/utils/indicators.py`)
- ATR calculation & compression detection
- Volume ratios
- Bollinger Band width
- Candle body strength

## Usage

### Basic Backtest

```bash
# Run on ITC data with 500K capital
uv run python scripts/run_strategy.py \
  data/ITC/ITC_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 500000
```

### Custom Parameters

```bash
# More aggressive settings
uv run python scripts/run_strategy.py \
  data/RELIANCE/RELIANCE_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 1000000 \
  --params "equal_level_tolerance=0.005,volume_spike_min=1.3,min_reward_risk=1.8"
```

### Save Results

```bash
uv run python scripts/run_strategy.py \
  data/BRITANNIA/BRITANNIA_2021-01-31_to_2026-01-31.csv \
  liquidity_swing \
  --cash 500000 \
  --output results/britannia_liquidity
  
# Creates:
# - results/britannia_liquidity_signals.csv
# - results/britannia_liquidity_trades.csv
# - results/britannia_liquidity_portfolio.csv
```

## Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `equal_level_tolerance` | 0.003 | Price clustering tolerance (0.3%) |
| `compression_threshold` | 0.75 | ATR contraction ratio (25% reduction required) |
| `volume_spike_min` | 1.5 | Minimum volume ratio for sweep confirmation |
| `min_reward_risk` | 2.0 | Minimum R:R ratio to accept trade |
| `stop_buffer_pct` | 0.01 | Stop placement below sweep low (1%) |
| `target_range_pct` | 1.0 | Target = entry + (1× current range) |
| `swing_order` | 3 | Bars on each side for pivot detection |
| `compression_window` | 10 | Days for compression calculation |
| `volume_lookback` | 20 | Days for average volume |
| `reclaim_strength_min` | 0.6 | Minimum candle body strength (60%) |

## Detection Logic

### 1. Equal Low Detection
```python
# Find swing lows (pivots where low is minimum over 'order' bars each side)
swing_lows = find_swing_lows(df, order=3)

# Cluster lows within 0.3% tolerance
equal_levels = detect_equal_levels(swing_lows, tolerance_pct=0.003)

# Require minimum 2 touches
if count >= 2: ✓
```

### 2. Compression Detection
```python
# Compare recent ATR to past ATR
recent_atr = atr.tail(10).mean()
past_atr = atr.iloc[:-10].mean()

# Require 25% contraction
if recent_atr < past_atr * 0.75: ✓
```

### 3. Sweep Detection
```python
# Check if latest candle swept below equal low but closed above
sweep = (
    candle['low'] < equal_low_level AND
    candle['close'] > equal_low_level AND
    volume_ratio >= 1.5  # 50% above average
)
```

### 4. Reclaim Confirmation
```python
# Verify strong bullish close above level
reclaim = (
    candle['close'] > equal_low_level AND
    candle['close'] > candle['open'] AND  # Bullish
    body_strength >= 0.6  # 60% of full range
)
```

### Combined Setup
```python
tradeable = (
    equal_low_count >= 2 AND
    sweep_detected AND
    reclaim_confirmed AND
    compression_detected
)
```

## Entry/Exit Calculation

### Entry Price
```python
# Slightly above equal low level
entry = equal_low_level + (equal_low_level * 0.002)  # +0.2%

# Don't chase - cap at current close + 1%
entry = min(entry, current_close * 1.01)
```

### Stop Loss
```python
# Below sweep low with buffer
stop = sweep_low * (1 - stop_buffer_pct)  # -1%
```

### Target
```python
# Range-based projection
target = entry + (current_range * target_range_pct)

# Ensure minimum 2% profit
target = max(target, entry * 1.02)
```

### Position Size
```python
# Fixed risk percentage (default 2%)
risk_per_share = entry - stop
max_risk_amount = capital * 0.02
position_size = int(max_risk_amount / risk_per_share)

# Check affordability
if entry * position_size > capital:
    position_size = int(capital / entry)
```

## Example Workflow

### 1. State Building
```python
from swing_trader.core.liquidity import LiquiditySwingStateBuilder
import pandas as pd

# Load data
df = pd.read_csv('data/ITC/ITC_2021-01-31_to_2026-01-31.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')

# Build state
builder = LiquiditySwingStateBuilder()
state = builder.build(df)

print(f"Equal lows: {state.equal_low_count} at {state.equal_low_level}")
print(f"Tradeable: {state.is_tradeable()}")
print(f"Confidence: {state.confidence_score():.1%}")
```

### 2. Signal Generation
```python
from swing_trader.core.strategies import LiquiditySwingStrategy

strategy = LiquiditySwingStrategy()
signal = strategy.generate_signal(df)

if signal.signal == 'buy':
    print(f"BUY at {signal.price}")
    print(f"Reason: {signal.reason}")
```

### 3. Trade Plan Creation
```python
plan = strategy.generate_trade_plan(
    symbol='ITC',
    data=df,
    capital=500000,
    risk_pct=0.02  # 2% risk
)

if plan:
    print(f"Entry: {plan.entry}, Stop: {plan.stop}, Target: {plan.target}")
    print(f"Size: {plan.position_size} shares")
    print(f"R:R: {plan.reward_to_risk:.2f}")
    print(f"Risk: ₹{plan.risk_amount:.2f}")
```

## Expected Behavior

### Conservative Setup Detection
- **Equal lows**: Found frequently (many stocks consolidate)
- **Compression**: Moderate frequency
- **Sweep**: Rare (requires specific price action)
- **Reclaim**: Moderate frequency  
- **All together**: **Very rare** (by design)

### Typical Backtest Results (5-year period)
- **Signals generated**: 0-5 per stock
- **Trades executed**: 0-3
- **Fill rate**: Not applicable (immediate execution in current backtester)
- **Win rate**: Target >40% with 2:1 R:R
- **Expected value**: Positive if R:R maintained

### Why Few Signals is Correct
This is a **quality over quantity** strategy:
- Operators don't create liquidity traps daily
- Requiring all 4 conditions filters noise aggressively
- Missing trades is PREFERRED over false positives
- Each trade should have high conviction

## Tuning Guidance

### If NO signals in 5 years:
1. Relax `equal_level_tolerance` to 0.005 (0.5%)
2. Reduce `volume_spike_min` to 1.3
3. Reduce `compression_threshold` to 0.80 (20% contraction)
4. Lower `reclaim_strength_min` to 0.5

### If TOO MANY signals (>10/year):
1. Tighten `equal_level_tolerance` to 0.002 (0.2%)
2. Increase `volume_spike_min` to 2.0
3. Increase `min_reward_risk` to 2.5
4. Add market trend filter (future enhancement)

### Parameter Optimization
```bash
# Use existing parameter tuner (need to add liquidity_swing to config)
uv run python scripts/parameter_tuner.py \
  --config configs/tuning_config.json \
  --strategy liquidity_swing \
  --metric sharpe
```

## Implementation Status

### ✅ Completed
- Core data models (TradePlan, Position, LiquiditySwingState)
- Liquidity detection primitives (swings, equal levels, sweeps, reclaims)
- State builder orchestration
- Liquidity swing strategy with conservative defaults
- Risk manager (position sizing, validation)
- Trade invalidation rules
- Position tracker
- Technical indicators (ATR, compression, volume)
- CLI integration (automatic strategy discovery)

### ⏳ Partial / Future Enhancements
- **Trade Plan Backtester**: Current backtester uses immediate execution; need limit order simulation with expiry
- **Multi-timeframe**: Daily only; could add weekly trend filter
- **Position tracking in backtester**: Currently simplified portfolio
- **Stop trailing**: Invalidation rules exist but not integrated in backtest
- **Event filtering**: No earnings/RBI calendar integration
- **Multi-symbol portfolio**: Single stock at a time currently

### 🧪 Testing
- Manual validation completed
- Unit tests for detectors: TODO
- Strategy tests: TODO
- Integration tests: TODO

## Files Created/Modified

### New Files
```
swing_trader/core/models.py                    # Extended with new models
swing_trader/core/liquidity/__init__.py        # New module
swing_trader/core/liquidity/detectors.py       # Detection primitives
swing_trader/core/liquidity/state_builder.py   # State orchestration
swing_trader/core/strategies/liquidity_swing.py # Main strategy
swing_trader/core/position_tracker.py          # Position lifecycle
swing_trader/core/risk_manager.py              # Risk management
swing_trader/core/trade_invalidation.py        # Invalidation rules
swing_trader/utils/indicators.py               # Technical indicators
```

### Modified Files
```
swing_trader/core/strategies/__init__.py       # Added LiquiditySwingStrategy export
```

## Next Steps

### Immediate
1. **Run on all stocks** in `data/` folder to gather statistics
2. **Parameter sensitivity analysis** - how much do results change with tolerance adjustments?
3. **Visual validation** - plot detected setups on charts to verify logic

### Short-term
4. **Create trade plan backtester** - proper limit order + expiry simulation
5. **Add unit tests** - especially for edge cases in detection
6. **Multi-timeframe support** - weekly trend filter for direction

### Long-term  
7. **Walk-forward optimization** - avoid overfitting
8. **Regime detection** - adjust parameters for trending vs ranging markets
9. **Portfolio-level backtester** - trade multiple symbols with correlation controls
10. **Live data integration** - real-time state monitoring

## Troubleshooting

### "No signals generated"
- **Check data quality**: Ensure OHLCV columns present and normalized
- **Verify lookback**: Need at least 30 days
- **Review logs**: State builder shows what conditions are met/missed
- **Relax parameters**: Start with more permissive settings

### "Signal generated but seems incorrect"
- **Enable debug logging**: See exact detection values
- **Plot setup**: Visual confirmation helps validate logic
- **Check individual conditions**: Which triggered incorrectly?

### "Performance is poor"
- **Expected**: Few trades = high variance
- **Check R:R**: Are actual exits matching plan?
- **Validate on multiple stocks**: One stock might be unrepresentative
- **Compare to benchmark**: Drawdown more important than raw return

## Philosophy

This framework embodies several key principles from the original analysis:

1. **Operator Psychology over Math**: Detection logic mirrors how operators accumulate and distribute
2. **Asymmetry over Frequency**: 2:1 R:R with 40% win rate beats 60% win rate at 1:1
3. **Structural Edge over Noise**: Equal lows + compression + sweep is a setup, not a pattern
4. **Risk First**: Position sizing calculated before entry, not after
5. **Plan the Trade**: Setup → plan → wait → execute, not react
6. **Invalidation Discipline**: Knowing when NOT to trade is the edge

## Credits

Framework developed based on liquidity-psychology trading concepts discussed in project documentation. Conservative defaults favor false negatives over false positives to maintain setup integrity.
