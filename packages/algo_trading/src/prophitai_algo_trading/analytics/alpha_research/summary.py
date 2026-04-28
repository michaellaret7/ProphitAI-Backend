"""Wide flat summary frame builder for the multi-alpha sweep.

One row per alpha; columns are the decision-relevant scalars from every
analyzer. The ``CrossAlphaReport.summary`` field is built from this and
is what keep / drop sweep tables render off.
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.analytics.alpha_research.models import AlphaReport


SUMMARY_COLUMNS_BACKTEST: tuple[str, ...] = (
    "total_return_pct",
    "annualized_return_pct",
    "sharpe_ratio",
    "max_drawdown_pct",
    "alpha_vs_benchmark_pct",
    "beta_vs_benchmark",
)


#     ================================
# --> Helper funcs
#     ================================

def _ic_row(report: AlphaReport) -> dict[str, float | int | str | None]:
    """Identity + headline IC scalars."""
    row: dict[str, float | int | str | None] = {
        "alpha": report.name,
        "ic_mean": round(report.ic_mean, 4),
        "ic_tstat": round(report.ic_tstat, 2),
        "ic_hit_rate": round(report.ic_hit_rate, 3),
    }

    for horizon, value in report.ic_decay.items():
        row[f"ic_h{horizon}"] = round(value, 4) if value is not None else None

    return row


def _backtest_row(report: AlphaReport) -> dict[str, float | int | str | None]:
    """Turnover, cost drag, and the fixed backtest scalars."""
    row: dict[str, float | int | str | None] = {
        "turnover_per_year": report.turnover_per_year,
        "cost_drag_pct": report.cost_drag_pct,
    }

    for col in SUMMARY_COLUMNS_BACKTEST:
        row[col] = report.metrics.get(col)

    return row


def _robustness_row(report: AlphaReport) -> dict[str, float | int | str | None]:
    """Subperiod, lag, and cost-breakeven scalars."""
    row: dict[str, float | int | str | None] = {}

    if report.subperiod_stability is not None:
        row["subperiod_sharpe_ratio"] = (
            report.subperiod_stability["sharpe_min_max_ratio"]
        )
        row["subperiod_ic_ratio"] = report.subperiod_stability["ic_min_max_ratio"]
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

    return row


def _verdict_row(report: AlphaReport) -> dict[str, float | int | str | None]:
    """FDR / cluster / graduation scalars."""
    return {
        "fdr_adj_p": report.fdr_adjusted_pvalue,
        "passes_fdr": report.passes_fdr,
        "cluster_id": report.cluster_id,
        "passes": report.passes,
        "failures": len(report.failure_reasons),
    }


#     ================================
# --> Public entry
#     ================================

def build_summary_frame(reports: list[AlphaReport]) -> pd.DataFrame:
    """Wide flat one-row-per-alpha view for keep/drop sweep tables."""
    rows: list[dict[str, float | int | str | None]] = []

    for report in reports:
        row = _ic_row(report)

        row.update(_backtest_row(report))
        row.update(_robustness_row(report))
        row.update(_verdict_row(report))

        rows.append(row)

    return pd.DataFrame(rows).set_index("alpha")
