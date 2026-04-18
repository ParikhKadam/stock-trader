# Notebook Walkthrough — `mutual_fund_portfolio.ipynb`

> Cell-by-cell explanation of what each cell does and how it works.

---

## Cell 1 — Title (markdown)
Just documentation. Links to the design plan.

---

## Cell 2 — Configuration

Every tunable number in one place. Change `PROFILE` here and re-run; nothing else needs touching.

Key things to understand:

- `MIN_CATEGORY_SIZE = 5` — if a category has fewer than 5 funds in the comparison group, percentile ranking within it would be noisy (1st of 3 is not the same as 1st of 20). The code falls back to ranking within the full tier pool instead.
- `MAX_PORTFOLIO_SIZE = 10` — the optimizer stops adding funds once it has 10. Without this cap the optimizer selected 22 funds (adding any low-overlap fund always increases the score sum).
- `ALLOC_FLOOR = 0.05, ALLOC_CAP = 0.20` — no fund gets less than 5% or more than 20% of the portfolio. With 10 funds the floor requires 50%, leaving 50% headroom for score-proportional differentiation. With 22 funds the floor required 110%, which is impossible — everything collapsed to a flat 4.5%.
- `PROFILE_WEIGHTS` — the full weight table for all three profiles. The `assert` at the bottom verifies each row sums exactly to 1.0.

---

## Cell 3 — Imports

Standard. `FACTOR_COLS = ["s_10Y", "s_5Y", "s_3Y", "s_risk_adjusted", "s_consistency"]` is defined here as a shared constant used in every display, heatmap, and weighted-average computation downstream.

---

## Cell 5 — Load MoneyControl data

Reads `all_funds_moneycontrol.tsv` (924 funds).

**Return column parsing.** The file stores returns as strings like `"18.5%"`. The loop strips the `%` and converts to float. Anything unparseable (blank cells, `"-"`) becomes `NaN`. NaN is how the code later decides tier assignment and whether `s_10Y` exists.

**`_short` name cleaning.** `clean_name()` strips `" - Direct Plan..."` and `" - Growth..."` suffixes using regex. This is the join key between MoneyControl and raw_funds. Both files have the same verbose scheme names but the API version may have slightly different suffixes — cleaning both to a common base is what makes the join work.

---

## Cell 6 — ISIN join

`raw_funds.tsv` is the only file that has ISINs. Without an ISIN you cannot reach `fund_info/` (all files there are named `holdings_{ISIN}.tsv` and `risk_metrics_{ISIN}.tsv`).

The join: clean both names the same way → build a dict `{cleaned_name: isin}` from raw_funds → map it onto the MoneyControl dataframe. After this every fund row has an ISIN attached.

---

## Cell 8 — Phase 0: Four hard gates

Funds are dropped permanently here if they fail any gate. The order matters — each gate shrinks the pool before the next check.

1. **ISIN exists** — no ISIN means no holdings file, so the fund is unusable.
2. **Crisil ≥ 4** — eliminates the bottom ~68% of each category. Crisil is a noisy backward-looking signal, but using it as a quality floor to exclude genuinely weak funds is valid. Crisil is NOT scored as a factor (that would double-count it — the gate already does the screening job).
3. **5Y return exists** — excludes funds younger than 5 years. Ensures everyone in the universe has comparable medium-term history.
4. **Holdings file exists** — without a holdings file the fund cannot participate in overlap computation. By gating here (rather than at Phase 5), the scoring universe used for percentile computation in Phase 2 only contains funds that can actually appear in the final portfolio. Previously this check happened at Phase 5, silently wasting shortlist slots.

---

## Cell 10 — Phase 1: Tier assignment

Simple rule applied row by row:
- **Tier A**: has both `10Y` and `5Y` — full history, all five factors available.
- **Tier B**: has `5Y` but not `10Y` — shorter history, `s_10Y` will be NaN.

Tier C (3Y only) is unreachable because gate 3 already required 5Y. The tier affects two things downstream: which comparison group is used for `s_10Y` percentile ranking (Tier A funds only), and how Phase 3 adjusts weights for Tier B funds.

---

## Cell 12 — Percentile rank helpers

Two functions that everything else calls.

**`pct_rank(series)`** — wraps pandas `.rank(pct=True)`. Returns 0–100 instead of 0–1. NaN inputs stay NaN (`na_option="keep"`). `method="average"` means ties share their average rank rather than being assigned arbitrarily.

**`within_cat_pct(df, col, mask, min_size)`** — the key function:

1. `source = df[mask]` if a mask is provided, else all of `df`. For `s_10Y` the mask is `tier == "A"`, so only Tier A funds form the comparison pool.
2. Compute `global_pct = pct_rank(source[col])` — tier-wide fallback.
3. Loop over each category group within `source`. If that category has ≥ `min_size` non-null values, use within-category rank. Otherwise use `global_pct` for those rows.
4. Write results back into a Series indexed to `df` (not just `source`) — so Tier B funds get NaN for `s_10Y` because they are not in the Tier A source group at all.

---

## Cell 13 — s_10Y, s_5Y, s_3Y

Three calls to `within_cat_pct`.

- `s_10Y` gets `mask=tier_a` — only Tier A funds compete with each other on 10Y return. Tier B funds get NaN here.
- `s_5Y` and `s_3Y` use no mask — all eligible funds compete within their category.

**Why within-category and not cross-fund?** A large-cap fund returning 14% over 5Y is excellent for its category. The same number for a small-cap fund is mediocre. Cross-fund percentiles would systematically rank small/mid-cap funds higher on returns, so the category cap in Phase 4 would be doing bias correction instead of diversification. Within-category percentiles fix the comparison at the source.

---

## Cell 14 — Load risk metrics

For each ISIN in the eligible universe, opens `fund_info/risk_metrics_{ISIN}.tsv` and reads three numbers: `sharpe_3y`, `sharpe_5y`, `sortino_3y`. Anything missing becomes NaN.

The warning about missing risk metrics reflects that `fetch_fund_information.py` was only run for a subset of the eligible universe — those files only exist for ISINs fetched under the old pipeline. Running the fetch script for all eligible ISINs would populate those files. The code handles missing data gracefully but flags it.

---

## Cell 15 — s_risk_adjusted

Three steps:

**Step 1: Percentile-normalise each raw metric within category.** Sharpe and Sortino are raw ratios — a Sharpe of 1.2 vs 0.8 has different meaning in different categories (small-cap funds naturally have higher Sharpe than large-cap in bull markets). Making them within-category percentiles puts them on a comparable 0–100 scale.

**Step 2: Blend.**
```
s_risk_adjusted = 0.45 × Sharpe_5Y_pct + 0.35 × Sortino_3Y_pct + 0.20 × Sharpe_3Y_pct
```
Sharpe 5Y gets the most weight — it is the most stable signal (less noise from a single bad year). Sortino 3Y captures downside-specific risk, which Sharpe does not distinguish. Sharpe 3Y adds recency but is the noisiest, so gets the least weight.

**Step 3: Handle missing components.** `blend_risk()` collects only non-NaN components, rescales their weights to sum to 1.0, and blends. If all three are missing the function returns NaN, which triggers the warning at the bottom of the cell.

**Note on NaN propagation to Phase 3:** When `s_risk_adjusted` is NaN for a fund, its 28% weight (moderate profile) redistributes to the other four factors in the composite score. This means funds with and without risk data are scored on effectively different weight profiles — they are not fully comparable. The warning text directs you to fix this by running the fetch script.

---

## Cell 16 — s_consistency

**What it measures:** Not traditional volatility — there are no per-year NAV series in the dataset. It measures *horizon consistency*: does this fund perform well across multiple time frames, or does it spike in one period and lag in another?

**How:**
1. For each fund, collect `{1Y, 2Y, 3Y, 5Y}` returns (plus `10Y` for Tier A).
2. Compute `CV = std / |mean|` over those values. A fund with 15%, 16%, 17%, 18% across horizons has low CV (consistent). A fund with 4%, 25%, 9%, 20% has high CV (erratic across time frames).
3. Cap CV at the 99th percentile before inversion — prevents a fund with near-zero mean return from producing an infinite inverse-CV and dominating the percentile.
4. Invert (`1 / CV_capped`) so lower CV → higher score.
5. Percentile-rank within category.

---

## Cell 17 — Factor score summary

Display only. Renders a styled table of the top 40 funds sorted by `s_5Y`, with green gradient shading on all five factor columns. Useful for sanity-checking: do high-return funds also score well on risk? Are there funds with great returns but poor consistency? No logic runs here.

---

## Cell 19 — Phase 3: Composite score

Two functions:

**`effective_weights(tier)`** — returns the weight dict for a fund's tier. For Tier A it is the profile weights unchanged. For Tier B, it pops `s_10Y` and redistributes its weight proportionally to `s_5Y` and `s_3Y` only:

```
s_5Y_eff = s_5Y_base + s_10Y_base × (s_5Y_base / (s_5Y_base + s_3Y_base))
s_3Y_eff = s_3Y_base + s_10Y_base × (s_3Y_base / (s_5Y_base + s_3Y_base))
```

For moderate profile: `s_10Y = 0.18, s_5Y = 0.29, s_3Y = 0.10` → Tier B gets `s_5Y = 0.424, s_3Y = 0.146`. The risk and consistency weights are untouched — missing 10Y is a return data gap, not a risk data gap.

**`composite_score(row)`** — iterates over the effective weights, skips any factor where the fund's score is NaN, renormalises the available weights to sum to 1.0, and returns the weighted average. This single number is used for ranking, shortlisting, and allocation.

---

## Cell 21 — Phase 4: Category shortlisting

```python
universe
  .sort_values("composite", ascending=False)   # rank all eligible funds by score
  .groupby("Category Name", group_keys=False)
  .head(CATEGORY_CAP)                          # take top 3 within each category
  .sort_values("composite", ascending=False)   # re-sort the shortlist for display
```

Produces at most `N_categories × CATEGORY_CAP` funds. The "no minimum per category" design means a category with no strong funds contributes nothing — you do not force a weak fund in just to tick a diversification box.

---

## Cell 23 — Load holdings

For each shortlisted ISIN, reads `fund_info/holdings_{ISIN}.tsv`.

The holdings file has multiple rows per stock because it stores monthly snapshots (Oct24, Nov24, ..., Aug25). Grouping by `stock_name` and summing `weight` across all months, then normalising the total to 1.0, gives the average weight per stock across the observed periods. This smooths out month-to-month rebalancing noise.

Result: `holdings_map = { ISIN: { "Larsen & Toubro": 0.094, "Treps": 0.092, ... } }` where weights are fractions summing to 1.0.

The safety-net warning at the bottom handles the edge case where a file disappeared after Phase 0 ran.

---

## Cell 24 — Pairwise overlap matrix

For every pair `(i, j)` in the shortlist:

```
overlap(i, j) = Σ  min(weight_i[stock], weight_j[stock])   for all common stocks  ×  100
```

This is the Sørensen overlap coefficient. If fund A holds HDFC Bank at 8% and fund B holds it at 5%, they share 5% on that stock. Sum across all shared stocks gives total overlap as a percentage.

If either fund has an empty holdings dict: returns 50% (neutral fallback — neither zero nor full overlap). Stored in a symmetric `n×n` DataFrame with 100% on the diagonal.

---

## Cell 25 — Optimizer

Recursive backtracking with branch-and-bound pruning.

**Setup:** Funds are sorted by composite score descending (`sorted_isins`). Higher-scoring funds are tried first, which helps B&B find a good solution early and prune aggressively.

**`backtrack(current, start, cur_score)` — step by step:**

1. If the current selection beats `best_score`, record it. This captures partial portfolios — the best 7-fund set is recorded even if we are trying for 10, in case no 10-fund set satisfies all overlap constraints.
2. If `len(current) == MAX_PORTFOLIO_SIZE`: stop recursing. This is the size cap.
3. Compute `future_ub`: sum the scores of the top `slots_left` remaining funds, ignoring overlap. This is an upper bound — overlap may prevent actually including all of them. If `cur_score + future_ub ≤ best_score`, prune this branch entirely.
4. For each remaining fund from `start` onwards: if it violates overlap with any already-selected fund, skip it. Otherwise add it, recurse, then remove it (backtrack).

The pruning in step 3 is what makes this fast. Without it a naive exhaustive search over C(27, 10) = 8,436,285 combinations would be required. B&B typically explores only a few thousand paths because most branches get pruned after the first few good solutions are found.

---

## Cell 27 — Phase 6: Allocation

**Raw allocation:** Each fund's composite score divided by the total. A fund scoring 90 naturally gets `90 / Σ scores` of the portfolio.

**`clip_and_renormalize` — iterative loop:**

1. Normalise weights to sum to 1.0.
2. Clip every weight to `[ALLOC_FLOOR, ALLOC_CAP]`.
3. If nothing changed (all weights already within bounds), stop. Otherwise go back to step 1.

Why iterative? Clipping changes the sum, so you must renormalise. But renormalising may push some weights back outside the bounds (e.g. a capped fund's weight falls below floor after renormalisation). The loop converges in typically 2–4 iterations. Convergence check: `abs(clipped[k] - w[k]) < 1e-9` for all k.

With 10 funds: `10 × 5% floor = 50%`, leaving 50% headroom for the cap and score-proportional differentiation to work meaningfully.

---

## Cell 29 — Final portfolio table

Assembles the display DataFrame from `selected`. Key points:

- Index starts at 1 (fund rank by allocation descending).
- `Alloc %` = `allocation × 100` rounded to 1 decimal.
- Green gradient on `Alloc %` and `composite` to quickly spot dominant positions and strongest-scoring funds.
- Weighted-average factor scores printed below — shows the portfolio's overall profile, e.g. whether you got high-consistency funds or just high-return funds.

---

## Cell 31 — Allocation bar chart

Horizontal bars, funds sorted by allocation (highest at top). Each bar is coloured by category using the `tab20` palette. The legend maps colours to categories. `bar_label` annotates each bar with its percentage.

---

## Cell 32 — Factor score heatmap

`portfolio.set_index("Fund")[FACTOR_COLS]` creates a matrix of funds × factors. `seaborn.heatmap` with `vmin=0, vmax=100` and the `YlGn` colormap. Annotations show the raw 0–100 percentile score per cell.

Reading it: a fund that is dark across all five columns is a genuine all-rounder. A fund dark on `s_3Y` but missing `s_10Y` is a Tier B fund with strong recent momentum but no long-term track record — weight this knowledge into your final decision.

---

## Cell 33 — Overlap heatmap

Takes only the selected funds' rows and columns from `overlap_df`. `mask=diag_mask` hides the 100% self-overlap diagonal so it does not wash out the colour scale. `vmax=60` (not 100) because 100% only appears on the diagonal — setting the ceiling at 60% makes colour differences between 10% and 40% pairs clearly visible.

---

## Cell 34 — Export

Writes the portfolio to `portfolio_{PROFILE}.tsv` in the same directory. Named by profile so running with different profiles does not overwrite each other. The `allocation` float column is dropped — `Alloc %` already captures it in rounded form.
