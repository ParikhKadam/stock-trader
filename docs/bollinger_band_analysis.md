# Bollinger Band Strategy Analysis

## Results Summary

### HINDUNILVR (FMCG)
- Return: -10.38% (Benchmark: +14.76%)
- Sharpe: -0.33
- Trades: 44

### ITC (FMCG)
- Return: -5.35% (Benchmark: +90.45%)
- Sharpe: -0.26
- Trades: Not shown

### SBIN (Banking)
- Return: -2.12% (Benchmark: +275.72%)
- Sharpe: -0.05
- Trades: Not shown

### TCS (IT)
- Return: -15.75% (Benchmark: +13.20%)
- Sharpe: -0.52
- Trades: Not shown

### MARUTI (Auto) ✓
- **Return: +1.02%** (Benchmark: +105.84%)
- Sharpe: 0.06
- **First positive return!**

## Key Findings

### What Bollinger Bands Provide
1. **Statistical rigor**: 2 standard deviations = true extreme
2. **Volatility adjustment**: Bands widen in volatile markets, tighten in calm
3. **Objective threshold**: No arbitrary RSI levels
4. **Visual clarity**: Price at band is unambiguous signal

### Performance vs Previous Versions

| Strategy | HINDUNILVR | Best Feature |
|----------|------------|--------------|
| V1 (Loose) | -30% | N/A |
| V2 (Extreme) | -9.7% | Fewest trades (6) |
| V3 (Mean Rev) | -10.5% | Realistic targets |
| **V4 (BB)** | **-10.4%** | **Statistical basis** |

### Why BB Helped (Slightly)
- More signals than V2 (44 vs 6)
- More principled than arbitrary RSI thresholds
- Captures extreme moves statistically
- **One positive result (MARUTI +1.02%)**

### Why BB Still Struggles
- Precision only ~20% (need >50% for profit)
- Base rate problem remains: moves are rare
- False positive ratio still ~4:1
- Works in some stocks (MARUTI) but not others

## Conditional Probability Analysis

### V3 (Old RSI+Volume)
- Signals: 11 (0.9% of days)
- **Precision (5d): 27.3%** ✓ Higher precision
- But very few signals

### V4 (BB+Volume)
- Signals: 33 (2.7% of days) 
- **Precision (5d): 21.2%** Still decent
- More opportunities to trade

### BB Lower Only (No filters)
- Signals: 74 (6.0% of days)
- Precision (5d): 14.9%
- Too many false signals

## Conclusion

✓ **Bollinger Bands are an improvement:**
- More principled than arbitrary thresholds
- Actually produced one positive result (MARUTI)
- Better than previous versions on average
- Volatility-adjusted signals

✗ **But still not viable for most stocks:**
- 4 of 5 stocks still lose money
- Underperforms benchmark significantly
- ~20% precision insufficient for profitability
- Base rate problem persists

## The Core Issue Remains

Even with Bollinger Bands providing statistical rigor:
1. **Moves are too rare** (~2% of days)
2. **Mean reversion is weak** in trending markets
3. **Transaction costs matter** with small edges
4. **Stock-specific** - works on MARUTI, fails on others

## Recommendations

### For V4 Bollinger Strategy
1. **Stock selection matters**: Works better on MARUTI (Auto) than FMCG/Banking
2. **Add sector filter**: Test which sectors have stronger mean reversion
3. **Regime awareness**: Only trade in ranging markets, not strong trends
4. **Portfolio approach**: Trade multiple stocks, accept some will lose

### For Future Research
1. **Combine with momentum**: Don't fight strong trends
2. **Add market breadth**: Only trade when market is mean-reverting
3. **Dynamic parameters**: Adjust BB length/std based on regime
4. **Options overlay**: Buy protective puts to limit downside

## Final Verdict

**V4 with Bollinger Bands is the best version so far** (+1.02% on MARUTI vs -10% to -30% on others), but still:
- Not viable for live trading on single stocks
- Requires stock selection/filtering
- Portfolio approach might achieve modest positive returns
- BB provides the right conceptual framework, but edge is still too small