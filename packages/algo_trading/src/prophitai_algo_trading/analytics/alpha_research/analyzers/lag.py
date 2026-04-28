"""Execution-lag sensitivity analyzer.

Re-runs the per-bar return computation with weights shifted by extra
bars and reports Sharpe + total return at each lag. Lag-1 is the
baseline (the canonical ``weights.shift(1) * asset_returns`` used by
``VectorBacktest``); higher lags simulate the case where the signal
arrives later than expected — a standard robustness check.

If lag-2 or lag-3 nukes the Sharpe, the alpha is unrealistically fast
and probably wouldn't survive realistic execution. ``lag_sharpe_decay``
is the single-scalar headline ratio of ``sharpe(max_lag) / sharpe(1)``,
suitable for the multi-alpha summary table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _annualized_sharpe(returns: pd.Series) -> float:
    """Annualized Sharpe of a per-bar return series, no risk-free rate.

    Uses log returns on (1 + r). Returns 0.0 for degenerate inputs.
    """
    clean = returns.dropna()

    if len(clean) < 2:
        return 0.0

    span_seconds = (clean.index[-1] - clean.index[0]).total_seconds()
    years = max(span_seconds / SECONDS_PER_YEAR, EPSILON)
    bars_per_year = len(clean) / years

    log_returns = np.log1p(clean)
    std = float(log_returns.std())

    if std <= EPSILON:
        return 0.0

    mean = float(log_returns.mean())

    return float(mean / std * np.sqrt(bars_per_year))


def _bar_returns_at_lag(
    weights: pd.DataFrame,
    asset_returns: pd.DataFrame,
    turnover: pd.Series,
    cost_per_turnover: float,
    lag: int,
) -> pd.Series:
    """Per-bar portfolio return with execution lagged by ``lag`` bars.

    ``cost_per_turnover * turnover`` stays unchanged across lags — cost
    is incurred at rebalance regardless of when the lagged weights
    actually start earning. This matches the standard lag-sensitivity
    convention in the literature.
    """
    pre_cost = (weights.shift(lag) * asset_returns).sum(axis=1).fillna(0.0)

    if cost_per_turnover > 0.0:
        return pre_cost - turnover * cost_per_turnover

    return pre_cost


#     ================================
# --> Public analyzer
#     ================================

def compute_lag_sensitivity(
    weights: pd.DataFrame,
    asset_returns: pd.DataFrame,
    turnover: pd.Series,
    bar_returns: pd.Series,
    cost_per_turnover: float,
    lag_horizons: tuple[int, ...],
) -> dict[int, dict[str, float]]:
    """Per-lag Sharpe + total return.

    Lag-1 is computed from the supplied ``bar_returns`` directly (it's
    the baseline already produced by ``VectorBacktest``); lag-k for
    k > 1 re-runs the returns op with ``weights.shift(k)``.

    Args:
        weights: ``[date x ticker]`` cadence-aligned PCM weights.
        asset_returns: ``[date x ticker]`` per-bar asset returns.
        turnover: Per-bar absolute weight delta summed across tickers.
        bar_returns: Existing post-cost lag-1 portfolio return series.
        cost_per_turnover: Linear turnover penalty applied identically
            at every lag.
        lag_horizons: Lags to evaluate. Must include 1 (validated by
            ``AnalyticsConfig``).

    Returns:
        ``{lag: {"sharpe": ..., "total_return_pct": ...}}``.
    """
    out: dict[int, dict[str, float]] = {}

    for lag in lag_horizons:
        if lag == 1:
            series = bar_returns
        else:
            series = _bar_returns_at_lag(
                weights, asset_returns, turnover, cost_per_turnover, lag,
            )

        sharpe = _annualized_sharpe(series)
        total_return = float((1.0 + series.fillna(0.0)).prod() - 1.0) * 100.0

        out[lag] = {
            "sharpe": round(sharpe, 3),
            "total_return_pct": round(total_return, 2),
        }

    return out


def lag_sharpe_decay_ratio(
    lag_sensitivity: dict[int, dict[str, float]],
) -> float | None:
    """``sharpe(max_lag) / sharpe(1)`` — single-scalar decay headline.

    Returns ``None`` when lag-1 Sharpe is non-positive (decay is
    meaningless in that case — the alpha doesn't work even at the
    canonical lag).
    """
    if not lag_sensitivity:
        return None

    lags = sorted(lag_sensitivity.keys())
    base = lag_sensitivity[lags[0]]["sharpe"]
    tail = lag_sensitivity[lags[-1]]["sharpe"]

    if base <= 0.0:
        return None

    return round(tail / base, 3)
