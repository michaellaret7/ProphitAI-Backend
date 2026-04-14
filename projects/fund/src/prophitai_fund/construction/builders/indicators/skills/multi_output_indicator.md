---
name: multi_output_indicator
title: Multi-Output Custom BaseIndicator Pattern
description: Use when a custom indicator must write two or more output columns (e.g. return + regime string, middle/upper/lower bands).
created: 2026-04-09
updated: 2026-04-10
---

# Multi-Output Custom BaseIndicator Pattern

## When to Use
When a manifest entry lists two or more `output_columns` for a single custom indicator.
Examples: MarketStateIndicator (market_return_252 + market_state_regime),
BollingerBandIndicator (bb_middle, bb_upper, bb_lower, bb_width).

## Procedure

1. Accept a separate `output_column` kwarg per output in `__init__` (e.g.
   `return_output_column`, `regime_output_column`).
2. Store each as an instance attribute before calling `super().__init__(df)`.
3. In `calculate()`, assign each output separately:
   `self.df[self.return_output_column] = ...`
   `self.df[self.regime_output_column] = ...`
4. Return `self.df` once at the end.
5. In `update_last_row()`, update each column on `self.df.loc[last_idx, col]`.
6. **Extract scalar regime logic into a helper** `_scalar_regime(ret)` so that
   `update_last_row()` can call it without duplicating threshold branches. This
   prevents drift between the batch and incremental paths.

## Code Template

```python
class MarketStateIndicator(BaseIndicator):
    def __init__(
        self,
        df: pd.DataFrame,
        window: int = 252,
        return_output_column: str = "market_return_252",
        regime_output_column: str = "market_state_regime",
        down_moderate_threshold: float = -0.15,
        down_severe_threshold: float = -0.25,
    ) -> None:
        self.window = window
        self.return_output_column = return_output_column
        self.regime_output_column = regime_output_column
        self.down_moderate_threshold = down_moderate_threshold
        self.down_severe_threshold = down_severe_threshold
        super().__init__(df)

    def _classify_regime(self, market_return: pd.Series) -> pd.Series:
        """Vectorized regime classification for calculate().
        
        CRITICAL: use self.down_moderate_threshold, NOT hardcoded 0.0.
        """
        regime = pd.Series("up", index=market_return.index, dtype="object")
        regime = regime.mask(market_return < self.down_moderate_threshold, "down_moderate")
        regime = regime.mask(market_return < self.down_severe_threshold, "down_severe")
        return regime

    def _scalar_regime(self, ret: float) -> str:
        """Scalar regime classification for update_last_row().
        
        Must mirror _classify_regime exactly — use same thresholds.
        """
        if math.isnan(ret):
            return "up"
        if ret < self.down_severe_threshold:
            return "down_severe"
        if ret < self.down_moderate_threshold:  # NOT 0.0!
            return "down_moderate"
        return "up"

    def calculate(self) -> pd.DataFrame:
        # ... compute both columns ...
        self.df[self.return_output_column] = market_return
        self.df[self.regime_output_column] = self._classify_regime(market_return)
        return self.df

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        self.df = new_df
        last_idx = self.df.index[-1]
        # ... compute scalar ret ...
        self.df.loc[last_idx, self.return_output_column] = ret
        self.df.loc[last_idx, self.regime_output_column] = self._scalar_regime(ret)
        return self.df
```

## Pitfalls
- **Never return a new DataFrame** — always modify `self.df` in-place and return it.
- **String-typed regime columns**: use `pd.Series("up", index=..., dtype="object")`
  to initialize, then `.mask()` for conditional overrides. Avoids dtype issues.
- **NaN warmup rows for regime**: `NaN < threshold` is `False` in pandas, so NaN rows
  naturally stay at the default "up" label. This is a conservative default that
  avoids blocking signals during warmup.
- **Duplicate threshold logic is a bug risk**: If `calculate()` and `update_last_row()`
  both implement regime logic independently, they can drift. Always factor shared
  logic into helpers (`_classify_regime` for Series, `_scalar_regime` for scalars).
- **CRITICAL threshold bug**: `_classify_regime` must use `self.down_moderate_threshold`
  (e.g. -0.15) as the 'up'/'down_moderate' boundary — NOT hardcoded `0.0`. Using 0.0
  classifies returns in (-0.15, 0.0) as 'down_moderate' when they should be 'up'.
  This was caught by code review in AQM52 build. Both `_classify_regime()` and
  `_scalar_regime()` must use the configured threshold consistently.

## Confirmed Patterns
- MarketStateIndicator (AQM52): regime uses `pd.Series.mask()` chained calls —
  start with "up", mask < down_moderate_threshold → "down_moderate",
  mask < down_severe_threshold → "down_severe".
  `_scalar_regime()` mirrors the vectorized logic for update_last_row().
- Code reviewer caught the 0.0 vs down_moderate_threshold bug — fixed by using
  `self.down_moderate_threshold` in both helpers.

## Revision Log
- 2026-04-09: Created after building MarketStateIndicator for AQM52 strategy.
- 2026-04-10: Added critical pitfall on threshold bug (0.0 vs down_moderate_threshold).
  Added `_scalar_regime()` helper pattern to avoid code duplication between
  calculate() and update_last_row(). Updated code template to use correct threshold.

