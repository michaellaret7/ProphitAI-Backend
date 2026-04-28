"""Pure-function analyzer modules for the alpha-research subsystem.

Every analyzer is a small module exporting one or more pure functions
that consume primitives (score panel, bar-returns series, forward-
return panels) and return a dict / scalar / Series. Analyzers know
nothing about ``AlphaReport`` — the runner is responsible for assembling
their outputs into the report.

Modules land here as features are added:
    PR 1: ic, stability, correlations
    PR 2: lag, cost
    PR 3: clustering, fdr, graduation
"""

from prophitai_algo_trading.analytics.alpha_research.analyzers.cadence import (
    STANDARD_CADENCES,
    best_cadence_label,
    compute_cadence_sweep,
)
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

__all__ = [
    # IC
    "compute_ic_series",
    "compute_ic_decay",
    "compute_ic_rolling",
    "summarize_ic",
    # Stability
    "compute_subperiod_stability",
    # Lag sensitivity
    "compute_lag_sensitivity",
    "lag_sharpe_decay_ratio",
    # Cost breakeven
    "compute_cost_breakeven",
    # Cross-alpha correlations
    "build_return_correlations",
    "top_correlations_for",
    # Clustering
    "cluster_by_correlation",
    # FDR
    "apply_fdr_correction",
    # Graduation
    "evaluate_graduation",
    # Cadence sweep
    "compute_cadence_sweep",
    "best_cadence_label",
    "STANDARD_CADENCES",
]
