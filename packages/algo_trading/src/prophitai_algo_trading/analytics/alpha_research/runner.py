"""Public entry points for the alpha-research subsystem.

Three entry points:

    analyze_alpha           — single-alpha pipeline. Returns a fully
                              populated ``AlphaReport`` (cross-alpha
                              projection fields stay ``None``).
    analyze_alphas          — multi-alpha sweep. Builds the cross-alpha
                              layer and back-fills cross projections
                              onto each per-alpha report.
    cadence_sweep_for_alpha — post-graduation deep-dive: Sharpe / return /
                              turnover at each cadence for one alpha.

Heavy lifting lives in:

    pipeline.run_analyzers   — per-alpha analyzer composition
    cross_alpha.*            — cross-alpha layer (FDR, clusters, graduation)
    summary.build_summary_frame — wide flat sweep table

This file is the orchestrator only — if logic is creeping in here that
isn't an entry point or call sequence, it belongs in one of the modules
above.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Callable

import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.analyzers.cadence import (
    STANDARD_CADENCES,
    best_cadence_label,
    compute_cadence_sweep,
)
from prophitai_algo_trading.analytics.alpha_research.cross_alpha import (
    apply_clustering,
    apply_fdr,
    apply_graduation,
    backfill_top_correlations,
    run_cross_alpha,
    validate_unique_names,
)
from prophitai_algo_trading.analytics.alpha_research.facts import (
    build_facts,
    build_forward_returns_cache,
)
from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    AnalyticsConfig,
    CrossAlphaReport,
)
from prophitai_algo_trading.analytics.alpha_research.pipeline import run_analyzers
from prophitai_algo_trading.analytics.alpha_research.summary import build_summary_frame

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPortfolioConstructor


#     ================================
# --> Public entry — single alpha
#     ================================

def analyze_alpha(
    alpha: "VectorAlpha",
    panel: "PricePanel",
    pcm_factory: Callable[[], "VectorPortfolioConstructor"],
    config: AnalyticsConfig = AnalyticsConfig(),
    benchmark: pd.Series | None = None,
) -> AlphaReport:
    """Run the full per-alpha research pipeline on a single alpha.

    Cross-alpha projection fields (``top_correlations``, ``cluster_id``,
    FDR fields) stay ``None`` — they only populate when the alpha is
    run via ``analyze_alphas``.
    """
    facts = build_facts(
        alpha=alpha,
        panel=panel,
        pcm_factory=pcm_factory,
        config=config,
        benchmark=benchmark,
    )

    return run_analyzers(facts)


#     ================================
# --> Public entry — multi-alpha sweep
#     ================================

def analyze_alphas(
    alphas: list["VectorAlpha"],
    panel: "PricePanel",
    pcm_factory: Callable[[], "VectorPortfolioConstructor"],
    config: AnalyticsConfig = AnalyticsConfig(),
    benchmark: pd.Series | None = None,
) -> tuple[list[AlphaReport], CrossAlphaReport]:
    """Sweep every alpha through the per-alpha pipeline + cross-cuts.

    Builds the panel-wide forward-returns cache once and shares it
    across every alpha, then runs the cross-alpha layer (FDR,
    clustering, graduation, top-correlations) and back-fills per-alpha
    projection fields. Summary frame is built last so its columns
    reflect every analyzer's output.
    """
    if not alphas:
        raise ValueError("analyze_alphas requires at least one alpha")

    validate_unique_names(alphas)

    forward_returns_cache = build_forward_returns_cache(panel, config.ic_horizons)

    reports: list[AlphaReport] = []

    for alpha in alphas:
        facts = build_facts(
            alpha=alpha,
            panel=panel,
            pcm_factory=pcm_factory,
            config=config,
            benchmark=benchmark,
            forward_returns_cache=forward_returns_cache,
        )

        reports.append(run_analyzers(facts))

    cross = run_cross_alpha(reports)

    apply_fdr(reports, cross, config)
    apply_clustering(reports, cross, config)
    backfill_top_correlations(reports, cross, config)
    apply_graduation(reports, config)

    cross.summary = build_summary_frame(reports)

    return reports, cross


#     ================================
# --> Public entry — cadence sweep (deep-dive on one alpha)
#     ================================

def cadence_sweep_for_alpha(
    alpha: "VectorAlpha",
    panel: "PricePanel",
    pcm_factory_at_cadence: Callable[[timedelta | None], "VectorPortfolioConstructor"],
    cadences: dict[str, timedelta | None] = STANDARD_CADENCES,
    config: AnalyticsConfig = AnalyticsConfig(),
    benchmark: pd.Series | None = None,
    report: AlphaReport | None = None,
) -> dict[str, dict[str, float]]:
    """Run ``VectorBacktest`` at every cadence; return Sharpe / return / turnover.

    Intended for post-graduation deep dive on a candidate alpha — N
    cadences = N additional backtests, so don't fire it for the bulk
    sweep. Use ``analyze_alphas`` to identify candidates, then call this
    on each survivor.

    When ``report`` is supplied, the result is also attached to
    ``report.cadence_sweep`` and ``report.best_cadence``.
    """
    sweep = compute_cadence_sweep(
        alpha=alpha,
        panel=panel,
        pcm_factory_at_cadence=pcm_factory_at_cadence,
        cadences=cadences,
        initial_capital=config.initial_capital,
        cost_per_turnover=config.cost_per_turnover,
        benchmark=benchmark,
    )

    best = best_cadence_label(sweep)

    if report is not None:
        report.cadence_sweep = sweep
        report.best_cadence = best

    return sweep
