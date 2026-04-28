"""Pretty-printers for alpha-research reports.

The summary table on ``CrossAlphaReport`` is wide — every alpha gets one
row across many columns. ``print_alpha_research`` renders it in fixed-
width form with sensible column widths, drops fully-empty columns, and
appends the return-correlation matrix below for cross-alpha context.

Standalone single-alpha use is supported via ``print_alpha_report`` —
shows one alpha's headline scalars, IC decay table, and sub-period
slices stacked vertically.
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    CrossAlphaReport,
)


DEFAULT_COL_WIDTH = 12
ALPHA_LABEL_WIDTH = 22


#     ================================
# --> Helper funcs
#     ================================

def _format_cell(value: object, width: int) -> str:
    """Right-aligned printable cell for a metric value."""
    if value is None:
        text = "n/a"
    elif isinstance(value, float):
        text = f"{value:.2f}" if not pd.isna(value) else "nan"
    elif isinstance(value, int):
        text = f"{value}"
    else:
        text = str(value)

    return f"{text:>{width}s}"


def _drop_empty_columns(summary: pd.DataFrame) -> pd.DataFrame:
    """Drop columns where every value is None / NaN.

    Keeps the printout focused on populated metrics — relevant when
    later PRs land columns that aren't always populated.
    """
    return summary.dropna(axis=1, how="all")


#     ================================
# --> Multi-alpha summary printer
#     ================================

def print_alpha_research(
    reports: list[AlphaReport], cross: CrossAlphaReport,
) -> None:
    """Print the wide summary table + return-correlation matrix."""
    summary = _drop_empty_columns(cross.summary)

    if summary.empty:
        print("(no alphas were run)")
        return

    columns = list(summary.columns)

    header = f"{'alpha':<{ALPHA_LABEL_WIDTH}s}" + "".join(
        _format_cell(c[:DEFAULT_COL_WIDTH], DEFAULT_COL_WIDTH) for c in columns
    )

    print("\n" + header)
    print("-" * len(header))

    for alpha_name, row in summary.iterrows():
        line = f"{str(alpha_name):<{ALPHA_LABEL_WIDTH}s}" + "".join(
            _format_cell(row[c], DEFAULT_COL_WIDTH) for c in columns
        )

        print(line)

    if not cross.return_correlations.empty:
        print("\nReturn correlations:")
        print(cross.return_correlations.round(3).to_string())

    if cross.clusters:
        print("\nClusters (alphas with |corr| above threshold are grouped):")

        for cluster_id in sorted(cross.clusters.keys()):
            members = cross.clusters[cluster_id]
            print(f"  cluster {cluster_id}: {', '.join(members)}")

    if not cross.fdr_table.empty:
        survivors = cross.fdr_table[cross.fdr_table["passes_fdr"]]

        print(f"\nFDR survivors ({len(survivors)} of {len(cross.fdr_table)}):")

        if survivors.empty:
            print("  (none — no alphas survived multiple-testing correction)")
        else:
            for name in survivors.index:
                print(f"  {name}")

    graduated = [r for r in reports if r.passes is True]

    if graduated:
        print(f"\nGraduated ({len(graduated)} of {len(reports)}):")

        for report in graduated:
            cluster_str = (
                f" (cluster {report.cluster_id})"
                if report.cluster_id is not None
                else ""
            )
            print(f"  {report.name}{cluster_str}")

    failures = [r for r in reports if r.has_failures]

    if failures:
        print("\nFailures:")

        for report in failures:
            print(f"  {report.name}:")

            for reason in report.failure_reasons:
                print(f"    - {reason}")

    print()


#     ================================
# --> Single-alpha printer
#     ================================

def print_alpha_report(report: AlphaReport) -> None:
    """Vertical layout for a single alpha — headline + decay + slices."""
    print(f"\n=== {report.name} ===")
    print(f"window: {report.panel_window[0].date()} -> {report.panel_window[1].date()}")
    print(f"bars:   {report.bars}    tickers: {report.tickers}")

    print("\nSignal quality:")
    print(f"  ic_mean      {report.ic_mean:.4f}")
    print(f"  ic_tstat     {report.ic_tstat:.2f}")
    print(f"  ic_hit_rate  {report.ic_hit_rate:.3f}")

    print("\nIC decay:")
    print(f"  {'horizon':>8s} {'ic':>10s} {'tstat':>8s}")

    for horizon in sorted(report.ic_decay.keys()):
        ic_value = report.ic_decay[horizon]
        tstat_value = report.ic_decay_tstats[horizon]

        ic_text = f"{ic_value:.4f}" if ic_value is not None else "n/a"
        tstat_text = f"{tstat_value:.2f}" if tstat_value is not None else "n/a"

        print(f"  {horizon:>8d} {ic_text:>10s} {tstat_text:>8s}")

    if report.subperiod_stability is not None:
        print("\nSub-period stability:")

        for i, slice_metrics in enumerate(report.subperiod_stability["slices"]):
            print(
                f"  slice {i + 1}: "
                f"sharpe={slice_metrics['sharpe']:.2f}  "
                f"ic={slice_metrics['ic_mean']:.4f}  "
                f"return={slice_metrics['total_return']:.2f}%  "
                f"bars={slice_metrics['bars']}",
            )

        ratio = report.subperiod_stability["sharpe_min_max_ratio"]
        ic_ratio = report.subperiod_stability["ic_min_max_ratio"]

        print(f"  sharpe_min_max_ratio: {ratio}")
        print(f"  ic_min_max_ratio:     {ic_ratio}")

    if report.lag_sensitivity is not None:
        print("\nLag sensitivity:")
        print(f"  {'lag':>6s} {'sharpe':>10s} {'total_ret':>12s}")

        for lag in sorted(report.lag_sensitivity.keys()):
            metrics = report.lag_sensitivity[lag]
            print(
                f"  {lag:>6d} {metrics['sharpe']:>10.2f} "
                f"{metrics['total_return_pct']:>11.2f}%",
            )

        if report.lag_sharpe_decay is not None:
            print(f"  sharpe_decay_ratio: {report.lag_sharpe_decay}")

    if report.cost_curve is not None:
        print("\nCost breakeven:")
        print(f"  {'cost_bps':>10s} {'total_ret':>12s}")

        for cost_bps in sorted(report.cost_curve.keys()):
            total = report.cost_curve[cost_bps]
            print(f"  {cost_bps:>10.1f} {total:>11.2f}%")

        breakeven = report.cost_breakeven_bps

        if breakeven is None:
            print("  breakeven_bps: undefined (unprofitable at zero cost)")
        elif breakeven == float("inf"):
            print(f"  breakeven_bps: > {max(report.cost_curve.keys())}")
        else:
            print(f"  breakeven_bps: {breakeven}")

    if report.cadence_sweep is not None:
        print("\nCadence sweep:")
        print(
            f"  {'cadence':>12s} {'sharpe':>10s} "
            f"{'total_ret':>12s} {'turnover/yr':>14s}",
        )

        for label, metrics in report.cadence_sweep.items():
            print(
                f"  {label:>12s} {metrics['sharpe']:>10.2f} "
                f"{metrics['total_return_pct']:>11.2f}% "
                f"{metrics['turnover_per_year']:>14.2f}",
            )

        if report.best_cadence is not None:
            print(f"  best_cadence: {report.best_cadence}")
        else:
            print("  best_cadence: none (alpha unprofitable at every cadence)")

    if report.metrics:
        print("\nBacktest metrics:")

        for key, value in report.metrics.items():
            print(f"  {key:<24s} {value}")

    if report.has_failures:
        print("\nFailures:")

        for reason in report.failure_reasons:
            print(f"  - {reason}")

    print()
