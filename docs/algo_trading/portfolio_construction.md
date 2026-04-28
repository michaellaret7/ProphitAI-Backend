# Portfolio Construction

A `PortfolioConstructor` (PCM) turns a list of `Insight`s into a list of `PortfolioTarget`s.  This is the step that:

- Decides **which symbols** make the book.
- Decides **how much capital** each position gets.
- Owns the **rebalance cadence**.
- Enforces **per-position caps** and gross exposure.

Four built-in PCMs cover the common patterns; they all live in `portfolio_construction/`.

## Protocol

```python
class PortfolioConstructor(Protocol):
    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]: ...
```

### Return-value semantics

- Return the **full desired book** for this bar.
- Symbols not in the returned list are **left alone** (existing positions don't close automatically — Execution diffs against the returned list).
- To close a position, emit an explicit `PortfolioTarget(symbol, target_shares=0.0)`.
- The built-in helper `append_close_orphans(ctx, targets)` appends zero-share targets for every currently-invested symbol not already in your list.  All four built-ins call it.

## Shared helpers — `portfolio_construction/helpers.py`

These are not part of the public API but they're what you use when building a custom PCM.

### `dedupe_insights(insights)`

Collapse multi-alpha insights per symbol to one, keeping the highest `|direction * magnitude|`.  Use this when your PCM expects one insight per symbol.

### `cross_sectional_zscore(values, winsor_at=3.0)`

Z-score a `{symbol: value}` dict using sample std-dev.  Clips to ±`winsor_at`.  Fewer than 3 values or zero variance → all zeros.  Missing/`None` values also map to 0.

### `RebalanceScheduler(rebalance_every)`

Gates PCMs to only emit targets on rebalance bars.  `rebalance_every=None` means "every bar".  Usage:

```python
self._scheduler = RebalanceScheduler(rebalance_every=timedelta(days=5))

def create_targets(self, ctx, insights):
    if not self._scheduler.is_rebalance_bar(ctx.timestamp):
        return []
    ...
```

**Note**: returning `[]` on non-rebalance bars means "don't touch anything" — positions stay as-is (Execution won't close what's not in the target list).

### `weight_to_shares(ctx, symbol, weight, direction)`

The **canonical** conversion from an intent weight (decimal % of equity) to signed target shares.  Every built-in PCM uses this so conversion semantics stay identical:

```python
target_shares = (equity * weight * direction) / price
```

Returns `None` if the symbol has no price data or price ≤ 0.  Handle the `None` case by skipping the target.

### `append_close_orphans(ctx, targets)`

For every currently-invested symbol NOT already in `targets`, append `PortfolioTarget(symbol, 0.0)` so Execution closes it.  Idempotent.

## Built-in PCMs

### `EqualWeightConstructor`

Simplest usable PCM.  Ranks insights by `|direction * magnitude|`, picks the top N most confident, splits gross exposure equally among them.  Longs and shorts land in the same N.

```python
EqualWeightConstructor(
    max_positions=10,               # cap across both sides
    gross_exposure=1.0,             # total absolute weight
    rebalance_every=None,           # None = every bar (high turnover)
)
```

Use for: sanity baselines; alphas whose magnitudes are too noisy to weight by.

### `InsightWeightedConstructor`

Magnitude-proportional sizing with a per-position cap:

```python
weight_i = magnitude_i / sum(magnitudes) * gross_exposure
weight_i = min(weight_i, per_position_cap)
```

```python
InsightWeightedConstructor(
    gross_exposure=1.0,
    per_position_cap=0.10,
    max_positions=None,             # optional truncation
    rebalance_every=None,
)
```

Reads `Insight.weight` first, falls back to `Insight.magnitude`, then `1.0` — lets an alpha emit explicit per-symbol weight hints when it has them.

### `MagnitudeWeightedLongShortConstructor`

The workhorse L/S builder.  Decile-cut, dollar-neutral, magnitude-weighted within each side:

1. Rank by signed score (`direction * magnitude`).
2. Take top `quantile` as longs, bottom `quantile` as shorts.
3. Filter by `min_abs_score` to drop weak signals.
4. Within each side, weight by `|score| / sum(|score|)`.
5. Rescale sides to the SMALLER side's gross, enforcing dollar-neutrality.
6. Cap per-position at `per_position_cap`.

```python
MagnitudeWeightedLongShortConstructor(
    gross_exposure=2.0,             # 2.0 = 100% long + 100% short
    per_position_cap=0.10,
    quantile=0.10,                  # decile cut; must be in (0, 0.5]
    min_abs_score=0.20,             # signed-score threshold
    rebalance_every=None,
)
```

Expects **one insight per symbol** as input — typically wrapped by `MultiAlphaBlender`.

### `MultiAlphaBlender`

The composite PCM for multi-alpha portfolios.  Pipeline:

1. Partition incoming insights by `source_alpha`.
2. Cross-sectionally z-score each alpha's `direction * magnitude` (winsorize at ±3σ).
3. Weighted-sum the z-scored values per symbol using the static `weights` dict.
4. Synthesize a single list of "blended" Insights (`source_alpha="blended"`, magnitude = `|composite|`).
5. Delegate to an **inner PCM** for the actual target construction.

```python
MultiAlphaBlender(
    weights={
        "momentum":   0.40,
        "breakout":   0.20,
        "reversal":   0.20,
        "low_vol":    0.20,
    },
    inner=MagnitudeWeightedLongShortConstructor(
        gross_exposure=1.5,
        per_position_cap=0.08,
        quantile=0.15,
    ),
    winsor_at=3.0,                  # None disables winsorization
)
```

Weights are **not** re-normalized — negative weights flip a signal's contribution; summing to ≠ 1 tilts the blended magnitude scale.

`inner` is any `PortfolioConstructor` — blend into `EqualWeightConstructor`, `InsightWeightedConstructor`, or a custom one.

## Composition patterns

### Single alpha, L/S book

```python
Algorithm(
    alphas=[MomentumAlpha()],
    portfolio_construction=MagnitudeWeightedLongShortConstructor(
        gross_exposure=1.5,
        per_position_cap=0.10,
        rebalance_every=timedelta(days=7),
    ),
    ...
)
```

### Multi-alpha blended book

```python
Algorithm(
    alphas=[MomentumAlpha(), BreakoutAlpha(), LowVolAlpha()],
    portfolio_construction=MultiAlphaBlender(
        weights={"momentum": 0.5, "breakout": 0.3, "low_vol": 0.2},
        inner=MagnitudeWeightedLongShortConstructor(gross_exposure=1.5),
    ),
    ...
)
```

### Single alpha, conviction-weighted long-only

```python
Algorithm(
    alphas=[MomentumAlpha()],
    portfolio_construction=InsightWeightedConstructor(
        gross_exposure=1.0,
        per_position_cap=0.15,
        max_positions=20,
    ),
    ...
)
```

## Writing a custom PCM

Use the shared helpers; don't hand-roll the equity/price math.

```python
from datetime import timedelta
from prophitai_algo_trading.core.models import (
    AlgorithmContext, Insight, PortfolioTarget,
)
from prophitai_algo_trading.portfolio_construction.helpers import (
    RebalanceScheduler, append_close_orphans, dedupe_insights, weight_to_shares,
)


class MyPCM:
    def __init__(self, rebalance_every=timedelta(days=5)):
        self._scheduler = RebalanceScheduler(rebalance_every)

    def create_targets(self, ctx, insights):
        if not self._scheduler.is_rebalance_bar(ctx.timestamp):
            return []

        active = [i for i in dedupe_insights(insights) if i.direction != 0]

        if not active:
            return append_close_orphans(ctx, [])

        # your weighting logic
        per_weight = 1.0 / len(active)

        targets = []
        for insight in active:
            shares = weight_to_shares(ctx, insight.symbol, per_weight, insight.direction)
            if shares is None:
                continue
            targets.append(PortfolioTarget(insight.symbol, shares))

        return append_close_orphans(ctx, targets)
```

Key points:

- Always go through `weight_to_shares` for the price/equity math.
- Always `append_close_orphans` before returning so you don't leak stale positions.
- If you gate on rebalance cadence, return `[]` on non-rebalance bars.  **Do not return `append_close_orphans(ctx, [])`** on non-rebalance bars — that would flatten everything every skipped bar.
