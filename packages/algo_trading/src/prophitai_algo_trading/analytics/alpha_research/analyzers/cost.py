"""Cost-breakeven analyzer.

Sweeps a grid of ``cost_per_turnover`` values, computes total return at
each, and interpolates the cost where total return crosses zero. The
resulting ``cost_breakeven_bps`` is the maximum frictional cost the
alpha can absorb before becoming a money-loser — a more honest
production-readiness number than a single-point cost-drag figure.

Three regimes:
  - Alpha negative even at zero cost → breakeven is undefined (returned
    as ``None``); the alpha doesn't make money frictionless.
  - Alpha still profitable at the highest grid cost → breakeven is
    above the grid; the function returns ``float('inf')`` so the agent
    knows the alpha is robust beyond the tested range.
  - Alpha crosses zero somewhere within the grid → linear interpolation
    on the bracketing pair gives the breakeven cost in bps.
"""

from __future__ import annotations

import pandas as pd


BPS_PER_UNIT = 10_000.0  # 1 bp = 0.0001 in decimal


#     ================================
# --> Helper funcs
#     ================================

def _total_return_at_cost(
    pre_cost_returns: pd.Series, turnover: pd.Series, cost_bps: float,
) -> float:
    """Total compounded return when cost is ``cost_bps`` bps per turnover.

    Returns the result as a percentage (e.g., 12.34 means +12.34%).
    """
    cost_decimal = cost_bps / BPS_PER_UNIT
    bar_returns = pre_cost_returns - turnover * cost_decimal

    return float((1.0 + bar_returns.fillna(0.0)).prod() - 1.0) * 100.0


def _interpolate_breakeven(
    cost_low: float, return_low: float,
    cost_high: float, return_high: float,
) -> float:
    """Linear interpolation: cost where return crosses zero.

    Assumes ``return_low > 0 > return_high`` and ``cost_low < cost_high``.
    Returns the cost in bps.
    """
    span = return_low - return_high

    if span <= 0.0:
        return cost_high

    fraction = return_low / span

    return cost_low + fraction * (cost_high - cost_low)

def _find_breakeven(cost_curve: dict[float, float]) -> float | None:
    """Locate the breakeven cost in a sorted ``{cost: return}`` dict.

    Walks the grid looking for the first cost where return drops from
    non-negative to negative; interpolates between that pair.
    """
    items = sorted(cost_curve.items())

    if not items:
        return None

    _, first_return = items[0]

    if first_return < 0.0:
        return None

    for (low_cost, low_ret), (high_cost, high_ret) in zip(items[:-1], items[1:]):
        if low_ret >= 0.0 > high_ret:
            return round(
                _interpolate_breakeven(low_cost, low_ret, high_cost, high_ret),
                2,
            )

    _, last_return = items[-1]

    if last_return >= 0.0:
        return float("inf")

    return None

#     ================================
# --> Public analyzer
#     ================================

def compute_cost_breakeven(
    pre_cost_returns: pd.Series,
    turnover: pd.Series,
    cost_curve_bps: tuple[float, ...],
) -> dict[str, float | dict[float, float] | None]:
    """Cost-breakeven analysis across a grid of friction levels.

    Args:
        pre_cost_returns: Per-bar portfolio return *before* turnover cost.
        turnover: Per-bar absolute weight delta summed across tickers.
        cost_curve_bps: Cost grid (basis points). Must be non-empty and
            non-negative; sorted internally.

    Returns:
        Dict with keys:
            ``cost_curve``: ``{cost_bps: total_return_pct}`` for every
                grid point.
            ``cost_breakeven_bps``: Interpolated breakeven cost. ``None``
                when the alpha is unprofitable at zero cost; ``inf``
                when the alpha is still profitable at the grid maximum.
    """
    grid = sorted(cost_curve_bps)

    cost_curve: dict[float, float] = {}

    for cost_bps in grid:
        cost_curve[cost_bps] = round(
            _total_return_at_cost(pre_cost_returns, turnover, cost_bps), 2,
        )

    breakeven = _find_breakeven(cost_curve)

    return {
        "cost_curve": cost_curve,
        "cost_breakeven_bps": breakeven,
    }

