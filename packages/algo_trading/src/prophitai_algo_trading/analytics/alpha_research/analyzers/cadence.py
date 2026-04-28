"""Rebalance-cadence sweep analyzer.

Re-runs ``VectorBacktest`` for one alpha at every cadence in a list and
reports headline metrics per cadence. Tells you empirically what
rebalance frequency the alpha prefers — the Sharpe-vs-cadence curve.

Unlike the other analyzers (which perturb intermediate panels and run
in milliseconds), this one runs N additional backtests per call. It's
intended for *post-graduation deep dive* on candidate alphas, not bulk
sweeps. The runner keeps it OUT of the per-alpha pipeline; users invoke
it explicitly via ``cadence_sweep_for_alpha`` when they want it.

The user supplies a ``pcm_factory_at_cadence: (cadence) -> VectorPortfolioConstructor``
because we can't override the cadence on a generic PCM instance — the
PCM's internal cadence handling differs across implementations, and
mutating private attributes is fragile. The factory pattern keeps the
override explicit and PCM-agnostic.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Callable

import pandas as pd

from prophitai_algo_trading.algorithm.vector import VectorAlgorithm
from prophitai_algo_trading.engines.vector_backtest import VectorBacktest

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPortfolioConstructor


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


#     ================================
# --> Standard cadence presets
#     ================================

STANDARD_CADENCES: dict[str, timedelta | None] = {
    "daily": None,
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=90),
}


#     ================================
# --> Helper funcs
#     ================================

def _annualized_turnover(turnover: pd.Series) -> float:
    """Annualized turnover from a per-bar turnover series."""
    if turnover.empty or len(turnover) < 2:
        return 0.0

    span_seconds = (turnover.index[-1] - turnover.index[0]).total_seconds()
    years = max(span_seconds / SECONDS_PER_YEAR, EPSILON)

    return float(turnover.sum()) / years


#     ================================
# --> Public analyzer
#     ================================

def compute_cadence_sweep(
    alpha: "VectorAlpha",
    panel: "PricePanel",
    pcm_factory_at_cadence: Callable[[timedelta | None], "VectorPortfolioConstructor"],
    cadences: dict[str, timedelta | None],
    initial_capital: float,
    cost_per_turnover: float,
    benchmark: pd.Series | None = None,
) -> dict[str, dict[str, float]]:
    """Run ``VectorBacktest`` at every cadence and report headline metrics.

    Args:
        alpha: Vectorized alpha implementing ``compute_panel``.
        panel: Source price panel.
        pcm_factory_at_cadence: ``(cadence) -> VectorPortfolioConstructor``. Called once
            per cadence to produce a fresh PCM with that cadence baked
            in. ``cadence=None`` means rebalance every bar.
        cadences: Ordered ``{label: timedelta | None}`` to test.
        initial_capital: Notional starting equity (matches per-alpha runs).
        cost_per_turnover: Linear turnover penalty per unit of weight delta.
        benchmark: Optional benchmark price series.

    Returns:
        ``{cadence_label: {sharpe, total_return_pct, turnover_per_year}}``.
    """
    engine = VectorBacktest(verbose=False)

    out: dict[str, dict[str, float]] = {}

    for label, cadence in cadences.items():
        pcm = pcm_factory_at_cadence(cadence)

        algo = VectorAlgorithm(
            alphas=[alpha],
            pcm=pcm,
            initial_capital=initial_capital,
            cost_per_turnover=cost_per_turnover,
        )

        result, diagnostics = engine.run_with_diagnostics(
            algo, panel, benchmark=benchmark,
        )

        sharpe = result.metrics.get("sharpe_ratio", 0.0) or 0.0
        total_return = result.metrics.get("total_return_pct", 0.0) or 0.0

        turnover_yr = _annualized_turnover(diagnostics.turnover)

        out[label] = {
            "sharpe": round(float(sharpe), 3),
            "total_return_pct": round(float(total_return), 2),
            "turnover_per_year": round(turnover_yr, 2),
        }

    return out


def best_cadence_label(
    cadence_sweep: dict[str, dict[str, float]],
) -> str | None:
    """Return the cadence label with the highest Sharpe.

    Returns ``None`` when the sweep is empty or every Sharpe is
    non-positive (the alpha doesn't work at any cadence).
    """
    if not cadence_sweep:
        return None

    best_label: str | None = None
    best_sharpe = float("-inf")

    for label, metrics in cadence_sweep.items():
        sharpe = metrics["sharpe"]

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_label = label

    if best_sharpe <= 0.0:
        return None

    return best_label
