"""``AnalyticsFacts`` — the per-alpha input bundle every analyzer reads.

Built once per alpha by ``_build_facts``: runs the alpha through
``VectorBacktest.run_with_diagnostics`` to produce the score panel,
weights, asset-returns, and bar-returns; then attaches the forward-
return panels at every ``ic_horizon`` (taken from a sweep-level cache
when one is supplied — saves redundant ``pct_change`` ops on N-alpha
sweeps).

Frozen so analyzers can't mutate shared inputs. Heavy panels (panel,
scores, weights, asset_returns) are kept as references — analyzers
treat them as read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

import pandas as pd

from prophitai_algo_trading.algorithm.vector import VectorAlgorithm
from prophitai_algo_trading.analytics.metrics import BacktestResult
from prophitai_algo_trading.engines.vector_backtest import VectorBacktest

if TYPE_CHECKING:
    from prophitai_algo_trading.analytics.alpha_research.models import (
        AnalyticsConfig,
    )
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPCM


#     ================================
# --> Helper funcs
#     ================================

def _forward_returns_for_horizon(
    panel: "PricePanel", horizon: int,
) -> pd.DataFrame:
    """``panel.close.pct_change(h).shift(-h)`` — forward returns at h bars."""
    return panel.close.pct_change(horizon).shift(-horizon)


def build_forward_returns_cache(
    panel: "PricePanel", horizons: tuple[int, ...],
) -> dict[int, pd.DataFrame]:
    """Compute every horizon's forward-return panel once.

    Reused across every alpha in a multi-alpha sweep — forward returns
    are alpha-independent. For 30 alphas with 5 horizons this saves 150
    redundant ``pct_change`` ops on a [N_bars x N_tickers] panel.

    Args:
        panel: Source price panel (uses ``close``).
        horizons: IC horizons to materialize.

    Returns:
        ``{horizon: forward_return_panel}``.
    """
    return {h: _forward_returns_for_horizon(panel, h) for h in horizons}


#     ================================
# --> Facts pack
#     ================================

@dataclass(frozen=True)
class AnalyticsFacts:
    """Per-alpha input bundle every analyzer consumes.

    Attributes:
        name: Alpha name.
        panel: Source price panel — kept as a reference, treated as
            read-only by every analyzer.
        benchmark: Optional benchmark price series.
        scores: ``[date x ticker]`` raw alpha score from the alpha's
            ``compute_panel``.
        weights: ``[date x ticker]`` PCM weights, cadence-aligned.
        asset_returns: ``panel.close.pct_change()``.
        pre_cost_returns: Per-bar portfolio return without turnover cost.
        bar_returns: Per-bar portfolio return after turnover cost.
        turnover: Per-bar absolute weight delta summed across tickers.
        backtest_result: Headline equity-curve + metrics dict from the
            vectorized backtest.
        forward_returns_by_horizon: Forward return panels keyed by IC
            horizon (in bars). Shared across the whole sweep.
        config: The active ``AnalyticsConfig``.
    """

    name: str
    panel: "PricePanel"
    benchmark: pd.Series | None

    scores: pd.DataFrame
    weights: pd.DataFrame
    asset_returns: pd.DataFrame
    pre_cost_returns: pd.Series
    bar_returns: pd.Series
    turnover: pd.Series

    backtest_result: BacktestResult

    forward_returns_by_horizon: dict[int, pd.DataFrame]

    config: "AnalyticsConfig"


#     ================================
# --> Builder
#     ================================

def build_facts(
    alpha: "VectorAlpha",
    panel: "PricePanel",
    pcm_factory: Callable[[], "VectorPCM"],
    config: "AnalyticsConfig",
    benchmark: pd.Series | None = None,
    forward_returns_cache: dict[int, pd.DataFrame] | None = None,
) -> AnalyticsFacts:
    """Run the alpha through ``VectorBacktest`` and pack the facts bundle.

    The PCM factory is called once per alpha so internal state never
    leaks between isolated runs — important for PCMs that aren't fully
    stateless (e.g., scheduler-based rebalance cadences).

    Args:
        alpha: Vectorized alpha implementing ``compute_panel``.
        panel: Source price panel.
        pcm_factory: Zero-arg callable returning a fresh ``VectorPCM``.
        config: Active ``AnalyticsConfig``.
        benchmark: Optional benchmark price series.
        forward_returns_cache: Sweep-shared cache of forward returns
            per horizon. When ``None``, the cache is built locally
            for this single alpha.

    Returns:
        Populated ``AnalyticsFacts``.

    Raises:
        ValueError: If ``len(panel.index) < config.minimum_bars``.
    """
    if len(panel.index) < config.minimum_bars:
        raise ValueError(
            f"panel has {len(panel.index)} bars — alpha-research requires "
            f">= {config.minimum_bars}",
        )

    algo = VectorAlgorithm(
        alphas=[alpha],
        pcm=pcm_factory(),
        initial_capital=config.initial_capital,
        cost_per_turnover=config.cost_per_turnover,
    )

    engine = VectorBacktest(verbose=config.verbose)

    result, diagnostics = engine.run_with_diagnostics(algo, panel, benchmark=benchmark)

    forward_returns = forward_returns_cache or build_forward_returns_cache(
        panel, config.ic_horizons,
    )

    return AnalyticsFacts(
        name=alpha.name,
        panel=panel,
        benchmark=benchmark,
        scores=diagnostics.scores[alpha.name],
        weights=diagnostics.weights,
        asset_returns=diagnostics.asset_returns,
        pre_cost_returns=diagnostics.pre_cost_returns,
        bar_returns=diagnostics.bar_returns,
        turnover=diagnostics.turnover,
        backtest_result=result,
        forward_returns_by_horizon=forward_returns,
        config=config,
    )
