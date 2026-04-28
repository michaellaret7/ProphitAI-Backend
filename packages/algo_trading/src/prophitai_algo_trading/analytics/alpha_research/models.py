"""Dataclasses for the alpha-research subsystem.

Three contracts:

    AnalyticsConfig — every knob, frozen, defaults baked in. Fields are
        added incrementally as analyzers land (PR 1 ships IC + stability;
        PR 2 adds lag + cost; PR 3 adds FDR + clustering + graduation).

    AlphaReport — rich per-alpha result. Carries identity, signal-quality
        metrics, the headline backtest result, robustness diagnostics,
        and projections of the cross-alpha layer (top-correlations now;
        cluster_id / FDR fields land in PR 3).

    CrossAlphaReport — multi-alpha cross-cuts: the wide flat summary
        table, the full N x N return correlation matrix, and the
        clustering / FDR tables (populated in PR 3).

Both reports expose ``to_agent_dict`` for compact LLM-prompt views —
heavy DataFrames are dropped; scalars and short dicts are kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


#     ================================
# --> Config
#     ================================

@dataclass(frozen=True)
class AnalyticsConfig:
    """Every knob the alpha-research subsystem reads.

    Frozen so analyzers can rely on it not changing mid-pipeline. Tweak
    via ``dataclasses.replace(config, ic_primary_horizon=5)``.

    Attributes:
        initial_capital: Notional starting equity for the per-alpha
            vector backtest.
        cost_per_turnover: Linear turnover penalty applied identically
            to every isolated alpha so cross-alpha return comparison is
            apples-to-apples.
        ic_horizons: Forward-return horizons (in bars) used by the IC
            decay analyzer.
        ic_primary_horizon: Horizon whose IC is reported as the headline
            ``ic_mean`` / ``ic_tstat``. Must be present in
            ``ic_horizons``.
        ic_rolling_window: Bars used for the rolling IC series surfaced
            on ``AlphaReport``.
        subperiod_count: How many equal-length sub-periods the stability
            analyzer splits the panel into. Default 2 (halves).
        minimum_bars: Hard floor — analyses raise ``ValueError`` when
            ``len(panel.index) < minimum_bars``. Soft analyzer-specific
            insufficiency is recorded on ``AlphaReport.failure_reasons``.
        top_correlations_k: How many peers each alpha's
            ``top_correlations`` projection carries.
        keep_diagnostics: When True, ``AlphaReport`` retains ``scores``,
            ``weights``, and ``asset_returns`` panels — useful for
            downstream attribution. Off by default for memory.
        verbose: When True, prints per-stage timings.
    """

    initial_capital: float = 1_000_000.0
    cost_per_turnover: float = 0.0001

    ic_horizons: tuple[int, ...] = (1, 2, 5, 10, 20)
    ic_primary_horizon: int = 1
    ic_rolling_window: int = 60

    subperiod_count: int = 2

    lag_horizons: tuple[int, ...] = (1, 2, 3)

    cost_curve_bps: tuple[float, ...] = (0.0, 1.0, 5.0, 10.0, 20.0)

    fdr_alpha: float = 0.10

    cluster_distance_threshold: float = 0.30

    graduation_min_ic_tstat: float = 2.0
    graduation_min_breakeven_bps: float = 5.0
    graduation_min_subperiod_sharpe_ratio: float = 0.30
    graduation_min_lag_sharpe_decay: float = 0.50
    graduation_require_passes_fdr: bool = True

    minimum_bars: int = 30

    top_correlations_k: int = 5

    keep_diagnostics: bool = False

    verbose: bool = False

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")

        if self.cost_per_turnover < 0:
            raise ValueError("cost_per_turnover must be >= 0")

        if not self.ic_horizons:
            raise ValueError("ic_horizons must not be empty")

        if any(h < 1 for h in self.ic_horizons):
            raise ValueError("every ic_horizon must be >= 1")

        if self.ic_primary_horizon not in self.ic_horizons:
            raise ValueError(
                f"ic_primary_horizon={self.ic_primary_horizon} must be in "
                f"ic_horizons={self.ic_horizons}",
            )

        if self.ic_rolling_window < 2:
            raise ValueError("ic_rolling_window must be >= 2")

        if self.subperiod_count < 2:
            raise ValueError("subperiod_count must be >= 2")

        if not self.lag_horizons:
            raise ValueError("lag_horizons must not be empty")

        if any(h < 1 for h in self.lag_horizons):
            raise ValueError("every lag_horizon must be >= 1")

        if 1 not in self.lag_horizons:
            raise ValueError(
                "lag_horizons must include 1 — it's the baseline lag the "
                "rest of the metrics are reported against",
            )

        if not self.cost_curve_bps:
            raise ValueError("cost_curve_bps must not be empty")

        if any(c < 0.0 for c in self.cost_curve_bps):
            raise ValueError("every cost in cost_curve_bps must be >= 0")

        if not 0.0 < self.fdr_alpha < 1.0:
            raise ValueError("fdr_alpha must be in (0, 1)")

        if not 0.0 < self.cluster_distance_threshold <= 2.0:
            raise ValueError(
                "cluster_distance_threshold must be in (0, 2] — distance "
                "is 1 - |corr| so 0 is identical, 2 is antipodes",
            )

        if self.graduation_min_ic_tstat < 0.0:
            raise ValueError("graduation_min_ic_tstat must be >= 0")

        if self.graduation_min_breakeven_bps < 0.0:
            raise ValueError("graduation_min_breakeven_bps must be >= 0")

        if self.minimum_bars < 2:
            raise ValueError("minimum_bars must be >= 2")

        if self.top_correlations_k < 1:
            raise ValueError("top_correlations_k must be >= 1")


#     ================================
# --> Per-alpha report
#     ================================

@dataclass
class AlphaReport:
    """Full research output for a single alpha.

    Populated incrementally by the analyzers in ``runner.py``. Fields
    that depend on a cross-alpha sweep (``top_correlations``,
    ``cluster_id``, ``fdr_*``) are ``None`` when ``analyze_alpha`` is
    called standalone — they're back-filled by ``analyze_alphas`` after
    the cross-alpha layer runs.
    """

    # Identity
    name: str
    panel_window: tuple[pd.Timestamp, pd.Timestamp]
    bars: int
    tickers: int

    # Signal quality (populated by analyzers/ic.py)
    ic_mean: float = 0.0
    ic_tstat: float = 0.0
    ic_per_date: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    ic_decay: dict[int, float | None] = field(default_factory=dict)
    ic_decay_tstats: dict[int, float | None] = field(default_factory=dict)
    ic_hit_rate: float = 0.0
    ic_rolling: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    # Backtest (populated by facts builder + VectorBacktest)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    bar_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    pre_cost_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    metrics: dict[str, float | int | None] = field(default_factory=dict)
    turnover_per_year: float = 0.0
    cost_drag_pct: float | None = None

    # Robustness (populated by analyzers/stability.py + lag.py + cost.py)
    subperiod_stability: dict[str, Any] | None = None
    lag_sensitivity: dict[int, dict[str, float]] | None = None
    lag_sharpe_decay: float | None = None
    cost_breakeven_bps: float | None = None
    cost_curve: dict[float, float] | None = None

    # Cross-alpha projections (populated by analyze_alphas only)
    top_correlations: list[tuple[str, float]] | None = None
    cluster_id: int | None = None
    cluster_peers: list[str] | None = None
    fdr_adjusted_pvalue: float | None = None
    passes_fdr: bool | None = None

    # Synthesis (PR 3 graduation analyzer)
    passes: bool | None = None

    # Failure tracking
    failure_reasons: list[str] = field(default_factory=list)

    # Optional diagnostics passthrough — only populated when
    # AnalyticsConfig.keep_diagnostics=True.
    scores: pd.DataFrame | None = None
    weights: pd.DataFrame | None = None
    asset_returns: pd.DataFrame | None = None

    @property
    def has_failures(self) -> bool:
        """True if any analyzer logged a soft failure on this report."""
        return len(self.failure_reasons) > 0

    def to_agent_dict(self) -> dict[str, Any]:
        """Compact, JSON-serializable view for LLM prompts.

        Drops every Series / DataFrame field — keeps the scalar
        decision-relevant numbers, the IC decay dict, and the
        cross-alpha projection scalars.
        """
        return {
            "name": self.name,
            "bars": self.bars,
            "tickers": self.tickers,
            "ic_mean": round(self.ic_mean, 4),
            "ic_tstat": round(self.ic_tstat, 2),
            "ic_hit_rate": round(self.ic_hit_rate, 3),
            "ic_decay": {h: _round_or_none(v, 4) for h, v in self.ic_decay.items()},
            "ic_decay_tstats": {
                h: _round_or_none(v, 2) for h, v in self.ic_decay_tstats.items()
            },
            "metrics": self.metrics,
            "turnover_per_year": round(self.turnover_per_year, 2),
            "cost_drag_pct": self.cost_drag_pct,
            "subperiod_stability": self.subperiod_stability,
            "lag_sensitivity": self.lag_sensitivity,
            "lag_sharpe_decay": _round_or_none(self.lag_sharpe_decay, 3),
            "cost_breakeven_bps": _round_or_none(self.cost_breakeven_bps, 2),
            "cost_curve": self.cost_curve,
            "top_correlations": self.top_correlations,
            "cluster_id": self.cluster_id,
            "cluster_peers": self.cluster_peers,
            "fdr_adjusted_pvalue": _round_or_none(self.fdr_adjusted_pvalue, 4),
            "passes_fdr": self.passes_fdr,
            "passes": self.passes,
            "failure_reasons": self.failure_reasons,
        }


#     ================================
# --> Cross-alpha report
#     ================================

@dataclass
class CrossAlphaReport:
    """Multi-alpha cross-cuts: summary table, correlations, clustering.

    Populated by ``analyze_alphas`` only. When N=1 (standalone
    ``analyze_alpha``), this object is not produced — the per-alpha
    ``AlphaReport`` is the entire result.
    """

    summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    return_correlations: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Populated in PR 3
    clusters: dict[int, list[str]] = field(default_factory=dict)
    linkage: Any | None = None
    fdr_table: pd.DataFrame = field(default_factory=pd.DataFrame)

    def to_agent_dict(self) -> dict[str, Any]:
        """Compact LLM-prompt view of the multi-alpha layer."""
        return {
            "summary": self.summary.reset_index().to_dict(orient="records"),
            "return_correlations": self.return_correlations.round(3).to_dict(),
            "clusters": self.clusters,
            "fdr_table": (
                self.fdr_table.reset_index().to_dict(orient="records")
                if not self.fdr_table.empty
                else []
            ),
        }


#     ================================
# --> Helper funcs
#     ================================

def _round_or_none(value: float | None, digits: int) -> float | None:
    """Round ``value`` to ``digits`` decimals, passing ``None`` through."""
    if value is None:
        return None

    return round(value, digits)
