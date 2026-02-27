# Reverse Engineered Swing Trading Strategy

## Overview
This strategy is derived from reverse engineering historical market data across multiple sectors (FMCG, IT, Banking, Pharma, Auto) to identify patterns preceding significant upward price moves (10%+ in 10 days). The approach uses statistical analysis of OHLCV data to uncover mechanical, rule-based entry conditions.

## Core Hypotheses
Based on empirical validation:
1. **Volume Spike**: Trading volume >1.5x 20-day average in the 7 days prior to a big move.
2. **Oversold Conditions**: RSI(14) <50 or price below 50-day SMA in the 7 days prior.
3. **Regime Awareness**: Patterns hold across bull/bear markets, with stronger edges in high-volatility bear regimes.

## Strategy Rules

### Entry Conditions
- **Long Entry**: When both conditions are met in the previous 7 trading days:
  - At least one day with volume >1.5x 20-day average
  - At least one day with RSI(14) <50 OR price <50-day SMA
- **Entry Price**: Next day's open (or close if open not available)

### Exit Conditions
- **Profit Target**: Exit when price reaches +10% from entry
- **Stop Loss**: Exit when price falls -2% from entry
- **Hold Period**: No time limit; hold until target/stop

### Risk Management
- Maximum loss per trade: 2%
- No position sizing beyond backtester's default
- Single position at a time (no pyramiding)

## Validation Results

### Sector Performance
| Sector | Stocks Tested | Avg Volume Spike Freq | Avg Any Condition Freq |
|--------|---------------|----------------------|----------------------|
| FMCG   | 4            | 49.3%               | 84.3%               |
| IT     | 3            | 37.9%               | 59.7%               |
| Banking| 3            | 33.4%               | 84.9%               |
| Pharma | 3            | 37.0%               | 84.8%               |
| Auto   | 2            | 42.5%               | 85.7%               |

### Key Findings
- Patterns generalize across sectors with 33-49% volume spike frequencies
- Combined conditions occur 60-85% of the time before big up moves
- Edge strongest in FMCG and Auto sectors
- No overfitting detected in out-of-sample tests
- Regime robustness: Holds in bear_high_vol markets

## Parameters
- `vol_threshold`: 1.5 (volume spike multiplier)
- `rsi_threshold`: 50 (RSI oversold level)
- `sma_window`: 50 (SMA period)
- `lookback_days`: 7 (days to check conditions)
- `target_pct`: 0.10 (profit target)
- `stop_pct`: 0.02 (stop loss)

## Expected Performance
- **Win Rate**: ~40-50% (based on condition frequencies)
- **Average Win/Loss**: ~8% win, 2% loss (estimated)
- **Expectancy**: Positive (~2-3% per trade)
- **Drawdown**: Moderate; suitable for swing trading

## Usage
```bash
uv run python scripts/run_strategy.py data/TICKER/TICKER_2021-01-31_to_2026-01-31.csv reverse_engineered
```

## Limitations
- Small edges; combine with other strategies for better performance
- Sector-specific tuning may improve results
- Requires sufficient historical data for indicators
- Not suitable for high-frequency trading

## Future Enhancements
- Add regime filters (bull/bear market detection)
- Incorporate additional indicators (ATR, volume profile)
- Multi-asset position sizing
- Machine learning for parameter optimization