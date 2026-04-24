"""End-to-end integration test for the framework.

Builds a complete Algorithm (5 alphas + MultiAlphaBlend PCM + composite
risk + ``ExecutionModel(PortfolioSink())``), runs ``Backtest`` on 2
years of real daily OHLCV for a 20-ticker universe, and grades the
result against contract + sanity invariants.

This is the test that proves the deepened framework actually works —
all 4 stages chained end-to-end through a real engine against real data.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_end_to_end.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading import (
    Algorithm,
    Backtest,
    CostModel,
)
from prophitai_algo_trading.alphas import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.execution import (
    ExecutionModel,
    PortfolioSink,
)
from prophitai_algo_trading.portfolio_construction import (
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    PortfolioDrawdownLimit,
    StopLossExit,
)
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AVGO",
    "JPM", "BAC", "WFC", "GS",
    "JNJ", "UNH", "LLY", "PFE",
    "XOM", "CVX", "COP",
    "WMT",
]
START = "2023-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Data
#     ================================

def load_data() -> dict[str, pd.DataFrame]:
    print(f"Fetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END} ...")
    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}
    for ticker in UNIVERSE:
        df = bulk.get(ticker)
        if df is None or df.empty:
            continue
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]
        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")
    return ready


#     ================================
# --> Algorithm factory
#     ================================

def build_algorithm() -> Algorithm:
    return Algorithm(
        alphas=[
            MomentumAlpha(),
            BreakoutAlpha(),
            ShortTermReversalAlpha(),
            LowVolAlpha(),
            TrendVolumeAlpha(),
        ],
        portfolio_construction=MultiAlphaBlendPCM(
            weights={
                "momentum":  0.30,
                "breakout":  0.25,
                "reversal":  0.15,
                "low_vol":   0.15,
                "trend_vol": 0.15,
            },
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5,
                per_position_cap=0.10,
                quantile=0.20,
                min_abs_score=0.15,
            ),
        ),
        risk_management=CompositeRiskModel([
            MaxDrawdownRiskModel(
                max_drawdown_pct=0.15,
                delever_factor=0.5,
                cooldown_days=30,
            ),
            PortfolioDrawdownLimit(dd_pct=0.20),
            StopLossExit(pct=0.10),
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),
        execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
    )


#     ================================
# --> Grading
#     ================================

def grade(result) -> None:
    equity_curve = result.equity_curve
    trades = result.trades
    metrics = result.metrics

    print(f"\n  equity bars: {len(equity_curve)}")
    print(f"  trades closed: {len(trades)}")

    assert not equity_curve.empty, "equity curve is empty"
    assert (equity_curve["equity"] > 0).all(), "negative equity detected"

    print(f"\n  METRICS:")
    for key in [
        "total_return_pct", "annualized_return_pct",
        "max_drawdown_pct", "sharpe_ratio",
        "total_trades", "win_rate_pct", "profit_factor",
        "avg_win_pct", "avg_loss_pct",
    ]:
        val = metrics.get(key)
        if val is not None:
            print(f"    {key}: {val}")

    start_eq = float(equity_curve["equity"].iloc[0])
    end_eq = float(equity_curve["equity"].iloc[-1])
    print(f"\n  equity: ${start_eq:,.0f} -> ${end_eq:,.0f}  "
          f"({(end_eq / start_eq - 1.0) * 100:+.2f}%)")

    long_trades = (trades["direction"] == "long").sum() if not trades.empty else 0
    short_trades = (trades["direction"] == "short").sum() if not trades.empty else 0
    print(f"  trade breakdown: {long_trades}L / {short_trades}S")


#     ================================
# --> Main tests
#     ================================

def test_event_driven() -> None:
    print("\n=== Backtest end-to-end ===")
    data = load_data()
    algo = build_algorithm()

    engine = Backtest(
        algo, initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),
    )

    result = engine.run(data)
    grade(result)

    # Reason: sanity — positive-or-small-negative over a strong 2023-2024
    # bull run is the expected regime behavior. A -50% result means
    # something broke in the pipeline.
    total = result.metrics.get("total_return_pct")
    assert total is not None and total > -30.0, \
        f"Total return {total}% suggests pipeline failure"

    assert result.metrics["total_trades"] > 0, "no trades fired — pipeline broken"


def test_forced_stop_loss_fires() -> None:
    """A stop-loss at 2% (very tight) on a high-vol 2-year window should
    force at least one exit."""
    print("\n=== StopLossExit force exits on tight stop ===")
    data = load_data()

    tight_algo = Algorithm(
        alphas=[MomentumAlpha(), BreakoutAlpha()],
        portfolio_construction=MultiAlphaBlendPCM(
            weights={"momentum": 0.5, "breakout": 0.5},
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5, per_position_cap=0.10,
                quantile=0.25, min_abs_score=0.0,
            ),
        ),
        risk_management=StopLossExit(pct=0.02),
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    result = Backtest(
        tight_algo, initial_capital=INITIAL_CAPITAL,
    ).run(data)

    total_trades = len(result.trades)
    assert total_trades > 0, "no trades fired"

    # Reason: with a 2% stop in a volatile window, lots of trades should
    # close at small losses. Assert at least some losers exist.
    losing = (result.trades["pnl"] < 0).sum()
    print(f"  total trades: {total_trades}, losing trades: {losing}")
    assert losing > 0, "stops never fired"
    print(f"  stops forcing closes: OK")


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    test_event_driven()
    test_forced_stop_loss_fires()
    print("\nAll end-to-end tests passed.")


if __name__ == "__main__":
    main()
