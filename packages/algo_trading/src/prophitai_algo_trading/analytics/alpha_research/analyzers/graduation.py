"""Graduation flag — pre-defined thresholds across the analyzer suite.

Synthesizes IC + cost + stability + lag + FDR diagnostics into one
boolean ``passes`` flag with named per-criterion failure messages.
This is the agent's actual decision input: it stops debating individual
numbers and reads the flag.

Uses ``abs(ic_tstat)`` so "real but inverted" alphas (strong negative
IC — same signal, opposite trade direction) survive the IC test. The
FDR analyzer upstream uses two-sided p-values for the same reason.

A breakeven of ``inf`` (still profitable above the cost grid maximum)
counts as passing the cost test — ``inf`` is the strongest possible
result, not a missing value.
"""

from __future__ import annotations

import math

from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    AnalyticsConfig,
)


#     ================================
# --> Helper funcs
#     ================================

def _check_ic_tstat(report: AlphaReport, config: AnalyticsConfig) -> str | None:
    """Pass when ``|ic_tstat|`` clears the threshold; fail message otherwise."""
    if abs(report.ic_tstat) >= config.graduation_min_ic_tstat:
        return None

    return (
        f"ic_tstat |{report.ic_tstat:.2f}| < {config.graduation_min_ic_tstat}"
    )


def _check_breakeven(report: AlphaReport, config: AnalyticsConfig) -> str | None:
    """Pass when breakeven is ``inf`` or >= threshold; fail otherwise."""
    breakeven = report.cost_breakeven_bps

    if breakeven is None:
        return "cost_breakeven_bps undefined (unprofitable at zero cost)"

    if math.isinf(breakeven):
        return None

    if breakeven < config.graduation_min_breakeven_bps:
        return (
            f"cost_breakeven_bps {breakeven:.2f} < "
            f"{config.graduation_min_breakeven_bps}"
        )

    return None


def _check_subperiod(report: AlphaReport, config: AnalyticsConfig) -> str | None:
    """Pass when sub-period Sharpe ratio clears the threshold."""
    stability = report.subperiod_stability

    if stability is None:
        return "subperiod_stability missing (panel too short)"

    ratio = stability.get("sharpe_min_max_ratio")

    if ratio is None or (isinstance(ratio, float) and math.isnan(ratio)):
        return "subperiod sharpe ratio undefined (max sharpe non-positive)"

    if ratio < config.graduation_min_subperiod_sharpe_ratio:
        return (
            f"subperiod_sharpe_ratio {ratio:.3f} < "
            f"{config.graduation_min_subperiod_sharpe_ratio}"
        )

    return None


def _check_lag_decay(report: AlphaReport, config: AnalyticsConfig) -> str | None:
    """Pass when lag-decay ratio clears the threshold."""
    decay = report.lag_sharpe_decay

    if decay is None:
        return "lag_sharpe_decay undefined (lag-1 Sharpe non-positive)"

    if decay < config.graduation_min_lag_sharpe_decay:
        return (
            f"lag_sharpe_decay {decay:.3f} < "
            f"{config.graduation_min_lag_sharpe_decay}"
        )

    return None


def _check_fdr(report: AlphaReport, config: AnalyticsConfig) -> str | None:
    """Pass when ``passes_fdr=True``, or skip when not required."""
    if not config.graduation_require_passes_fdr:
        return None

    if report.passes_fdr is None:
        return "passes_fdr unset (FDR analyzer did not run)"

    if not report.passes_fdr:
        return "passes_fdr=False (did not survive multiple-testing correction)"

    return None


CHECKS = (
    _check_ic_tstat,
    _check_breakeven,
    _check_subperiod,
    _check_lag_decay,
    _check_fdr,
)


#     ================================
# --> Public analyzer
#     ================================

def evaluate_graduation(
    report: AlphaReport, config: AnalyticsConfig,
) -> tuple[bool, list[str]]:
    """Apply every graduation check; return ``(passes, failed_checks)``.

    Args:
        report: ``AlphaReport`` after FDR and clustering have already
            populated ``passes_fdr``.
        config: Active ``AnalyticsConfig``.

    Returns:
        ``(passes, failed)``:
            passes: True iff every check passed.
            failed: List of named failure messages (one per failed
                check). Empty when ``passes`` is True.
    """
    failed: list[str] = []

    for check in CHECKS:
        message = check(report, config)

        if message is not None:
            failed.append(f"graduation: {message}")

    return len(failed) == 0, failed
