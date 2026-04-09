---
name: multi_output_indicator
title: Multi-Output Custom BaseIndicator Pattern
description: Use when a custom indicator must write two or more output columns (e.g. return + regime string, middle/upper/lower bands).
created: 2026-04-09
updated: 2026-04-09
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

    def calculate(self) -> pd.DataFrame:
        # ... compute both columns ...
        self.df[self.return_output_column] = market_return
        self.df[self.regime_output_column] = regime
        return self.df
```

## Pitfalls
- **Never return a new DataFrame** — always modify `self.df` in-place and return it.
- **String-typed regime columns**: use `pd.Series("up", index=..., dtype="object")`
  to initialize, then `.mask()` for conditional overrides. Avoids dtype issues.
- **NaN warmup rows for regime**: decide a default label (e.g. `"up"`) for NaN
  return periods — document this in the docstring.

## Confirmed Patterns
- MarketStateIndicator (AQM52): regime uses `pd.Series.mask()` chained calls —
  start with "up", mask < 0 → "down_moderate", mask < severe → "down_severe".
  This is clean and avoids nested np.where for string labels.

## Revision Log
- 2026-04-09: Created after building MarketStateIndicator for AQM52 strategy.

