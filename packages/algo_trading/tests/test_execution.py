"""Targeted tests for the 2 Phase 4 ExecutionModels.

Each scenario constructs an AlgorithmContext with known price data + a
portfolio in a known state, calls ``execute()``, and asserts the
resulting portfolio / broker calls. Real price data from the market_data
DB so fill-price math matches production behavior.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        packages/algo_trading/tests/test_execution.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

_PKG_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_PKG_SRC))

from prophitai_algo_trading.framework import (
    AlgorithmContext,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.execution import (
    BrokerExecutionModel,
    SimulatedExecutionModel,
)
from prophitai_algo_trading.portfolio import Portfolio, Position
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


UNIVERSE = ["AAPL", "MSFT", "NVDA", "META"]
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


class MockBroker:
    """Records every buy/sell/close_position call — no network, no real broker."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def buy(self, symbol: str, qty: Any) -> None:
        self.calls.append(("buy", symbol, qty))

    def sell(self, symbol: str, qty: Any) -> None:
        self.calls.append(("sell", symbol, qty))

    def close_position(self, symbol: str) -> None:
        self.calls.append(("close", symbol, None))


#     ================================
# --> Simulated — open new
#     ================================

def test_sim_open_long() -> None:
    print("\n--- SIM: open new long from flat ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _make_ctx(data, asof)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("AAPL", 100.0)])

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.direction == 1 and pos.shares == 100.0, \
        f"expected long 100 AAPL, got {pos}"
    print(f"  AAPL long {pos.shares} @ ${pos.entry_price:.2f}  OK")


def test_sim_open_short() -> None:
    print("\n--- SIM: open new short from flat ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _make_ctx(data, asof)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("MSFT", -50.0)])

    pos = ctx.portfolio.positions.get("MSFT")
    assert pos is not None and pos.direction == -1 and pos.shares == 50.0, \
        f"expected short 50 MSFT, got {pos}"
    print(f"  MSFT short {pos.shares} @ ${pos.entry_price:.2f}  OK")


#     ================================
# --> Simulated — close
#     ================================

def test_sim_close() -> None:
    print("\n--- SIM: close existing position (target=0) ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=200.0, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = 980_000.0

    ctx = _make_ctx(data, asof, portfolio=portfolio)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("AAPL", 0.0)])

    assert "AAPL" not in ctx.portfolio.positions, "AAPL should be closed"
    assert len(ctx.portfolio.trades) == 1, "one trade expected in log"
    print(f"  AAPL closed, trade logged: pnl=${ctx.portfolio.trades[0].pnl:.2f}  OK")


#     ================================
# --> Simulated — resize
#     ================================

def test_sim_resize_material() -> None:
    print("\n--- SIM: resize 100 -> 150 long (material change) ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    price = float(data["AAPL"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=price, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 100.0 * price

    ctx = _make_ctx(data, asof, portfolio=portfolio)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("AAPL", 150.0)])

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.shares == 150.0 and pos.direction == 1, \
        f"expected 150 AAPL long, got {pos}"
    print(f"  AAPL resized 100 -> 150 via close+reopen, trades logged: {len(ctx.portfolio.trades)}  OK")


def test_sim_resize_skip_under_tolerance() -> None:
    print("\n--- SIM: skip tiny rebalance (under 0.5% tolerance) ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    price = float(data["AAPL"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=price, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 100.0 * price

    ctx = _make_ctx(data, asof, portfolio=portfolio)

    model = SimulatedExecutionModel(min_change_pct=0.005)
    # Delta = 1 share * price; threshold = 0.005 * 1_000_000 = $5,000
    # AAPL price around $250 → 1 share ≈ $250 < $5,000 → should skip.
    model.execute(ctx, [PortfolioTarget("AAPL", 101.0)])

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.shares == 100.0, \
        f"expected unchanged 100 AAPL, got {pos.shares if pos else None}"
    assert len(ctx.portfolio.trades) == 0, "no trades should fire under tolerance"
    print(f"  delta notional ${price:.0f} < $5,000 threshold -> skipped, pos still 100  OK")


#     ================================
# --> Simulated — flip
#     ================================

def test_sim_flip() -> None:
    print("\n--- SIM: flip long -> short ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    price = float(data["AAPL"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["AAPL"] = Position(
        symbol="AAPL", shares=100.0, direction=1,
        entry_price=price, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 100.0 * price

    ctx = _make_ctx(data, asof, portfolio=portfolio)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("AAPL", -100.0)])

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.direction == -1 and pos.shares == 100.0, \
        f"expected -100 AAPL short after flip, got {pos}"
    print(f"  AAPL flipped: now short {pos.shares}  OK")


#     ================================
# --> Simulated — warmup
#     ================================

def test_sim_warmup_noop() -> None:
    print("\n--- SIM: warmup no-op ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _make_ctx(data, asof, warmup=True)

    model = SimulatedExecutionModel()
    model.execute(ctx, [PortfolioTarget("AAPL", 100.0)])

    assert len(ctx.portfolio.positions) == 0, "warmup should suppress all trades"
    print(f"  warmup=True: 0 positions opened despite target  OK")


#     ================================
# --> Broker — open long
#     ================================

def test_broker_open_long() -> None:
    print("\n--- BROKER: open new long fires buy() and mirrors into portfolio ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _make_ctx(data, asof)

    broker = MockBroker()
    model = BrokerExecutionModel(broker)
    model.execute(ctx, [PortfolioTarget("AAPL", 100.0)])

    assert broker.calls == [("buy", "AAPL", 100.0)], \
        f"expected one buy call, got {broker.calls}"

    pos = ctx.portfolio.positions.get("AAPL")
    assert pos is not None and pos.direction == 1 and pos.shares == 100.0, \
        f"mirror portfolio missing AAPL long, got {pos}"

    print(f"  broker call: {broker.calls[0]}")
    print(f"  mirror: AAPL long {pos.shares}  OK")


#     ================================
# --> Broker — close
#     ================================

def test_broker_close() -> None:
    print("\n--- BROKER: close fires close_position() and updates mirror ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["MSFT"] = Position(
        symbol="MSFT", shares=50.0, direction=-1,
        entry_price=float(data["MSFT"]["close"].iloc[-1]),
        entry_time=asof, entry_cost=0.0,
    )
    ctx = _make_ctx(data, asof, portfolio=portfolio)

    broker = MockBroker()
    model = BrokerExecutionModel(broker)
    model.execute(ctx, [PortfolioTarget("MSFT", 0.0)])

    assert broker.calls == [("close", "MSFT", None)], \
        f"expected one close call, got {broker.calls}"
    assert "MSFT" not in ctx.portfolio.positions, "mirror should reflect close"
    print(f"  broker call: {broker.calls[0]}, mirror closed  OK")


#     ================================
# --> Broker — flip fires close + short
#     ================================

def test_broker_flip() -> None:
    print("\n--- BROKER: flip long -> short fires close + sell ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    price = float(data["NVDA"]["close"].iloc[-1])

    portfolio = Portfolio(initial_capital=INITIAL_CAPITAL)
    portfolio.positions["NVDA"] = Position(
        symbol="NVDA", shares=200.0, direction=1,
        entry_price=price, entry_time=asof, entry_cost=0.0,
    )
    portfolio.cash = INITIAL_CAPITAL - 200.0 * price

    ctx = _make_ctx(data, asof, portfolio=portfolio)

    broker = MockBroker()
    model = BrokerExecutionModel(broker)
    model.execute(ctx, [PortfolioTarget("NVDA", -200.0)])

    expected = [("close", "NVDA", None), ("sell", "NVDA", 200.0)]
    assert broker.calls == expected, \
        f"expected close+sell, got {broker.calls}"

    pos = ctx.portfolio.positions.get("NVDA")
    assert pos is not None and pos.direction == -1 and pos.shares == 200.0, \
        f"mirror should reflect short, got {pos}"

    print(f"  broker calls: {broker.calls}, mirror flipped to short  OK")


#     ================================
# --> Broker — warmup no-op
#     ================================

def test_broker_warmup_noop() -> None:
    print("\n--- BROKER: warmup no-op ---")
    data = _load_bars()
    asof = max(df.index[-1] for df in data.values()).to_pydatetime()
    ctx = _make_ctx(data, asof, warmup=True)

    broker = MockBroker()
    model = BrokerExecutionModel(broker)
    model.execute(ctx, [PortfolioTarget("AAPL", 100.0)])

    assert broker.calls == [], f"warmup should not fire broker calls, got {broker.calls}"
    print(f"  warmup=True: 0 broker calls  OK")


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    # Simulated
    test_sim_open_long()
    test_sim_open_short()
    test_sim_close()
    test_sim_resize_material()
    test_sim_resize_skip_under_tolerance()
    test_sim_flip()
    test_sim_warmup_noop()

    # Broker
    test_broker_open_long()
    test_broker_close()
    test_broker_flip()
    test_broker_warmup_noop()

    print("\nAll execution tests passed.")


if __name__ == "__main__":
    main()
