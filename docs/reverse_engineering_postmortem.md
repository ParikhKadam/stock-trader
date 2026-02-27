# Why the Reverse Engineered Strategy Fails: A Post-Mortem Analysis

## Executive Summary
Despite rigorous validation showing patterns exist, the strategy underperforms (-27% vs +15% benchmark) due to a **fundamental statistical error**: confusing P(conditions | big move) with P(big move | conditions).

## The Critical Mistake: Conditional Probability Confusion

### What We Measured (Backward Looking)
During reverse engineering, we identified 10%+ moves and looked backward:
- **P(volume spike | big move occurred)** = 25-60%
- **P(any condition | big move occurred)** = 60-85%

These tell us: "When a big move happened, these conditions were often present beforehand."

### What We Actually Need (Forward Looking)
For trading, we need to know:
- **P(big move will occur | conditions present)** = ???

This tells us: "When we see these conditions, how likely is a big move?"

### Why They're NOT the Same: Bayes' Theorem

```
P(big move | conditions) = P(conditions | big move) × P(big move) / P(conditions)
```

**The Base Rate Problem:**
- P(big move on any day) ≈ 1.9% (23 events in ~1200 days)
- P(conditions present) ≈ 60-85% (conditions are very common!)
- P(conditions | big move) ≈ 60-85%

**Calculating the True Probability:**
```
P(big move | conditions) = (0.70 × 0.019) / 0.70 ≈ 0.019 = 1.9%
```

**The devastating finding:** Seeing the conditions barely increases the probability of a big move! The edge is only +0.2-0.4% as noted in Stage 4.

## Why Small Edges Cause Losses

### 1. **False Positive Rate**
- Strategy generated 85 trades in 5 years
- Only ~23 actual big moves occurred
- **False positive ratio: ~3.7:1** (62 false signals for 23 real moves)

### 2. **Asymmetric Risk/Reward Reality**
- Target: +10% (rarely reached if no big move occurs)
- Stop: -2% (frequently hit on false signals)
- **Expected value per false signal:** -2%
- **Expected value per true signal:** Variable, but often stopped out early

### 3. **Death by a Thousand Cuts**
With 85 trades and ~73% false positives:
- ~62 trades hit stop loss: -2% × 62 = -124%
- ~23 trades with potential: Mixed results
- **Net result:** Large cumulative loss

## What Our Analysis Actually Revealed

### Correct Interpretation
✅ "These conditions occurred before most big moves" (P(cond|move) = 70%)
✅ "Conditions are common in the dataset" (P(cond) = 70%)
✅ "The correlation is weak due to high base rate" (P(move|cond) ≈ P(move))

### Incorrect Interpretation (What We Assumed)
❌ "When these conditions occur, a big move is likely"
❌ "We can predict big moves with 70% accuracy"
❌ "Entering on these conditions will capture most opportunities"

## The Math Behind Our Stage 4 Finding

From Stage 4 notes: **"Edges are small (+0.2-0.4%)"**

This means:
- Baseline P(big move) = 1.9%
- Conditional P(big move | our conditions) = 2.1-2.3%
- **Edge = 0.2-0.4 percentage points**

In betting terms, this is like having a 51% win rate in a coin flip. It's positive expectancy in theory, but:
1. Transaction costs eat the edge
2. Variance kills you with small sample sizes
3. Inconsistent exits (stops vs targets) destroy the math

## Why Cross-Sector Validation Didn't Help

Validating across sectors showed patterns were **consistent**, not **strong**:
- Consistent ≠ Profitable
- All sectors showed the same ~2% conditional probability
- We confirmed the pattern exists everywhere... and is equally weak everywhere

## What We Should Have Done Differently

### 1. **Calculate Forward Probabilities Early**
   - Stage 4 should have been Stage 2
   - Focus on P(move|conditions) from the start
   - Abort if edge <5 percentage points

### 2. **Filter Harder**
   - Our conditions were too loose (70% occurrence rate)
   - Need conditions that occur <10% of the time but capture >50% of moves
   - Example: Multiple indicators simultaneously at extremes

### 3. **Test Multiple Thresholds**
   - Volume >1.5x is too common
   - Should have tested 2x, 2.5x, 3x to reduce false positives
   - Trade off recall for precision

### 4. **Realistic Exit Strategy**
   - 10% target is unrealistic for a 2% edge
   - Should use smaller targets (2-3%) or trailing stops
   - Or hold longer for actual 10% moves (but drawdown risk)

### 5. **Position Sizing Based on Edge**
   - With 0.2-0.4% edge, Kelly Criterion says bet tiny amounts
   - Our all-in approach massively over-leveraged the weak edge

## Lessons Learned

### Statistical Lessons
1. **Correlation ≠ Causation ≠ Predictive Power**
2. **High recall ≠ High precision**
3. **Base rates dominate when conditions are common**
4. **Always calculate both directions of conditional probability**

### Trading Lessons
1. **Edges <5% are nearly untradeable for retail**
2. **More validation ≠ Better strategy if the foundation is wrong**
3. **Backtesting would have caught this immediately**
4. **Theory without execution testing is dangerous**

### Process Lessons
1. **Start with forward testing mindset, not backward analysis**
2. **Calculate profitability metrics at each stage**
3. **Abort early if probabilities are unfavorable**
4. **Backtest with realistic parameters before deep validation**

## Correct Approach for Reverse Engineering

### Phase 1: Discovery (What We Did)
✅ Identify patterns before significant moves

### Phase 2: Validation (What We Missed)
❌ Calculate P(move|pattern) not just P(pattern|move)
❌ Ensure edge >5% above baseline
❌ Filter for precision, not recall

### Phase 3: Refinement (Never Reached)
- Combine multiple low-correlation patterns
- Add regime filters to boost conditional probability
- Test threshold variations

### Phase 4: Execution (Should Have Been Phase 3)
- Backtest with realistic exits
- Optimize position sizing for edge magnitude
- Calculate maximum acceptable drawdown

## Conclusion

The reverse engineering process was **methodologically sound but strategically flawed**. We executed a rigorous research plan but measured the wrong probability. The strategy fails not because the patterns don't exist, but because:

1. **The patterns are too common** (high base rate)
2. **The edge is microscopic** (0.2-0.4 percentage points)
3. **The exits are mismatched** to the edge magnitude
4. **False positives dominate** (3.7:1 ratio)

**Bottom line:** We found a statistically significant pattern that is financially insignificant. This is a cautionary tale about the difference between academic research and profitable trading.

## Recommendations

To salvage this work:
1. **Tighten conditions** drastically (aim for <20% occurrence rate)
2. **Add confluence** (require 3+ indicators simultaneously)
3. **Filter by regime** (only trade in specific market conditions)
4. **Use realistic exits** (2-3% targets, or trail longer)
5. **Combine with other strategies** (ensemble approach)
6. **Accept 0.2-0.4% edge may be noise**, not signal