# Position Sizing Standard Library

The sizing module provides a standard library of categorized position sizers with a declarative spec system.

## Architecture

```
sizing/
  base.py              # BasePositionSizer ABC
  specs.py             # SizingSpec declarative config
  std_lib/             # Categorized sizer implementations
    equity/            # Equity-fraction sizers
      all_in.py        # AllInSizer
      fixed_quantity.py # FixedQuantitySizer
      percent_of_equity.py # PercentOfEquitySizer
    risk_based/        # Risk-budget sizers
      atr_risk.py      # ATRRiskSizer
    volatility/        # Volatility-aware sizers
      volatility_target.py # VolatilityTargetSizer
      inverse_volatility.py # InverseVolatilitySizer
    wrappers/          # Decorator sizers
      drawdown_scaled.py # DrawdownScaledSizer
```

## Available Sizers

| Class | Category | Description |
|-------|----------|-------------|
| `AllInSizer` | equity | Allocate all available cash |
| `FixedQuantitySizer` | equity | Fixed share count per trade |
| `PercentOfEquitySizer` | equity | Percentage of total equity |
| `ATRRiskSizer` | risk_based | Risk-budget sizing from ATR/stop distance |
| `VolatilityTargetSizer` | volatility | Target fixed volatility contribution |
| `InverseVolatilitySizer` | volatility | Inverse-volatility weighted allocation |
| `DrawdownScaledSizer` | wrappers | Scales down another sizer during drawdowns |

## SizingSpec

Declarative configuration for selecting a sizer with parameters:

```python
from prophitai_algo_trading.sizing import SizingSpec, PercentOfEquitySizer, ATRRiskSizer

# With direct class reference
spec = SizingSpec(sizer=PercentOfEquitySizer, params={"pct": 0.25})

# With drawdown wrapper
spec = SizingSpec(
    sizer=ATRRiskSizer,
    params={"risk_pct": 0.01, "atr_multiple": 1.5},
    wrapper="drawdown_scaled",
    wrapper_params={"soft_drawdown": 0.05, "hard_drawdown": 0.15},
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `sizer` | `str \| type[BasePositionSizer]` | Sizer class or identifier |
| `params` | `dict[str, Any]` | Constructor kwargs for the sizer |
| `wrapper` | `str \| type[BasePositionSizer] \| None` | Optional wrapper sizer |
| `wrapper_params` | `dict[str, Any]` | Wrapper kwargs (excluding `base_sizer`) |
| `description` | `str \| None` | Human-readable description |

## Adding a New Sizer

1. Create a new file in the appropriate `std_lib/` category folder
2. Inherit from `BasePositionSizer` and implement `calculate_shares()`
3. Import and re-export in the category's `__init__.py`
4. Import and re-export in `std_lib/__init__.py`
5. Add to the `__all__` list in `sizing/__init__.py`
