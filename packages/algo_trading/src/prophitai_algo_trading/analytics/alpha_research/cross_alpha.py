"""Cross-alpha layer — runs after every per-alpha report is built.

Public surface:

    validate_unique_names      — raise on duplicate alpha names
    run_cross_alpha            — bare ``CrossAlphaReport`` (correlations only)
    apply_fdr                  — FDR correction → cross.fdr_table + per-alpha
    apply_clustering           — clusters → cross.clusters + per-alpha
    apply_graduation           — graduation flag + appended failure reasons
    backfill_top_correlations  — peer correlations onto each ``AlphaReport``

These are deliberately tiny coordinator funcs that delegate to the
analyzer modules under ``analyzers/``. The orchestrator in
``runner.analyze_alphas`` calls them in order; the call list reads
top-to-bottom and the side-effects on ``AlphaReport`` / ``CrossAlphaReport``
are local to each func.
"""

from __future__ import annotations

from prophitai_algo_trading.analytics.alpha_research.analyzers.clustering import (
    cluster_by_correlation,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.correlations import (
    build_return_correlations,
    top_correlations_for,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.fdr import (
    apply_fdr_correction,
)
from prophitai_algo_trading.analytics.alpha_research.analyzers.graduation import (
    evaluate_graduation,
)
from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    AnalyticsConfig,
    CrossAlphaReport,
)


#     ================================
# --> Validation
#     ================================

def validate_unique_names(alphas: list) -> None:
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
# --> Cross-alpha builders
#     ================================

def run_cross_alpha(reports: list[AlphaReport]) -> CrossAlphaReport:
    """Build the bare cross-alpha report (correlations only).

    The summary frame is built last in ``analyze_alphas`` — after FDR,
    clustering, and graduation populate per-alpha fields — so its
    columns reflect every analyzer's output.
    """
    bar_returns_map = {r.name: r.bar_returns for r in reports}

    correlations = build_return_correlations(bar_returns_map)

    return CrossAlphaReport(return_correlations=correlations)


def apply_fdr(
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


def apply_clustering(
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


def apply_graduation(
    reports: list[AlphaReport], config: AnalyticsConfig,
) -> None:
    """Apply graduation thresholds; set ``passes`` and append failure reasons."""
    for report in reports:
        passes, failed = evaluate_graduation(report, config)

        report.passes = passes
        report.failure_reasons.extend(failed)


def backfill_top_correlations(
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
