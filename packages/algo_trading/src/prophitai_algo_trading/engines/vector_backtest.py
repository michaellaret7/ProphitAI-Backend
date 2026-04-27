"""``VectorBacktest`` — pure signal-to-equity vectorized backtest.

Operates on full ``[date x ticker]`` panels rather than per-bar
context. The pipeline is short and explicit:

    panel ─▶ alpha.compute_panel(panel)         (per alpha)
          ─▶ pcm.build_weights({name: scores})  (single call)
          ─▶ shifted weights * forward returns
          ─▶ minus turnover penalty
          ─▶ cumprod → equity curve
          ─▶ calculate_metrics

No ``Portfolio``, no ``Position``, no ``Trade`` — those concepts live
in the event-driven engine. The vector engine is for rapid research
iteration; graduate proven candidates to ``Backtest`` for execution-
realistic validation (stops, drawdown rules, fill modeling, trade log).

``VectorDiagnostics`` is an optional second return value carrying the
intermediate panels (scores, weights, returns) for downstream
attribution / IC / correlation analysis. Set ``return_diagnostics=True``
on ``run`` to get them — the default keeps the call lean.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.analytics.metrics import (
    BacktestResult,
    calculate_metrics,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel
    from prophitai_algo_trading.algorithm.vector import VectorAlgorithm


#     ================================
# --> Diagnostics
#     ================================

@dataclass(frozen=True)
class VectorDiagnostics:
    """Intermediate panels surfaced for attribution / IC / correlation work.

    Attributes:
        scores: Per-alpha raw score panel — ``{alpha_name: DataFrame}``.
        weights: Final cadence-applied weight panel from the PCM.
        pre_cost_returns: Per-bar portfolio returns without turnover
            cost subtracted.
        bar_returns: Per-bar portfolio returns AFTER turnover cost.
        asset_returns: ``panel.close.pct_change()`` — handy for IC math.
        turnover: Per-bar absolute weight delta summed across tickers.
    """

    scores: dict[str, pd.DataFrame]
    weights: pd.DataFrame
    pre_cost_returns: pd.Series
    bar_returns: pd.Series
    asset_returns: pd.DataFrame
    turnover: pd.Series


#     ================================
# --> Helper funcs
#     ================================

def _validate_panel_alignment(
    name: str, score: pd.DataFrame, panel: "PricePanel",
) -> None:
    """Raise if ``score`` doesn't share index/columns with ``panel.close``.

    Catches alpha bugs early — a misaligned score panel produces silent
    NaN downstream that's hard to debug.
    """
    if not score.index.equals(panel.close.index):
        raise ValueError(
            f"Alpha '{name}' compute_panel returned mismatched index "
            f"({len(score.index)} rows vs panel {len(panel.close.index)})",
        )

    if list(score.columns) != list(panel.close.columns):
        raise ValueError(
            f"Alpha '{name}' compute_panel returned mismatched columns "
            f"({len(score.columns)} cols vs panel {len(panel.close.columns)})",
        )


def _compute_returns_block(
    weights: pd.DataFrame,
    panel: "PricePanel",
    cost_per_turnover: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Compute returns and intermediate panels in one pass.

    Uses ``weights.shift(1)`` so today's return is earned on yesterday's
    target weights — no lookahead. Returns enough intermediates that
    downstream code can compute attribution / IC / cost analysis without
    re-deriving anything.

    Args:
        weights: Signed ``[date x ticker]`` target-weight panel.
        panel: Price panel — uses ``close`` for forward returns.
        cost_per_turnover: Linear cost per unit of weight delta.

    Returns:
        Tuple of ``(asset_returns, aligned_weights, pre_cost_returns,
        bar_returns, turnover)``. ``bar_returns`` is the post-cost
        per-bar portfolio return.
    """
    asset_returns = panel.close.pct_change()

    aligned_weights = weights.reindex(
        index=panel.close.index, columns=panel.close.columns, fill_value=0.0,
    )

    pre_cost = (aligned_weights.shift(1) * asset_returns).sum(axis=1).fillna(0.0)

    turnover = aligned_weights.diff().abs().sum(axis=1).fillna(0.0)

    if cost_per_turnover > 0.0:
        bar_returns = pre_cost - turnover * cost_per_turnover
    else:
        bar_returns = pre_cost.copy()

    return asset_returns, aligned_weights, pre_cost, bar_returns, turnover


def _build_equity_curve(
    bar_returns: pd.Series, initial_capital: float,
) -> pd.DataFrame:
    """Cumprod of (1 + returns) scaled by initial capital.

    Returned shape matches the event-driven ``Portfolio.equity_curve()``
    output — ``equity`` column, datetime index — so ``calculate_metrics``
    consumes it without modification.
    """
    growth = (1.0 + bar_returns).cumprod()

    equity = growth * initial_capital

    return pd.DataFrame({"equity": equity, "cash": equity, "positions": 0})


#     ================================
# --> Vector backtest
#     ================================

class VectorBacktest:
    """Pure signal-to-equity vectorized engine.

    Args:
        verbose: When True, prints stage timings (alpha, pcm, returns)
            so iteration loops can spot the slow component.
    """

    def __init__(self, verbose: bool = False):
        self._verbose = verbose

    def run(
        self,
        algo: "VectorAlgorithm",
        panel: "PricePanel",
        benchmark: pd.Series | None = None,
    ) -> BacktestResult:
        """Run the full pipeline and return a ``BacktestResult``.

        Args:
            algo: Composed research spec — alphas + PCM + capital.
            panel: ``PricePanel`` with at minimum ``close``.
            benchmark: Optional benchmark price series for beta + alpha.

        Returns:
            ``BacktestResult`` with equity curve, empty trades frame,
            and the standard metrics dict from ``calculate_metrics``.
        """
        result, _ = self._run_internal(algo, panel, benchmark)

        return result

    def run_with_diagnostics(
        self,
        algo: "VectorAlgorithm",
        panel: "PricePanel",
        benchmark: pd.Series | None = None,
    ) -> tuple[BacktestResult, VectorDiagnostics]:
        """Same as ``run`` but also returns intermediate panels.

        Use this when you need scores + weights + bar returns for
        downstream attribution (IC, turnover analysis, correlation
        matrices). Identical compute path — the diagnostics are
        already produced internally; this signature just surfaces them.
        """
        return self._run_internal(algo, panel, benchmark)

    #     ================================
    # --> Internal pipeline
    #     ================================

    def _run_internal(
        self,
        algo: "VectorAlgorithm",
        panel: "PricePanel",
        benchmark: pd.Series | None,
    ) -> tuple[BacktestResult, VectorDiagnostics]:
        """Single source of truth for the vector pipeline."""
        if panel.close.empty:
            raise ValueError("panel is empty — nothing to backtest")

        scores = self._run_alphas(algo, panel)
        weights = self._run_pcm(algo, scores)

        asset_returns, aligned_weights, pre_cost, bar_returns, turnover = (
            _compute_returns_block(weights, panel, algo.cost_per_turnover)
        )

        equity_curve = _build_equity_curve(bar_returns, algo.initial_capital)

        empty_trades = pd.DataFrame(columns=[
            "symbol", "direction", "entry_time", "exit_time",
            "entry_price", "exit_price", "shares", "pnl", "return_pct",
            "entry_alphas", "exit_reason",
        ])

        metrics = calculate_metrics(
            equity_curve, empty_trades, benchmark=benchmark,
        )

        result = BacktestResult(
            equity_curve=equity_curve,
            trades=empty_trades,
            metrics=metrics,
        )

        diagnostics = VectorDiagnostics(
            scores=scores,
            weights=aligned_weights,
            pre_cost_returns=pre_cost,
            bar_returns=bar_returns,
            asset_returns=asset_returns,
            turnover=turnover,
        )

        return result, diagnostics

    #     ================================
    # --> Internal stages
    #     ================================

    def _run_alphas(
        self, algo: "VectorAlgorithm", panel: "PricePanel",
    ) -> dict[str, pd.DataFrame]:
        """Call every alpha's ``compute_panel`` and return the score map."""
        scores: dict[str, pd.DataFrame] = {}

        for alpha in algo.alphas:
            if not hasattr(alpha, "compute_panel"):
                raise TypeError(
                    f"Alpha '{alpha.name}' does not implement "
                    f"`compute_panel(panel)` — it cannot be run in the "
                    f"vector engine. Add a vectorized companion or run "
                    f"it through the event-driven Backtest instead.",
                )

            t0 = time.perf_counter()

            score = alpha.compute_panel(panel)

            elapsed = time.perf_counter() - t0

            _validate_panel_alignment(alpha.name, score, panel)

            scores[alpha.name] = score

            if self._verbose:
                print(f"  alpha {alpha.name:24s} {elapsed * 1000:8.1f} ms")

        return scores

    def _run_pcm(
        self,
        algo: "VectorAlgorithm",
        scores: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Hand scores to the PCM and return the weight panel."""
        if not hasattr(algo.pcm, "build_weights"):
            raise TypeError(
                f"PCM {type(algo.pcm).__name__} does not implement "
                f"`build_weights(scores)` — it cannot be run in the "
                f"vector engine. Use a PCM with a vectorized companion.",
            )

        t0 = time.perf_counter()

        weights = algo.pcm.build_weights(scores)

        elapsed = time.perf_counter() - t0

        if self._verbose:
            print(
                f"  pcm   {type(algo.pcm).__name__:24s} {elapsed * 1000:8.1f} ms",
            )

        return weights
