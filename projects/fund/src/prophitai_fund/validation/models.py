"""Output models for the Validator agent.

Defines the structured result the Validator produces after screening the
universe, running the vectorized backtest across bounded tuning runs, and
assigning a pass/fail verdict. Consumed by the strategy builder orchestrator
to confirm whether the strategy goes to paper trading.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ================================
# --> Helper models
# ================================


class TickerUniverse(BaseModel):
    """Universe produced by the screener for this strategy."""

    asset_class: Literal["equity", "etf"] = Field(
        description="Whether the screener used equity_screener or etf_screener",
    )
    tickers: list[str] = Field(
        description="Ticker symbols returned by the screener, post liquidity gate",
    )
    filters_applied: dict[str, str] = Field(
        default_factory=dict,
        description="Screener filter name -> stringified value, for the record",
    )


class BacktestRun(BaseModel):
    """One vectorized backtest run inside the tuning loop."""

    run_index: int = Field(description="0-indexed position in the 12-run budget")
    label: str = Field(
        description="Short human label for what was tuned this run (e.g. 'baseline', 'fast_ema=10, bb_window=15')",
    )
    param_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Strategy + sizing param overrides applied for this run, stringified",
    )
    metrics: dict[str, float] = Field(
        description="Raw metrics dict from BacktestResult.metrics (sharpe, max_drawdown, total_return, trade_count, etc.)",
    )
    sharpe: float = Field(description="Extracted Sharpe ratio for verdict comparison")
    ran_cleanly: bool = Field(
        description="True if the backtest script exited 0 and produced metrics",
    )
    error: Optional[str] = Field(
        None,
        description="Stderr/exception detail if ran_cleanly is False",
    )


# ================================
# --> Output model
# ================================


class ValidationVerdict(BaseModel):
    """Complete output from the Validator agent.

    The orchestrator consumes this directly. The verdict is also persisted
    to past_ideas.md via the past_ideas tool before the agent returns.
    """

    strategy_id: str = Field(description="Strategy identifier (e.g. 'omfm_15')")
    strategy_name: str = Field(
        description="Idea title as recorded in past_ideas.md — exact match required for update_verdict",
    )

    verdict: Literal["passed", "failed", "build_failure"] = Field(
        description=(
            "'passed' if best-run Sharpe > 0.8; 'failed' if the strategy ran but didn't clear. "
            "'build_failure' if the built code itself couldn't produce any clean run — "
            "this path does NOT update past_ideas.md and signals upstream fix needed."
        ),
    )

    universe: TickerUniverse = Field(description="Screened universe written to ticker_universe.py")

    runs: list[BacktestRun] = Field(
        description="All backtest runs executed during validation (up to 12)",
    )
    best_run_index: int = Field(
        description="Index into `runs` of the best Sharpe run (or -1 on build_failure)",
    )

    research_summary: str = Field(
        description=(
            "Markdown summary written to past_ideas.md — includes the universe, the tuning "
            "table, the best run's metrics, and the reasoning behind the verdict."
        ),
    )
