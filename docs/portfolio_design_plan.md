# Mutual Fund Portfolio Construction — Design Plan

> Consolidated plan capturing all design decisions, reasoning, and open questions
> from the architecture review session (April 2026).

---

## Background & Motivation

The original two-notebook design had a fundamental disconnect:

- **`fund_selection_strategy.ipynb`** — computes a composite `final_score` from
  return horizons, stability, and Crisil rating, then exports a single number per fund.
- **`portfolio_manager_v2.ipynb`** — receives that single number as `abs_score`,
  blends it with a separately-computed `risk_score`, and runs an overlap-constrained optimizer.

This creates several problems:
1. The investor profile (`conservative/moderate/aggressive`) only modifies a blend ratio
   at the very end. A conservative investor cares about *different signals within absolute
   returns* — not just a different blend of two opaque aggregates.
2. Rich factor information (s10Y, s5Y, s_stability, tier, CV) is collapsed into one
   number before the PM ever sees it. Information is permanently lost.
3. Two orthogonal scoring systems (return-horizon percentiles + Sharpe/Sortino) were
   designed independently with no shared intent.
4. The track record multiplier and tier-based weight redistribution both penalise
   the same information gap — a double penalty.

---

## Key Design Decisions (with reasoning)

### 1. Track Record Multiplier — Remove It

**Decision:** Remove `track_record_mult` (×1.00 / ×0.95 / ×0.85 per tier) entirely.

**Reasoning:**
- Weight redistribution (Tier A/B/C) already expresses appropriate caution given
  available data. Applying a second penalty on top of that double-penalises the
  same information gap.
- As a portfolio manager, your job is to produce the *best score estimate given
  available data*. Uncertainty about the estimate belongs in position sizing or
  allocation, not in the score itself.
- The Crisil rating multiplier is a *different* kind of signal — it's an independent
  third-party quality assessment, not a data-availability penalty. It is kept.
- **Exception considered but rejected:** Even Tier C (3Y only) does not need a
  multiplier because the weight scheme already heavily reduces the influence of
  3Y-only data relative to multi-horizon data.

---

### 2. 10Y Return — Longevity Bonus, Not Foundation

**Decision:** 10Y return should be a bonus for funds that have it, not the
dominant weight in the scoring formula.

**Reasoning (illustrated by the BOI vs HDFC Flexi Cap comparison):**

| Fund | 3Y | 5Y | 10Y | s_3Y | s_5Y | s_10Y | Tier | Final (old) |
|------|----|----|-----|------|------|-------|------|-------------|
| Bank of India Flexi Cap | 20.6% | 18.2% | — | 100 | 91.7 | — | B | 72.8 |
| HDFC Flexi Cap | 18.2% | 18.7% | 16.7% | 91.7 | 100 | 84.2 | A | 85.2 |

Gap was 12.4 points. BOI has a *better* 3-year rank (100th percentile) and nearly
identical 5Y performance. A 12-point gap purely because 10Y data isn't published
for BOI is disproportionate.

**Principle:** If both funds have 10Y data, it matters. If only one does, the
comparison should be anchored on 5Y + 3Y, not punish the fund missing 10Y.

---

### 3. 3Y Return — First-Class Citizen

**Decision:** 3Y return is always included as a scored factor in every tier,
not just used as a Tier C fallback.

**Reasoning:**
- 3Y captures recent performance and current market cycle positioning.
- In the old scheme, Tier A and Tier B funds had 3Y return completely ignored.
  A fund with the best recent 3Y performance (percentile 100) received zero credit
  for it, which is information waste.
- 3Y alone can be a bull-market artefact; hence it gets a *lower weight* than 5Y,
  not zero weight.

---

### 4. Profile Permeates Scoring, Not Just Final Blend

**Decision:** Factor weights should vary by investor profile from the start,
not be applied as a blend ratio at the end.

**Reasoning:**
- A conservative investor doesn't just want "less return and more risk" — they want
  *stability and downside protection to matter proportionally more throughout*.
- Applying profile only at the `abs_norm * W_ABS + risk_norm * W_RISK` stage
  means both `abs_norm` and `risk_norm` are computed the same way for all profiles,
  which contradicts the intent.

---

### 5. AuM Filter — Not Currently Available

**Finding (April 2026):**
- `AuM (Cr)` column exists in `all_funds_moneycontrol.tsv` header but is **completely
  empty** for all 924 funds.
- The MoneyControl API (`getSchemeCollection`) does not return AuM data.
- `raw_funds.tsv` (from `download_mutual_funds_v2.py`) also has no AuM field.
- **AuM is therefore not usable as a filter until a separate data source is integrated.**

**Why AuM would matter (for future implementation):**
- Very small AuM = liquidity risk + potential fund closure + manager instability.
- Recommended threshold when available: ₹500 Cr minimum for core holdings.
- This is a *hard filter* (binary in/out), not a scoring factor.

---

### 6. Return Factors — Three Separate Scores, Not One

**Decision:** Split the single `s_long_return` concept into three independent scored
factors: `s_10Y`, `s_5Y`, and `s_3Y`. Each carries its own profile-driven weight.

**Reasoning:**
- Collapsing 10Y and 5Y into one slot meant that for Tier A funds, the 5Y return was
  silently discarded — the same information-loss problem we already fixed for 3Y.
- With three separate factors, missing data is handled cleanly: a Tier B fund simply
  has no `s_10Y` score, and its weight redistributes proportionally to `s_5Y` and
  `s_3Y`. No penalty, no multiplier — honest renormalization.
- `s_10Y` percentile is computed **within Tier A peers only** (fair comparison among
  funds with comparable history). `s_5Y` and `s_3Y` are computed **cross-fund** since
  all eligible funds have this data.
- Conservative investors actually weight `s_10Y` *highest* among return factors —
  multi-cycle proof of survival through bear markets matters more to them than to
  aggressive investors chasing recent momentum.

---

### 7. Crisil Rating — Scored Factor, Not Multiplier

**Decision:** Move Crisil rating from a multiplicative modifier (×1.05/×1.00) to
a scored factor with ~10% weight in the composite.

**Reasoning:**
- A multiplier creates non-linear, hard-to-reason-about effects on the final score.
- Making it a percentile score on the same 0–100 scale as other factors keeps the
  model transparent and additive.
- Same weight across all investor profiles — it's an external quality signal, not
  a market-view or risk-view signal.

---

## Proposed Consolidated Pipeline

```
Phase 0 — Universe Eligibility (hard gates — binary in/out)
  ├── Crisil Rating ≥ 4
  ├── Min data: configurable (3Y / 5Y)        ← Tier C opt-in flag
  └── AuM ≥ floor                              ← deferred (data not available)

Phase 1 — Data Tier Assignment
  ├── Tier A: has 10Y + 5Y
  ├── Tier B: has 5Y, no 10Y
  └── Tier C: has 3Y only (opt-in)

Phase 2 — Five Factor Scores (0–100 percentile)
  ├── s_10Y           10Y return pct — within Tier A + within category; absent for Tier B (redistributes to s_5Y/s_3Y only — see Decision 9)
  ├── s_5Y            5Y return pct — within category (not cross-fund — see Decision 10)
  ├── s_3Y            3Y return pct — within category (not cross-fund — see Decision 10)
  ├── s_risk_adjusted 0.45×Sharpe_5Y_pct + 0.35×Sortino_3Y_pct + 0.20×Sharpe_3Y_pct (each percentile-normalised within category — see Decision 12)
  └── s_consistency   Inverse-CV percentile within category (CV across return horizons = horizon consistency, not volatility — see Decision 11)
  [s_quality REMOVED — Crisil ≥ 4 gate already screens quality; within filtered universe factor is near-binary and overlaps s_risk_adjusted — see Decision 8]

Phase 3 — Profile-Driven Composite Score
  (weights vary by profile; missing s_10Y for Tier B redistributes to s_5Y + s_3Y only — see Decision 9)

  | Factor          | Conservative | Moderate | Aggressive | Investor mindset |
  |-----------------|:-----------:|:--------:|:----------:|------------------|
  | s_10Y           |     25%     |    18%   |    10%     | Multi-cycle proof; conservatives value bear-market survival most |
  | s_5Y            |     15%     |    29%   |    33%     | Medium-term compounding; dominant signal for moderate/aggressive |
  | s_3Y            |      5%     |    10%   |    30%     | Recency/momentum; aggressives ride current trajectory |
  | s_risk_adjusted |     32%     |    28%   |    17%     | Return per unit of risk; primary conservative signal |
  | s_consistency   |     23%     |    15%   |    10%     | Horizon consistency; conservatives avoid uneven multi-period track records |
  | ~~s_quality~~   |      —      |     —    |     —      | Removed — see Decision 8 |

  Return cluster: conservative 45%, moderate 57%, aggressive 73%
  Risk cluster:   conservative 55%, moderate 43%, aggressive 27%

Phase 4 — Category-Aware Shortlisting
  └── Max N per category (default: 3, configurable) — no minimum per category

Phase 5 — Overlap-Constrained Portfolio Optimization
  └── Same backtracking + branch-and-bound algorithm (from portfolio_manager_v2)

Phase 6 — Score-Proportional Weight Allocation
  └── Clip to [floor, cap], iteratively renormalize
```

---

## Resolved Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | **Tier C opt-in** | **Hard-exclude.** 3Y-only funds have no Crisil rating and insufficient history. |
| 2 | **Category constraint** | **Max 3 per category (configurable).** "At least 1 per category" rejected — some categories structurally underperform and forcing inclusion hurts the portfolio. |
| 3 | **AuM filter** | **Skipped.** Data not available from MoneyControl API. To be applied manually by the investor if needed. |
| 4 | **Single or two notebooks** | **Single consolidated notebook.** `fund_selection_strategy.ipynb` and `portfolio_manager_v2.ipynb` to be replaced by one notebook. `fund_scores.tsv` intermediate artifact becomes obsolete. |
| 5 | **Profile weight table** | **Signed off.** 6 factors: s_10Y, s_5Y, s_3Y, s_risk_adjusted, s_stability, s_quality. Weights per profile in Phase 3 table above. Conservative weights s_10Y highest (20%) among return factors — multi-cycle proof matters most. Aggressive weights s_3Y highest (25%) — momentum-driven. |

---

## Data Sources & File Map

| File | Contents | Limitations |
|------|----------|-------------|
| `mutualfunds/all_funds_moneycontrol.tsv` | Returns (1W→10Y), Crisil, Category, AuM (empty) | AuM column always null |
| `mutualfunds/raw_funds.tsv` | ISINs, scheme codes, raw API fields | No AuM, no Sharpe/Sortino |
| `mutualfunds/fund_info/risk_metrics_{isin}.tsv` | Sharpe 3Y/5Y, Sortino, category averages | Fetched per-fund by `fetch_fund_information.py` |
| `mutualfunds/fund_info/holdings_{isin}.tsv` | Stock-level holdings with weights | Used for overlap matrix |
| `mutualfunds/fund_scores.tsv` | Exported scores from fund_selection_strategy.ipynb | Intermediate artifact — becomes obsolete in new design |

---

## What Changes vs Current Implementation

| Aspect | Current | New |
|--------|---------|-----|
| Return factors | 1 slot (10Y or 5Y fallback, 3Y only for Tier C) | 3 separate factors: s_10Y, s_5Y, s_3Y |
| 10Y weight | 40% fixed (Tier A) | 10–20% depending on profile; within-tier percentile |
| 5Y treatment | Dropped for Tier A when 10Y present | Always scored cross-fund |
| 3Y in Tier A/B | Not used | 5–25% depending on profile |
| Stability weight | 25–45% fixed | 10–20% by profile |
| Track record multiplier | ×0.85–1.00 | Removed |
| Crisil treatment | Multiplicative (×1.05/×1.00) | Scored factor, 10% fixed across profiles |
| Profile application | Final blend ratio only | Shapes all six factor weights from the start |
| Two-notebook pipeline | Separate scoring + PM | Single consolidated notebook |
| Score passed between notebooks | `abs_score` single number | All 6 factor scores computed and visible in one place |
| Return percentile scope | Cross-fund | Within-category (see Decision 10) |
| s_10Y redistribution target | All remaining factors | s_5Y + s_3Y only (see Decision 9) |
| s_stability | Inverse-CV, cross-fund | Renamed s_consistency; within-category (see Decision 11) |
| s_quality factor | 10% weight | Removed; Crisil kept as gate only (see Decision 8) |
| s_risk_adjusted definition | Unspecified blend | Explicit: 0.45×Sharpe_5Y + 0.35×Sortino_3Y + 0.20×Sharpe_3Y (see Decision 12) |

---

## Post-Review Design Updates (April 2026)

The following decisions refine the "Proposed Consolidated Pipeline" above after a deeper expert audit.

---

### Decision 8: Remove `s_quality` as a Scored Factor

**Decision:** Drop `s_quality` from the five-factor model entirely. `Crisil ≥ 4` hard gate in Phase 0 is kept unchanged.

**Reasoning:**

1. **Gate makes the factor redundant.** After filtering to `Crisil ≥ 4`, the universe contains only 4-star and 5-star funds. Within that filtered set, `s_quality` is near-binary — the entire 10% weight discriminates between two adjacent rating levels. The marginal information is negligible.

2. **Hard multi-collinearity with `s_risk_adjusted`.** Crisil and Value Research compute Indian MF ratings using Sharpe ratio + 3-year NAV returns within category. That means `s_quality` and `s_risk_adjusted` share underlying inputs — this is not soft correlation, it is a derived overlap. Including both inflates the influence of Sharpe-based signals.

3. **Backward-looking and mean-reverting.** Crisil ratings reflect a trailing 3-year window. Top-rated funds exhibit mean reversion over the subsequent 3-year period — the rating captures past outperformance, not future quality. Using it as a scored factor bakes in a recency bias.

4. **Within-category normalization makes cross-fund comparison meaningless.** A 5-star large-cap fund and a 5-star small-cap fund both earn 100 on `s_quality` — they are top of their respective category pools, not equivalent absolute quality.

**What happens to the freed 10%:** Redistributed to remaining four factors per profile priority — see updated weight table in Phase 3.

---

### Decision 9: Fix Missing `s_10Y` Redistribution — Return Factors Only

**Decision:** When `s_10Y` is absent for a Tier B fund, redistribute its weight **only to `s_5Y` and `s_3Y`**, proportionally by their base weights. `s_risk_adjusted` and `s_consistency` remain at their base profile weights.

**Reasoning:**

Missing 10Y data is a **return data gap**, not a risk data gap. The original "proportional across all factors" redistribution causes a structural error: for a conservative profile, `s_risk_adjusted` inflates from 32% to 39.5% simply because a fund lacks 10Y history. That conflates two different kinds of information.

The correct principle: when long-term return data is absent, compensate with stronger weight on the return data you do have — not on an orthogonal signal category.

**Formula (applied per fund, per profile):**

```
w5  = weights[profile]["s_5Y"]
w3  = weights[profile]["s_3Y"]
w10 = weights[profile]["s_10Y"]

s_5Y_eff  = w5  + w10 × (w5  / (w5 + w3))
s_3Y_eff  = w3  + w10 × (w3  / (w5 + w3))
s_10Y_eff = 0.0
# s_risk_adjusted and s_consistency unchanged from profile base weights
```

**Conservative Tier B example:**
- Base: s_10Y=25%, s_5Y=15%, s_3Y=5%, s_risk=32%, s_consistency=23%
- After: s_10Y=0%, s_5Y=33.75%, s_3Y=11.25%, s_risk=32%, s_consistency=23%
- Risk cluster remains at 55% — same as Tier A. Only the return split changes.

---

### Decision 10: Return Percentiles — Within Category, Not Cross-Fund

**Decision:** `s_5Y`, `s_3Y`, and `s_10Y` percentiles are computed **within category** first. If a category has fewer than `MIN_CATEGORY_SIZE` (default: 5) eligible funds, fall back to Tier-wide percentile.

**Reasoning:**

Cross-fund percentiles give small-cap and mid-cap funds a structural ranking advantage because their category has higher absolute return profiles. A well-managed large-cap fund at the 80th percentile of its category would score near the 40th percentile cross-fund — not because it is a worse fund, but because it plays a different role. The category cap in Phase 4 then has to work as a bias-correction rather than a diversification rule. Computing within-category fixes the root cause.

**Note on `s_10Y`:** The original plan computed `s_10Y` within Tier A peers cross-category. The updated rule adds the within-category constraint on top: within Tier A *and* within category. For categories with fewer than 5 Tier A funds, fall back to Tier A cross-category.

---

### Decision 11: Rename `s_stability` → `s_consistency`; Clarify What CV Measures Here

**Decision:** Rename the factor `s_consistency`. The computation (inverse-CV across return horizons) is retained; only the name and documentation change.

**Reasoning:**

The CV is computed over `{r_1Y, r_2Y, r_3Y, r_5Y [, r_10Y]}` — overlapping cumulative return windows, not independent annual periods. This means the metric measures **horizon consistency**: does this fund deliver well across short, medium, and long time frames? It does *not* measure intra-period volatility (which would require year-by-year NAV series not available in the current dataset).

Calling it `s_stability` implies a volatility measurement that the data does not support. `s_consistency` accurately describes what is being scored.

The reviewer's suggestion to replace with max drawdown or downside deviation is noted but deferred — those require per-year NAV time series, which the MoneyControl data source does not provide. The CV-across-horizons proxy is the best available approximation given current data.

**Implementation note:** Cap raw CV at the 99th percentile before inversion to prevent numerical instability from near-zero mean returns.

---

### Decision 12: Explicit `s_risk_adjusted` Composition

**Decision:**

```
s_risk_adjusted = 0.45 × Sharpe_5Y_pct + 0.35 × Sortino_3Y_pct + 0.20 × Sharpe_3Y_pct
```

Where each component is **percentile-normalised within category** before blending.

**Reasoning:**

- **Sharpe 5Y** (45%): Most stable and reliable risk-adjusted return signal. Longer window reduces noise from a single bad year.
- **Sortino 3Y** (35%): Measures return per unit of *downside* deviation — directly relevant to what investors care about (losses, not upside swings). Adds information orthogonal to Sharpe.
- **Sharpe 3Y** (20%): Adds recency signal. Given lowest weight because it is the noisiest and most correlated with Sharpe 5Y.

Raw Sharpe and Sortino values are scale-sensitive and not directly addable across funds. Percentile normalisation within category is required before the weighted blend.

**Missing value handling:** If `Sharpe_5Y` is absent, redistribute its 0.45 weight proportionally to the other two components (Sortino 3Y → 0.64, Sharpe 3Y → 0.36).

---

### Rejected Suggestions

| Suggestion | Decision | Reason |
|---|---|---|
| Redistribute missing `s_10Y` at 80–90% only, leaving 10–20% as "uncertainty drag" | **Rejected** | Arbitrary magic number with no principled basis. Uncertainty belongs in position sizing (allocation floor/cap), not in the composite score. Full redistribution to return factors is the correct approach. |
| Add "category-relative strength" as a 5% meta-factor (category momentum vs. benchmark) | **Rejected** | Over-engineering. Requires category benchmark time-series not in current dataset. Category timing is a tactical/trading signal, not relevant to long-term MF selection. Can be revisited if benchmark data becomes available. |

---

## Final Notebook Implementation Plan

**Goal:** A single Jupyter notebook — `mutual_fund_portfolio.ipynb` — that replaces both `fund_selection_strategy.ipynb` and `portfolio_manager_v2.ipynb`. Top-to-bottom execution produces a final portfolio with allocations.

---

### Section 0 — Configuration

All tunable parameters in one cell at the top. No magic numbers buried in code.

```python
# ── Investor profile ──────────────────────────────────────────────────────────
PROFILE = "moderate"          # "conservative" | "moderate" | "aggressive"

# ── Universe filters ──────────────────────────────────────────────────────────
CRISIL_MIN          = 4       # hard gate: minimum Crisil star rating
MIN_CATEGORY_SIZE   = 5       # min funds in category for within-category pct;
                              # falls back to tier-wide if below

# ── Portfolio construction ────────────────────────────────────────────────────
CATEGORY_CAP        = 3       # max funds selected per category (Phase 4)
OVERLAP_THRESHOLD   = 0.40    # max allowed pairwise holding overlap (Phase 5)
ALLOC_FLOOR         = 0.05    # minimum allocation per fund (Phase 6)
ALLOC_CAP           = 0.20    # maximum allocation per fund (Phase 6)

# ── s_risk_adjusted sub-weights (must sum to 1.0) ─────────────────────────────
RISK_WEIGHTS = {
    "sharpe_5y":  0.45,
    "sortino_3y": 0.35,
    "sharpe_3y":  0.20,
}

# ── Profile weight table ──────────────────────────────────────────────────────
PROFILE_WEIGHTS = {
    "conservative": {"s_10Y": 0.25, "s_5Y": 0.15, "s_3Y": 0.05,
                     "s_risk_adjusted": 0.32, "s_consistency": 0.23},
    "moderate":     {"s_10Y": 0.18, "s_5Y": 0.29, "s_3Y": 0.10,
                     "s_risk_adjusted": 0.28, "s_consistency": 0.15},
    "aggressive":   {"s_10Y": 0.10, "s_5Y": 0.33, "s_3Y": 0.30,
                     "s_risk_adjusted": 0.17, "s_consistency": 0.10},
}
```

---

### Section 1 — Data Loading

**Inputs:**

| Source | What it provides |
|--------|-----------------|
| `mutualfunds/all_funds_moneycontrol.tsv` | Returns (1W–10Y), Crisil rating, Category |
| `mutualfunds/raw_funds.tsv` | ISIN ↔ scheme code mapping |
| `mutualfunds/fund_info/risk_metrics_{isin}.tsv` | Sharpe 3Y/5Y, Sortino 3Y, category averages |
| `mutualfunds/fund_info/holdings_{isin}.tsv` | Stock holdings with weights (for overlap) |

Load risk_metrics and holdings for all ISINs in the MoneyControl universe (not just those passing filters — loading upfront avoids re-scanning later). Report: fund count loaded, ISINs with missing risk_metrics, ISINs with missing holdings.

---

### Section 2 — Phase 0: Universe Eligibility

Hard gates applied in order. Each drops funds permanently.

1. `crisil_rating` is non-null and `≥ CRISIL_MIN`
2. `return_5y` is non-null (fund has at least 5-year history)
3. ISIN has a loadable holdings file (required for Phase 5 overlap)

**Report:** fund count before → after each gate, with dropout reasons.

---

### Section 3 — Phase 1: Tier Assignment

```
Tier A: return_10y is non-null AND return_5y is non-null
Tier B: return_5y is non-null AND return_10y is null
```

Tier C (3Y-only) is excluded — no Crisil rating available and insufficient history.

**Report:** tier count by category table.

---

### Section 4 — Phase 2: Factor Score Computation

All output scores are 0–100. Percentile computation uses `within-category` by default; falls back to tier-wide if category count < `MIN_CATEGORY_SIZE`.

**4a. `s_10Y`**
- Tier A only. `percentile_rank(return_10y)` within `[category ∩ Tier A]`.
- Tier B funds: `s_10Y = NaN` (handled in Phase 3, not imputed here).

**4b. `s_5Y`**
- All funds. `percentile_rank(return_5y)` within `[category]`.

**4c. `s_3Y`**
- All funds. `percentile_rank(return_3y)` within `[category]`.

**4d. `s_risk_adjusted`**
```python
# 1. Percentile-normalise each metric within category
sharpe_5y_pct  = percentile_rank(sharpe_5y,  within=category)
sortino_3y_pct = percentile_rank(sortino_3y, within=category)
sharpe_3y_pct  = percentile_rank(sharpe_3y,  within=category)

# 2. Handle missing sharpe_5y: redistribute 0.45 weight to remaining two
#    (sharpe_5y absent → sortino_3y gets 0.64, sharpe_3y gets 0.36)

# 3. Weighted blend
s_risk_adjusted = (RISK_WEIGHTS["sharpe_5y"]  * sharpe_5y_pct  +
                   RISK_WEIGHTS["sortino_3y"] * sortino_3y_pct +
                   RISK_WEIGHTS["sharpe_3y"]  * sharpe_3y_pct)
```

**4e. `s_consistency`**
```python
# Returns vector: use whichever horizons are available
# For Tier A: [r_1y, r_2y, r_3y, r_5y, r_10y]
# For Tier B: [r_1y, r_2y, r_3y, r_5y]
cv = std(returns_vector) / mean(returns_vector)

# Cap at 99th percentile to prevent instability near zero mean
cv_capped = min(cv, np.percentile(all_cvs, 99))

# Invert and percentile-rank within category (lower CV = more consistent = higher score)
s_consistency = percentile_rank(1 / cv_capped, within=category)
```

---

### Section 5 — Phase 3: Profile-Driven Composite Score

```python
weights = PROFILE_WEIGHTS[PROFILE].copy()

for each fund:
    w = weights.copy()

    # Tier B: redistribute s_10Y weight to s_5Y and s_3Y only
    if fund.tier == "B":
        w10, w5, w3 = w["s_10Y"], w["s_5Y"], w["s_3Y"]
        w["s_5Y"]  = w5 + w10 * (w5 / (w5 + w3))
        w["s_3Y"]  = w3 + w10 * (w3 / (w5 + w3))
        w["s_10Y"] = 0.0
        # s_risk_adjusted and s_consistency unchanged

    composite = sum(w[f] * fund.scores[f]
                    for f in w if fund.scores[f] is not NaN)
```

**Report:** full score breakdown table — all five factor scores + composite, sorted by composite descending. Include tier and category columns.

---

### Section 6 — Phase 4: Category-Aware Shortlisting

Within each category, take the top `CATEGORY_CAP` funds by composite score. No minimum per category — if a category has no funds scoring well, it contributes zero funds (forcing inclusion of a weak category hurts the portfolio).

**Report:** shortlist table with fund count per category.

---

### Section 7 — Phase 5: Overlap-Constrained Portfolio Selection

**Overlap computation:**
```
overlap(i, j) = Σ  min(weight_ik, weight_jk)   for all stocks k in union of holdings
```

**Objective:** Select final set `S` from the shortlist that:
- Maximises `Σ composite_score_i` (primary objective)
- Subject to: `overlap(i, j) ≤ OVERLAP_THRESHOLD` for all pairs `i, j ∈ S`

Algorithm: backtracking with branch-and-bound (carried over from `portfolio_manager_v2`). Explicit objective must be `Σ composite_score_i` — not fund count maximisation.

**Report:** selected fund list with composite scores; pairwise overlap matrix for selected funds.

---

### Section 8 — Phase 6: Score-Proportional Allocation

```python
# Raw allocation proportional to composite score
raw = {fund: score / sum(scores.values()) for fund, score in scores.items()}

# Iterative clip-and-renormalize
alloc = raw.copy()
while True:
    clipped = {f: max(ALLOC_FLOOR, min(ALLOC_CAP, a)) for f, a in alloc.items()}
    total = sum(clipped.values())
    renormed = {f: v / total for f, v in clipped.items()}
    if renormed == alloc:
        break
    alloc = renormed
```

---

### Section 9 — Final Portfolio Output

1. **Portfolio table** — fund name, AMC, category, tier, composite score, all 5 factor scores, allocation %
2. **Allocation bar chart** — sorted by allocation descending, coloured by category
3. **Factor score heatmap** — funds × {s_10Y, s_5Y, s_3Y, s_risk_adjusted, s_consistency}, 0–100 scale
4. **Pairwise overlap matrix** — heatmap for selected funds with OVERLAP_THRESHOLD line
5. **Portfolio summary** — weighted-average composite score; weighted-average per factor; return/risk cluster split for chosen profile
