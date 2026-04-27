"""Integration tests for ``BarRunner.step`` and ``BarRunner.force_flatten``.

Wires a real ``Algorithm`` (one stub alpha, one PCM, one risk rule,
``ExecutionModel`` with ``PortfolioSink``), drives a single bar through
``step()``, and asserts the complete surface: position mutation,
lifecycle event firing, warmup suppression, and force_flatten cleanup.

Real price data from the market_data DB so fill-price math matches
production behavior.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_runner.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.engines import BarRunner
from prophitai_algo_trading.core import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.algorithm.event import Algorithm
from prophitai_algo_trading.execution import (
    ExecutionModel,
    PortfolioSink,
)
from prophitai_algo_trading.portfolio.portfolio import Portfolio, Position
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


UNIVERSE = ["AAPL", "MSFT"]
START = "2024-06-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Fixtures
#     ================================

def _load_bars() -> dict[str, pd.DataFrame]:
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


def _make_ctx(
    data: dict[str, pd.DataFrame],
    asof: datetime,
    portfolio: Portfolio | None = None,
    warmup: bool = False,
) -> AlgorithmContext:
    sliced: dict[str, pd.DataFrame] = {}
    for ticker, df in data.items():
        upto = df.loc[df.index <= pd.Timestamp(asof)]
        if not upto.empty:
            sliced[ticker] = upto

    return AlgorithmContext(
        timestamp=asof,
        portfolio=portfolio or Portfolio(initial_capital=INITIAL_CAPITAL),
        data=sliced,
        warmup=warmup,
    )


#     ================================
# --> Stub components
#     ================================

class StubAlpha:
    """Emits a fixed set of insights every bar."""

    name = "stub"
    lookback = 0

    def __init__(self, insights: list[Insight]):
        self._insights = insights

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        return list(self._insights)


class FixedTargetPCM:
    """Emits a fixed list of targets every bar, ignores insights."""

    def __init__(self, targets: list[PortfolioTarget]):
        self._targets = targets

    def create_targets(
        self, ctx: AlgorithmContext, insights: list[Insight],
    ) -> list[PortfolioTarget]:
        return list(self._targets)


class RecordingRiskModel:
    """Pass-through risk with lifecycle recording."""

    def __init__(self) -> None:
        self.opens: list[str] = []
        self.closes: list[tuple[str, float]] = []

    def manage(
        self, ctx: AlgorithmContext, targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        return targets

    def on_position_opened(
        self, ctx: AlgorithmContext, symbol: str,
    ) -> None:
        self.opens.append(symbol)

    def on_position_closed(
        self, ctx: AlgorithmContext, symbol: str, pnl: float,
    ) -> None:
        self.closes.append((symbol, pnl))


#     ================================
# --> step() scenarios
#     ================================

def test_step_opens_positions_and_fires_lifecycle() -> None:
    print("\n--- step(): target opens -> position + on_position_opened ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    risk = RecordingRiskModel()
    algo = Algorithm(
        alphas=[StubAlpha(insights=[])],
        portfolio_construction=FixedTargetPCM([PortfolioTarget("AAPL", 100.0)]),
        risk_management=risk,
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    ctx = _make_ctx(data, asof)
    runner = BarRunner(algo)
    runner.step(ctx)

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.direction == 1 and pos.shares == 100.0, \
        f"expected 100 AAPL long, got {pos}"
    assert risk.opens == ["AAPL"], f"expected open event for AAPL, got {risk.opens}"
    assert risk.closes == [], f"expected no closes, got {risk.closes}"
    print(f"  position: {pos.shares} AAPL long; opens={risk.opens}  OK")


def test_step_warmup_suppresses_execution_but_runs_pipeline() -> None:
    print("\n--- step(): warmup runs pipeline but execution no-ops ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    risk = RecordingRiskModel()
    algo = Algorithm(
        alphas=[StubAlpha(insights=[])],
        portfolio_construction=FixedTargetPCM([PortfolioTarget("AAPL", 100.0)]),
        risk_management=risk,
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    ctx = _make_ctx(data, asof, warmup=True)
    runner = BarRunner(algo)
    runner.step(ctx)

    assert len(ctx.portfolio.positions) == 0, \
        "warmup should suppress execution; no positions expected"
    assert risk.opens == [] and risk.closes == [], \
        f"no lifecycle events during warmup, got opens={risk.opens}, closes={risk.closes}"
    print(f"  warmup=True: 0 positions, 0 lifecycle events  OK")


def test_step_flip_fires_close_then_open() -> None:
    print("\n--- step(): flip long->short fires close AND open ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    price = float(data["AAPL"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=price, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 100.0 * price

    risk = RecordingRiskModel()
    algo = Algorithm(
        alphas=[StubAlpha(insights=[])],
        portfolio_construction=FixedTargetPCM([PortfolioTarget("AAPL", -100.0)]),
        risk_management=risk,
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    ctx = _make_ctx(data, asof, portfolio=portfolio)
    runner = BarRunner(algo)
    runner.step(ctx)

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.direction == -1, \
        f"expected short after flip, got {pos}"
    assert risk.closes and risk.closes[0][0] == "AAPL", \
        f"expected close event, got {risk.closes}"
    assert risk.opens == ["AAPL"], f"expected open event, got {risk.opens}"
    print(f"  flip: closes={risk.closes}, opens={risk.opens}  OK")


#     ================================
# --> force_flatten() scenarios
#     ================================

def test_force_flatten_closes_all_and_fires_events() -> None:
    print("\n--- force_flatten(): closes every position + fires on_position_closed ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    price_aapl = float(data["AAPL"]["close"].iloc[-1])
    price_msft = float(data["MSFT"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=price_aapl, entry_time=asof, entry_cost=0.0,
    )
    portfolio.positions["MSFT"] = Position(
        symbol="MSFT", shares=50.0, direction=-1,
        entry_price=price_msft, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 100.0 * price_aapl

    risk = RecordingRiskModel()
    algo = Algorithm(
        alphas=[StubAlpha(insights=[])],
        portfolio_construction=FixedTargetPCM([]),
        risk_management=risk,
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    ctx = _make_ctx(data, asof, portfolio=portfolio)
    runner = BarRunner(algo)
    runner.force_flatten(ctx)

    assert not ctx.portfolio.positions, \
        f"expected empty positions, got {list(ctx.portfolio.positions)}"
    assert len(ctx.portfolio.trades) == 2, \
        f"expected 2 trades logged, got {len(ctx.portfolio.trades)}"
    closed_symbols = {c[0] for c in risk.closes}
    assert closed_symbols == {"AAPL", "MSFT"}, \
        f"expected close events for AAPL + MSFT, got {risk.closes}"
    print(f"  all closed; trades={len(ctx.portfolio.trades)}; closes={risk.closes}  OK")


def test_force_flatten_noop_when_empty() -> None:
    print("\n--- force_flatten(): no positions -> no-op ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    risk = RecordingRiskModel()
    algo = Algorithm(
        alphas=[StubAlpha(insights=[])],
        portfolio_construction=FixedTargetPCM([]),
        risk_management=risk,
        execution=ExecutionModel(sink=PortfolioSink()),
    )

    ctx = _make_ctx(data, asof)
    runner = BarRunner(algo)
    runner.force_flatten(ctx)

    assert not ctx.portfolio.trades, "no trades expected on empty force_flatten"
    assert risk.closes == [], f"no lifecycle events expected, got {risk.closes}"
    print("  no-op on empty portfolio  OK")


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    test_step_opens_positions_and_fires_lifecycle()
    test_step_warmup_suppresses_execution_but_runs_pipeline()
    test_step_flip_fires_close_then_open()
    test_force_flatten_closes_all_and_fires_events()
    test_force_flatten_noop_when_empty()

    print("\nAll runner tests passed.")


if __name__ == "__main__":
    main()
