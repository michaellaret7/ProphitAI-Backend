"""Per-alpha analyzer pipeline.

Composes every per-alpha analyzer in ``analyzers/`` into a single
``AlphaReport``. Public surface: ``run_analyzers``.

The pipeline is intentionally split into three blocks so each step
stays under the 50-line rule and reads top-to-bottom:

    _compute_ic_metrics       — IC summary + decay + rolling series
    _compute_robustness_metrics — subperiod, lag, cost breakeven
    _collect_failure_reasons  — aggregates soft-failure strings

If a new analyzer lands, it slots into the appropriate block (or its
own block if it's a new concern) — never inline into ``run_analyzers``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.analyzers.cost import (
    compute_cost_breakeven,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.ic import (
    compute_ic_decay,
    compute_ic_rolling,
    compute_ic_series,
    summarize_ic,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.lag import (
    compute_lag_sensitivity,
    lag_sharpe_decay_ratio,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.stability import (
    compute_subperiod_stability,
)
from prophitai_algo_trading.analytics.alpha_research.facts import AnalyticsFacts
from prophitai_algo_trading.analytics.alpha_research.models import AlphaReport


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _years_in_index(index: pd.DatetimeIndex) -> float:
    """Years spanned by the index — used for annualizing turnover."""
    if len(index) < 2:
        return EPSILON

    span_seconds = (index[-1] - index[0]).total_seconds()

    return max(span_seconds / SECONDS_PER_YEAR, EPSILON)


def _cost_drag(facts: AnalyticsFacts) -> float | None:
    """Total-return delta between pre-cost and post-cost equity, in pct.

    Returns ``None`` when either return series is empty.
    """
    if facts.pre_cost_returns.empty or facts.bar_returns.empty:
        return None

    pre = float((1.0 + facts.pre_cost_returns).prod() - 1.0)
    post = float((1.0 + facts.bar_returns).prod() - 1.0)

    return round((pre - post) * 100.0, 2)


def _turnover_per_year(facts: AnalyticsFacts) -> float:
    """Annualized turnover from ``facts.turnover``."""
    years = _years_in_index(facts.turnover.index)  # type: ignore[arg-type]

    return round(float(facts.turnover.sum()) / years, 2)


#     ================================
# --> Analyzer blocks
#     ================================

def _compute_ic_metrics(facts: AnalyticsFacts) -> dict[str, Any]:
    """Compute IC summary, IC decay, and rolling IC.

    Returned dict keys exactly match the corresponding ``AlphaReport``
    field names so it can be splatted into the dataclass constructor.
    """
    config = facts.config

    primary_forward = facts.forward_returns_by_horizon[config.ic_primary_horizon]

    ic_series = compute_ic_series(facts.scores, primary_forward)
    ic_mean, ic_tstat, ic_hit_rate = summarize_ic(ic_series)

    ic_decay, ic_decay_tstats = compute_ic_decay(
        facts.scores, facts.forward_returns_by_horizon,
    )

    ic_rolling = compute_ic_rolling(ic_series, config.ic_rolling_window)

    return {
        "ic_mean": ic_mean,
        "ic_tstat": ic_tstat,
        "ic_per_date": ic_series,
        "ic_decay": ic_decay,
        "ic_decay_tstats": ic_decay_tstats,
        "ic_hit_rate": ic_hit_rate,
        "ic_rolling": ic_rolling,
    }


def _compute_robustness_metrics(facts: AnalyticsFacts) -> dict[str, Any]:
    """Compute subperiod stability, lag sensitivity, and cost breakeven.

    Returned dict keys exactly match the corresponding ``AlphaReport``
    field names so it can be splatted into the dataclass constructor.
    """
    config = facts.config

    primary_forward = facts.forward_returns_by_horizon[config.ic_primary_horizon]

    subperiod = compute_subperiod_stability(
        facts.bar_returns,
        facts.scores,
        primary_forward,
        config.subperiod_count,
        config.minimum_bars,
    )

    lag_sensitivity = compute_lag_sensitivity(
        facts.weights,
        facts.asset_returns,
        facts.turnover,
        facts.bar_returns,
        config.cost_per_turnover,
        config.lag_horizons,
    )

    cost = compute_cost_breakeven(
        facts.pre_cost_returns,
        facts.turnover,
        config.cost_curve_bps,
    )

    return {
        "subperiod_stability": subperiod,
        "lag_sensitivity": lag_sensitivity,
        "lag_sharpe_decay": lag_sharpe_decay_ratio(lag_sensitivity),
        "cost_breakeven_bps": cost["cost_breakeven_bps"],
        "cost_curve": cost["cost_curve"],
    }


def _collect_failure_reasons(
    facts: AnalyticsFacts,
    ic_metrics: dict[str, Any],
    robustness: dict[str, Any],
) -> list[str]:
    """Aggregate soft-failure messages across analyzers."""
    config = facts.config
    failures: list[str] = []

    if robustness["subperiod_stability"] is None:
        failures.append(
            "subperiod: panel too short to split into "
            f"{config.subperiod_count} slices of >= {config.minimum_bars} bars",
        )

    if robustness["lag_sharpe_decay"] is None:
        failures.append(
            "lag_sensitivity: lag-1 Sharpe non-positive — decay ratio undefined",
        )

    if robustness["cost_breakeven_bps"] is None:
        failures.append(
            "cost_breakeven: alpha unprofitable at zero cost — breakeven undefined",
        )

    for horizon, value in ic_metrics["ic_decay"].items():
        if value is None:
            failures.append(f"ic_decay h={horizon}: insufficient bars")

    if ic_metrics["ic_per_date"].dropna().empty:
        failures.append("ic: degenerate scores (all-NaN per-date IC)")

    return failures


#     ================================
# --> Public entry
#     ================================

def run_analyzers(facts: AnalyticsFacts) -> AlphaReport:
    """Compose every per-alpha analyzer into one ``AlphaReport``.

    Reads top-to-bottom: IC block → robustness block → failure
    aggregation → report assembly. Each block returns a dict whose keys
    line up with ``AlphaReport`` fields so assembly stays a single
    constructor call.
    """
    config = facts.config

    ic_metrics = _compute_ic_metrics(facts)
    robustness = _compute_robustness_metrics(facts)

    failure_reasons = _collect_failure_reasons(facts, ic_metrics, robustness)

    return AlphaReport(
        name=facts.name,
        panel_window=(facts.panel.index[0], facts.panel.index[-1]),
        bars=len(facts.panel.index),
        tickers=len(facts.panel.tickers),
        equity_curve=facts.backtest_result.equity_curve,
        bar_returns=facts.bar_returns,
        pre_cost_returns=facts.pre_cost_returns,
        metrics=facts.backtest_result.metrics,
        turnover_per_year=_turnover_per_year(facts),
        cost_drag_pct=_cost_drag(facts),
        failure_reasons=failure_reasons,
        scores=facts.scores if config.keep_diagnostics else None,
        weights=facts.weights if config.keep_diagnostics else None,
        asset_returns=facts.asset_returns if config.keep_diagnostics else None,
        **ic_metrics,
        **robustness,
    )
