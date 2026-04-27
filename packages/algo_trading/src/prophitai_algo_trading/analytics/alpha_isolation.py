"""Alpha isolation runner — backtest each alpha alone for attribution.

Loops every alpha through a fresh PCM and runs a standalone vector
backtest. Returns per-alpha ``BacktestResult`` objects, headline
metrics, and the diagnostics an LLM agent actually needs to make
"keep / drop / reweight" decisions on alphas:

    Information Coefficient (IC)     — signal quality, decoupled from
                                       sizing/PCM choice.
    Turnover + pre-cost return       — separates "bad signal" from
                                       "expensive to harvest."
    Pairwise return correlation      — independence question for
                                       multi-alpha blends.

This is the canonical "which alpha is pulling weight in my blend"
diagnostic. At ~70ms per alpha, an N-alpha sweep finishes faster than
one event-driven backtest — that's the entire point of the vector
engine.

Works with ANY alpha that implements ``compute_panel(panel)`` — pre-
built or user-written. The PCM is supplied via a factory so each
isolated run gets a fresh instance (avoids accidental state leakage
across runs in PCMs that carry rebalance / scheduler state).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import numpy as np
import pandas as pd

from prophitai_algo_trading.algorithm.vector import VectorAlgorithm
from prophitai_algo_trading.engines.vector_backtest import VectorBacktest

if TYPE_CHECKING:
    from prophitai_algo_trading.analytics.metrics import BacktestResult
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.core.protocols import VectorAlpha, VectorPCM
    from prophitai_algo_trading.engines.vector_backtest import VectorDiagnostics


SECONDS_PER_YEAR = 365.25 * 86_400
EPSILON = 1e-9


#     ================================
# --> Helper funcs
#     ================================

def _years_in_index(index: pd.DatetimeIndex) -> float:
    """Years spanned by the panel — used for annualizing turnover."""
    if len(index) < 2:
        return EPSILON

    span_seconds = (index[-1] - index[0]).total_seconds()

    return max(span_seconds / SECONDS_PER_YEAR, EPSILON)


def _compute_ic(
    score: pd.DataFrame,
    forward_returns: pd.DataFrame,
    horizon: int = 1,
) -> tuple[float, float]:
    """Mean per-date Spearman IC and its t-statistic.

    For each date, ranks tickers by alpha score and by ``horizon``-day
    forward return, computes the rank correlation, and averages across
    dates. The t-stat is the per-date IC mean divided by its standard
    error — values > ~2 indicate the IC is statistically reliable.

    Returns ``(0.0, 0.0)`` for degenerate inputs (all-NaN, single bar).

    Args:
        score: ``[date x ticker]`` raw alpha score panel.
        forward_returns: ``[date x ticker]`` forward asset returns —
            typically ``close.pct_change(horizon).shift(-horizon)``.
        horizon: Forward horizon in bars (1 = next-bar IC).

    Returns:
        ``(mean_ic, ic_tstat)``.
    """
    if score.empty or forward_returns.empty:
        return 0.0, 0.0

    aligned_score = score.reindex_like(forward_returns)

    # Reason: rank rows independently — Spearman = Pearson on ranks.
    ranked_score = aligned_score.rank(axis=1)
    ranked_ret = forward_returns.rank(axis=1)

    # Pearson rowwise: cov / (sd_x * sd_y).
    sx = ranked_score.sub(ranked_score.mean(axis=1), axis=0)
    sy = ranked_ret.sub(ranked_ret.mean(axis=1), axis=0)

    numer = (sx * sy).sum(axis=1)
    denom = np.sqrt((sx ** 2).sum(axis=1) * (sy ** 2).sum(axis=1))

    valid = denom > 0.0
    per_date_ic = pd.Series(np.where(valid, numer / denom.where(valid, 1.0), np.nan),
                            index=aligned_score.index)

    per_date_ic = per_date_ic.dropna()

    if per_date_ic.empty:
        return 0.0, 0.0

    mean_ic = float(per_date_ic.mean())
    std_ic = float(per_date_ic.std(ddof=1)) if len(per_date_ic) > 1 else 0.0

    if std_ic <= 0.0:
        return mean_ic, 0.0

    tstat = mean_ic / (std_ic / np.sqrt(len(per_date_ic)))

    return mean_ic, float(tstat)


def _summary_row(
    alpha_name: str,
    result: "BacktestResult",
    diagnostics: "VectorDiagnostics",
    pre_cost_metrics: dict[str, float],
    ic: float,
    ic_tstat: float,
    turnover_yr: float,
    elapsed_ms: float,
) -> dict[str, float | int | str | None]:
    """Pack one alpha's metrics into a flat row for the summary table."""
    metrics = result.metrics

    post_cost_total = metrics.get("total_return_pct")
    pre_cost_total = pre_cost_metrics.get("total_return_pct")

    cost_drag = (
        round(pre_cost_total - post_cost_total, 2)
        if pre_cost_total is not None and post_cost_total is not None
        else None
    )

    return {
        "alpha": alpha_name,
        "ic": round(ic, 4),
        "ic_tstat": round(ic_tstat, 2),
        "pre_cost_return_pct": pre_cost_total,
        "post_cost_return_pct": post_cost_total,
        "cost_drag_pct": cost_drag,
        "annualized_return_pct": metrics.get("annualized_return_pct"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "max_drawdown_pct": metrics.get("max_drawdown_pct"),
        "turnover_per_year": round(turnover_yr, 2),
        "alpha_vs_benchmark_pct": metrics.get("alpha_vs_benchmark_pct"),
        "beta_vs_benchmark": metrics.get("beta_vs_benchmark"),
        "elapsed_ms": round(elapsed_ms, 1),
    }


def _format_value(value: object) -> str:
    """Right-aligned printable cell for a metric value."""
    if value is None:
        return "n/a"

    if isinstance(value, (int, float)):
        return f"{value:.2f}" if isinstance(value, float) else f"{value}"

    return str(value)


def _pre_cost_metrics_from_returns(
    pre_cost_returns: pd.Series, initial_capital: float,
) -> dict[str, float]:
    """Recompute total + annualized return from the pre-cost return series.

    Avoids re-running the full ``calculate_metrics`` pipeline — we only
    need pre-cost total / annualized for the cost-drag column.
    """
    if pre_cost_returns.empty:
        return {"total_return_pct": 0.0, "annualized_return_pct": 0.0}

    growth = float((1.0 + pre_cost_returns).prod())
    total = (growth - 1.0) * 100.0

    years = _years_in_index(pre_cost_returns.index)  # type: ignore[arg-type]

    annualized = (growth ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

    return {
        "total_return_pct": round(total, 2),
        "annualized_return_pct": round(annualized, 2),
    }


#     ================================
# --> Report
#     ================================

@dataclass
class AlphaIsolationReport:
    """Container for per-alpha results, summary table, and diagnostics.

    Attributes:
        results: ``{alpha_name: BacktestResult}`` — full per-alpha
            output for downstream plotting / equity-curve overlays.
        summary: DataFrame indexed by alpha name with headline metrics
            including IC, turnover, pre/post-cost returns, Sharpe, MDD.
        return_correlations: Pairwise correlation matrix of per-alpha
            bar return series — the multi-alpha independence diagnostic.
        bar_returns: ``{alpha_name: bar_return_series}`` for downstream
            ensemble construction or correlation re-analysis.
    """

    results: dict[str, "BacktestResult"] = field(default_factory=dict)
    summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    return_correlations: pd.DataFrame = field(default_factory=pd.DataFrame)
    bar_returns: dict[str, pd.Series] = field(default_factory=dict)

    def to_agent_dict(self) -> dict[str, object]:
        """Compact JSON-serializable view for LLM agent consumption.

        Drops the heavy DataFrames and equity curves; keeps the
        decision-relevant numbers. Use this when wiring isolation
        output into an agent prompt.
        """
        return {
            "summary": self.summary.reset_index().to_dict(orient="records"),
            "return_correlations": self.return_correlations.round(3).to_dict(),
        }

    def print_summary(self) -> None:
        """Print a compact comparison table + correlation matrix."""
        if self.summary.empty:
            print("(no alphas were run)")
            return

        columns = [
            "ic",
            "ic_tstat",
            "pre_cost_return_pct",
            "post_cost_return_pct",
            "cost_drag_pct",
            "annualized_return_pct",
            "sharpe_ratio",
            "max_drawdown_pct",
            "turnover_per_year",
            "alpha_vs_benchmark_pct",
            "beta_vs_benchmark",
            "elapsed_ms",
        ]

        present = [c for c in columns if c in self.summary.columns]

        col_width = 12

        header = f"{'alpha':<20s}" + "".join(
            f" {c[:col_width]:>{col_width}s}" for c in present
        )

        print("\n" + header)
        print("-" * len(header))

        for alpha_name, row in self.summary.iterrows():
            line = f"{alpha_name:<20s}" + "".join(
                f" {_format_value(row[c]):>{col_width}s}" for c in present
            )

            print(line)

        if not self.return_correlations.empty:
            print("\nReturn correlations:")
            print(self.return_correlations.round(3).to_string())

        print()


#     ================================
# --> Isolation runner
#     ================================

def run_alpha_isolation(
    alphas: list["VectorAlpha"],
    pcm_factory: Callable[[], "VectorPCM"],
    panel: "PricePanel",
    initial_capital: float = 1_000_000.0,
    cost_per_turnover: float = 0.0001,
    benchmark: pd.Series | None = None,
    ic_horizon: int = 1,
    verbose: bool = False,
) -> AlphaIsolationReport:
    """Run every alpha alone through a fresh PCM and collect results.

    Each alpha is wrapped in a single-alpha ``VectorAlgorithm`` and
    executed by ``VectorBacktest.run_with_diagnostics``. The PCM
    factory is called once per alpha so internal state never leaks
    between isolated runs — important for PCMs that aren't fully
    stateless.

    The report carries:
      - ``results``: full ``BacktestResult`` per alpha
      - ``summary``: headline metrics + IC + turnover + pre/post-cost
      - ``return_correlations``: pairwise corr matrix of bar returns
      - ``bar_returns``: per-alpha return series for further analysis

    Args:
        alphas: One or more vectorized alphas. Each must implement
            ``compute_panel(panel) -> DataFrame`` and have a unique
            ``name``.
        pcm_factory: Zero-arg callable returning a fresh ``VectorPCM``
            each call. Use a ``lambda:`` to bake in your sizing config.
        panel: ``PricePanel`` of OHLCV data — same instance reused
            across every isolated run (the input is read-only).
        initial_capital: Notional starting equity per run.
        cost_per_turnover: Linear turnover penalty applied identically
            in every run so cross-alpha comparison is apples-to-apples.
        benchmark: Optional benchmark price series for beta + alpha
            metrics.
        ic_horizon: Forward-return horizon (bars) for IC computation.
            Default 1 = next-bar IC.
        verbose: When True, prints stage timings per alpha.

    Returns:
        ``AlphaIsolationReport``.
    """
    if not alphas:
        raise ValueError("run_alpha_isolation requires at least one alpha")

    seen: set[str] = set()

    for alpha in alphas:
        if alpha.name in seen:
            raise ValueError(
                f"Duplicate alpha name {alpha.name!r} — "
                f"isolation requires unique names",
            )

        seen.add(alpha.name)

    engine = VectorBacktest(verbose=verbose)

    forward_returns = panel.close.pct_change(ic_horizon).shift(-ic_horizon)

    results: dict[str, "BacktestResult"] = {}
    rows: list[dict[str, float | int | str | None]] = []
    bar_returns_map: dict[str, pd.Series] = {}

    for alpha in alphas:
        if verbose:
            print(f"\n--- isolating alpha: {alpha.name} ---")

        algo = VectorAlgorithm(
            alphas=[alpha],
            pcm=pcm_factory(),
            initial_capital=initial_capital,
            cost_per_turnover=cost_per_turnover,
        )

        t0 = time.perf_counter()

        result, diagnostics = engine.run_with_diagnostics(
            algo, panel, benchmark=benchmark,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        score_panel = diagnostics.scores[alpha.name]

        ic, ic_tstat = _compute_ic(
            score_panel, forward_returns, horizon=ic_horizon,
        )

        years = _years_in_index(diagnostics.turnover.index)  # type: ignore[arg-type]
        turnover_yr = float(diagnostics.turnover.sum()) / years

        pre_cost_metrics = _pre_cost_metrics_from_returns(
            diagnostics.pre_cost_returns, initial_capital,
        )

        results[alpha.name] = result
        bar_returns_map[alpha.name] = diagnostics.bar_returns

        rows.append(_summary_row(
            alpha.name, result, diagnostics, pre_cost_metrics,
            ic, ic_tstat, turnover_yr, elapsed_ms,
        ))

    summary = pd.DataFrame(rows).set_index("alpha")

    correlations = _build_correlation_matrix(bar_returns_map)

    return AlphaIsolationReport(
        results=results,
        summary=summary,
        return_correlations=correlations,
        bar_returns=bar_returns_map,
    )


#     ================================
# --> Correlation matrix
#     ================================

def _build_correlation_matrix(
    bar_returns_map: dict[str, pd.Series],
) -> pd.DataFrame:
    """Pearson correlation of per-alpha bar return series.

    Uses the union of indices; missing values become NaN and pandas
    handles them pairwise. Returns an empty DataFrame when fewer than
    two alphas are supplied.
    """
    if len(bar_returns_map) < 2:
        return pd.DataFrame()

    frame = pd.DataFrame(bar_returns_map)

    return frame.corr()
