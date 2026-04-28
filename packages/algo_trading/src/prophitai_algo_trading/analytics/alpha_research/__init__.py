"""Alpha-research subsystem — deep analytics on alpha signals.

Public surface:

    analyze_alpha    — single-alpha entry point
    analyze_alphas   — multi-alpha sweep with cross-cuts
    AlphaReport      — rich per-alpha result
    CrossAlphaReport — cross-alpha cross-cuts (summary, correlations)
    AnalyticsConfig  — every knob, frozen, defaults baked in

Every per-alpha analyzer is a pure function under ``analyzers/``.
The runner orchestrates them; the report dataclasses carry results.

PR 1 ships: IC + IC decay + IC rolling, sub-period stability, return
correlations, top-correlation projections. PR 2 adds lag + cost. PR 3
adds clustering + FDR + graduation flags.
"""

from prophitai_algo_trading.analytics.alpha_research.formatters import (
    print_alpha_report,
    print_alpha_research,
)
from prophitai_algo_trading.analytics.alpha_research.models import (
    AlphaReport,
    AnalyticsConfig,
    CrossAlphaReport,
)
from prophitai_algo_trading.analytics.alpha_research.runner import (
    analyze_alpha,
    analyze_alphas,
)

__all__ = [
    "AlphaReport",
    "AnalyticsConfig",
    "CrossAlphaReport",
    "analyze_alpha",
    "analyze_alphas",
    "print_alpha_report",
    "print_alpha_research",
]
