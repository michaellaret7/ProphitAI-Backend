"""Public entry points for the alpha-research subsystem.

Two functions:

    analyze_alpha:  single-alpha entry. Runs the per-alpha analyzer
                    pipeline and returns a fully populated
                    ``AlphaReport`` (cross-alpha projection fields stay
                    ``None`` — those only make sense in a sweep).
    analyze_alphas: multi-alpha entry. Runs ``analyze_alpha`` once per
                    alpha (with a sweep-shared forward-returns cache),
                    builds the cross-alpha layer, and back-fills the
                    cross projections onto each per-alpha report.

Each per-alpha analyzer call is one line — the orchestrator stays
small and reads top-to-bottom. If this file grows past ~150 LOC, that's
a smell: a new analyzer should land in its own module under
``analyzers/`` and slot in here as a single new line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.analyzers.clustering import (
    cluster_by_correlation,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.correlations import (
    build_return_correlations,
    top_correlations_for,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.cost import (
    compute_cost_breakeven,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.fdr import (
    apply_fdr_correction,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.graduation import (
    evaluate_graduation,
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
from prophitai_algo_trading.analytics.alpha_research.facts import (
    AnalyticsFacts,
    build_facts,
    build_forward_returns_cache,
)
from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    AnalyticsConfig,
    CrossAlphaReport,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPCM


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


def _validate_unique_names(alphas: list["VectorAlpha"]) -> None:
    """Raise on duplicate alpha names — projections key on name."""
    seen: set[str] = set()
    duplicates: list[str] = []

    for alpha in alphas:
        if alpha.name in seen:
            duplicates.append(alpha.name)
            continue

        seen.add(alpha.name)

    if duplicates:
        raise ValueError(
            f"Duplicate alpha names: {sorted(set(duplicates))}. "
            f"Each alpha must have a unique name.",
        )


#     ================================
# --> Per-alpha analyzer pipeline
#     ================================

def _run_analyzers(facts: AnalyticsFacts) -> AlphaReport:
    """Compose every per-alpha analyzer into one ``AlphaReport``.

    Reads top-to-bottom: identity → IC → IC decay → rolling IC →
    backtest passthrough → sub-period stability → optional diagnostics.
    Every analyzer call is one line; failures append to
    ``failure_reasons`` but never raise.
    """
    config = facts.config

    primary_horizon = config.ic_primary_horizon
    primary_forward = facts.forward_returns_by_horizon[primary_horizon]

    ic_series = compute_ic_series(facts.scores, primary_forward)
    ic_mean, ic_tstat, ic_hit_rate = summarize_ic(ic_series)

    ic_decay, ic_decay_tstats = compute_ic_decay(
        facts.scores, facts.forward_returns_by_horizon,
    )

    ic_rolling = compute_ic_rolling(ic_series, config.ic_rolling_window)

    turnover_per_year = _turnover_per_year(facts)
    cost_drag_pct = _cost_drag(facts)

    failure_reasons: list[str] = []

    subperiod = compute_subperiod_stability(
        facts.bar_returns,
        facts.scores,
        primary_forward,
        config.subperiod_count,
        config.minimum_bars,
    )

    if subperiod is None:
        failure_reasons.append(
            "subperiod: panel too short to split into "
            f"{config.subperiod_count} slices of >= {config.minimum_bars} bars",
        )

    lag_sensitivity = compute_lag_sensitivity(
        facts.weights,
        facts.asset_returns,
        facts.turnover,
        facts.bar_returns,
        config.cost_per_turnover,
        config.lag_horizons,
    )

    lag_decay = lag_sharpe_decay_ratio(lag_sensitivity)

    if lag_decay is None:
        failure_reasons.append(
            "lag_sensitivity: lag-1 Sharpe non-positive — decay ratio undefined",
        )

    cost = compute_cost_breakeven(
        facts.pre_cost_returns,
        facts.turnover,
        config.cost_curve_bps,
    )

    if cost["cost_breakeven_bps"] is None:
        failure_reasons.append(
            "cost_breakeven: alpha unprofitable at zero cost — breakeven undefined",
        )

    for horizon, value in ic_decay.items():
        if value is None:
            failure_reasons.append(
                f"ic_decay h={horizon}: insufficient bars",
            )

    if ic_series.dropna().empty:
        failure_reasons.append("ic: degenerate scores (all-NaN per-date IC)")

    return AlphaReport(
        name=facts.name,
        panel_window=(facts.panel.index[0], facts.panel.index[-1]),
        bars=len(facts.panel.index),
        tickers=len(facts.panel.tickers),
        ic_mean=ic_mean,
        ic_tstat=ic_tstat,
        ic_per_date=ic_series,
        ic_decay=ic_decay,
        ic_decay_tstats=ic_decay_tstats,
        ic_hit_rate=ic_hit_rate,
        ic_rolling=ic_rolling,
        equity_curve=facts.backtest_result.equity_curve,
        bar_returns=facts.bar_returns,
        pre_cost_returns=facts.pre_cost_returns,
        metrics=facts.backtest_result.metrics,
        turnover_per_year=turnover_per_year,
        cost_drag_pct=cost_drag_pct,
        subperiod_stability=subperiod,
        lag_sensitivity=lag_sensitivity,
        lag_sharpe_decay=lag_decay,
        cost_breakeven_bps=cost["cost_breakeven_bps"],  # type: ignore[arg-type]
        cost_curve=cost["cost_curve"],  # type: ignore[arg-type]
        failure_reasons=failure_reasons,
        scores=facts.scores if config.keep_diagnostics else None,
        weights=facts.weights if config.keep_diagnostics else None,
        asset_returns=facts.asset_returns if config.keep_diagnostics else None,
    )


def _turnover_per_year(facts: AnalyticsFacts) -> float:
    """Annualized turnover from ``facts.turnover``."""
    years = _years_in_index(facts.turnover.index)  # type: ignore[arg-type]

    return round(float(facts.turnover.sum()) / years, 2)


#     ================================
# --> Public entry — single alpha
#     ================================

def analyze_alpha(
    alpha: "VectorAlpha",
    panel: "PricePanel",
    pcm_factory: Callable[[], "VectorPCM"],
    config: AnalyticsConfig = AnalyticsConfig(),
    benchmark: pd.Series | None = None,
) -> AlphaReport:
    """Run the full per-alpha research pipeline on a single alpha.

    Cross-alpha projection fields (``top_correlations``, ``cluster_id``,
    FDR fields) stay ``None`` — they only become populated when the
    alpha is run via ``analyze_alphas``.

    Args:
        alpha: Vectorized alpha implementing ``compute_panel``.
        panel: Source price panel.
        pcm_factory: Zero-arg callable returning a fresh ``VectorPCM``.
        config: Active ``AnalyticsConfig``. Defaults are sensible.
        benchmark: Optional benchmark price series for beta + alpha.

    Returns:
        Populated ``AlphaReport``.
    """
    facts = build_facts(
        alpha=alpha,
        panel=panel,
        pcm_factory=pcm_factory,
        config=config,
        benchmark=benchmark,
    )

    return _run_analyzers(facts)


#     ================================
# --> Public entry — multi-alpha sweep
#     ================================

def analyze_alphas(
    alphas: list["VectorAlpha"],
    panel: "PricePanel",
    pcm_factory: Callable[[], "VectorPCM"],
    config: AnalyticsConfig = AnalyticsConfig(),
    benchmark: pd.Series | None = None,
) -> tuple[list[AlphaReport], CrossAlphaReport]:
    """Sweep every alpha through the per-alpha pipeline + cross-cuts.

    Builds the panel-wide forward-returns cache once and shares it
    across every alpha — saves redundant ``pct_change`` ops on N-alpha
    sweeps.

    After the per-alpha layer, builds the return-correlation matrix and
    back-fills each ``AlphaReport.top_correlations``. Cluster / FDR
    projection fields stay ``None`` until PR 3 lands those analyzers.

    Args:
        alphas: One or more vectorized alphas with unique names.
        panel: Source price panel.
        pcm_factory: Zero-arg callable returning a fresh ``VectorPCM``
            per call. State never leaks between alphas.
        config: Active ``AnalyticsConfig``.
        benchmark: Optional benchmark price series.

    Returns:
        ``(per_alpha_reports, cross_alpha_report)``.
    """
    if not alphas:
        raise ValueError("analyze_alphas requires at least one alpha")

    _validate_unique_names(alphas)

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

        reports.append(_run_analyzers(facts))

    cross = _run_cross_alpha(reports)

    _apply_fdr(reports, cross, config)
    _apply_clustering(reports, cross, config)
    _backfill_top_correlations(reports, cross, config)
    _apply_graduation(reports, config)

    cross.summary = _build_summary_frame(reports)

    return reports, cross


#     ================================
# --> Cross-alpha layer
#     ================================

def _run_cross_alpha(reports: list[AlphaReport]) -> CrossAlphaReport:
    """Build the bare cross-alpha report (correlations only).

    The summary frame is built last in ``analyze_alphas`` — after FDR,
    clustering, and graduation populate per-alpha fields — so its
    columns reflect every analyzer's output.
    """
    bar_returns_map = {r.name: r.bar_returns for r in reports}

    correlations = build_return_correlations(bar_returns_map)

    return CrossAlphaReport(return_correlations=correlations)


def _apply_fdr(
    reports: list[AlphaReport],
    cross: CrossAlphaReport,
    config: AnalyticsConfig,
) -> None:
    """Run FDR correction; populate ``cross.fdr_table`` and per-alpha fields."""
    ic_tstats = {r.name: r.ic_tstat for r in reports}

    fdr_table = apply_fdr_correction(ic_tstats, config.fdr_alpha)

    cross.fdr_table = fdr_table

    if fdr_table.empty:
        return

    for report in reports:
        if report.name not in fdr_table.index:
            continue

        row = fdr_table.loc[report.name]

        report.fdr_adjusted_pvalue = float(row["fdr_adjusted_pvalue"])
        report.passes_fdr = bool(row["passes_fdr"])


def _apply_clustering(
    reports: list[AlphaReport],
    cross: CrossAlphaReport,
    config: AnalyticsConfig,
) -> None:
    """Cluster by correlation; populate ``cross.clusters`` + per-alpha fields."""
    if cross.return_correlations.empty:
        return

    clusters, linkage_matrix = cluster_by_correlation(
        cross.return_correlations, config.cluster_distance_threshold,
    )

    cross.clusters = clusters
    cross.linkage = linkage_matrix

    name_to_cluster = {
        name: cid for cid, names in clusters.items() for name in names
    }

    for report in reports:
        cid = name_to_cluster.get(report.name)

        if cid is None:
            continue

        report.cluster_id = cid
        report.cluster_peers = [n for n in clusters[cid] if n != report.name]


def _apply_graduation(
    reports: list[AlphaReport], config: AnalyticsConfig,
) -> None:
    """Apply graduation thresholds; set ``passes`` and append failure reasons."""
    for report in reports:
        passes, failed = evaluate_graduation(report, config)

        report.passes = passes
        report.failure_reasons.extend(failed)


def _backfill_top_correlations(
    reports: list[AlphaReport],
    cross: CrossAlphaReport,
    config: AnalyticsConfig,
) -> None:
    """Populate each report's ``top_correlations`` from the corr matrix."""
    if cross.return_correlations.empty:
        return

    for report in reports:
        report.top_correlations = top_correlations_for(
            report.name, cross.return_correlations, config.top_correlations_k,
        )


#     ================================
# --> Summary frame
#     ================================

SUMMARY_COLUMNS_BACKTEST: tuple[str, ...] = (
    "total_return_pct",
    "annualized_return_pct",
    "sharpe_ratio",
    "max_drawdown_pct",
    "alpha_vs_benchmark_pct",
    "beta_vs_benchmark",
)


def _build_summary_frame(reports: list[AlphaReport]) -> pd.DataFrame:
    """Wide flat one-row-per-alpha view for keep/drop sweep tables."""
    rows: list[dict[str, float | int | str | None]] = []

    for report in reports:
        row: dict[str, float | int | str | None] = {
            "alpha": report.name,
            "ic_mean": round(report.ic_mean, 4),
            "ic_tstat": round(report.ic_tstat, 2),
            "ic_hit_rate": round(report.ic_hit_rate, 3),
        }

        for horizon, value in report.ic_decay.items():
            row[f"ic_h{horizon}"] = (
                round(value, 4) if value is not None else None
            )

        row.update({
            "turnover_per_year": report.turnover_per_year,
            "cost_drag_pct": report.cost_drag_pct,
        })

        for col in SUMMARY_COLUMNS_BACKTEST:
            row[col] = report.metrics.get(col)

        if report.subperiod_stability is not None:
            row["subperiod_sharpe_ratio"] = (
                report.subperiod_stability["sharpe_min_max_ratio"]
            )
            row["subperiod_ic_ratio"] = (
                report.subperiod_stability["ic_min_max_ratio"]
            )
        else:
            row["subperiod_sharpe_ratio"] = None
            row["subperiod_ic_ratio"] = None

        if report.lag_sensitivity is not None:
            for lag, metrics in sorted(report.lag_sensitivity.items()):
                row[f"sharpe_lag{lag}"] = metrics["sharpe"]

        row["lag_sharpe_decay"] = report.lag_sharpe_decay
        row["cost_breakeven_bps"] = (
            report.cost_breakeven_bps
            if report.cost_breakeven_bps != float("inf")
            else None
        )

        row["fdr_adj_p"] = report.fdr_adjusted_pvalue
        row["passes_fdr"] = report.passes_fdr
        row["cluster_id"] = report.cluster_id
        row["passes"] = report.passes
        row["failures"] = len(report.failure_reasons)

        rows.append(row)

    return pd.DataFrame(rows).set_index("alpha")
