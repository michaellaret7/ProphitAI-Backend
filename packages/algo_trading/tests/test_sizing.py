"""Unit tests for sizing policies and compatibility exports."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from prophitai_algo_trading.engines import VectorizedBacktestEngine
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import (
    Direction,
    PortfolioContext,
    TradeCandidate,
)
from prophitai_algo_trading.sizing import (
    ATRRiskSizer,
    BasePositionSizer,
    DrawdownScaledSizer,
    FixedQuantitySizer,
    InverseVolatilitySizer,
    PercentOfEquitySizer,
    VolatilityTargetSizer,
)
from prophitai_algo_trading.strategies.base import BaseStrategy


class _RecordingSizer(BasePositionSizer):
    def __init__(self):
        self.prepare_calls: list[dict[str, object]] = []

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        self.prepare_calls.append({
            "ticker_closes": {ticker: closes.copy() for ticker, closes in ticker_closes.items()},
            "latest_prices": dict(latest_prices or {}),
            "strategy_data": {
                ticker: frame.copy() for ticker, frame in (strategy_data or {}).items()
            },
            "timestamp": timestamp,
        })

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        return 1.0


class _SingleEntryStrategy(BaseStrategy):
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        enriched = df.copy()
        enriched["marker"] = range(len(enriched))
        return enriched

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.calculate_indicators(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        long_entry = pd.Series(False, index=df.index)
        long_entry.iloc[-1] = True
        empty = pd.Series(False, index=df.index)
        return {
            "long_entry": long_entry,
            "long_exit": empty,
            "short_entry": empty,
            "short_exit": empty,
        }


def test_percent_of_equity_sizer_caps_allocation_at_cash() -> None:
    sizer = PercentOfEquitySizer(pct=0.5, cost_model=CostModel(ptc=0.0))
    context = PortfolioContext(equity=10_000.0, cash=1_000.0, positions={})

    shares = sizer.calculate_shares("AAPL", 100.0, context)

    assert shares == pytest.approx(10.0)


def test_fixed_quantity_sizer_raises_when_cash_is_insufficient() -> None:
    sizer = FixedQuantitySizer(qty=5, cost_model=CostModel(ptc=0.0))
    context = PortfolioContext(equity=100.0, cash=100.0, positions={})

    with pytest.raises(ValueError, match="Insufficient cash"):
        sizer.calculate_shares("AAPL", 50.0, context)


def test_inverse_volatility_sizer_prefers_lower_volatility_assets() -> None:
    sizer = InverseVolatilitySizer(
        max_positions=2,
        max_weight=1.0,
        cost_model=CostModel(ptc=0.0),
    )
    calm = pd.Series([100.0, 100.2, 100.3, 100.4, 100.5])
    volatile = pd.Series([100.0, 105.0, 98.0, 108.0, 95.0])
    sizer.prepare_for_bar({"AAPL": calm, "TSLA": volatile})

    context = PortfolioContext(equity=10_000.0, cash=10_000.0, positions={})
    calm_shares = sizer.calculate_shares("AAPL", 100.0, context)
    volatile_shares = sizer.calculate_shares("TSLA", 100.0, context)

    assert calm_shares > volatile_shares


def test_atr_risk_sizer_uses_candidate_risk_per_share() -> None:
    sizer = ATRRiskSizer(
        risk_pct=0.01,
        max_pct_equity=1.0,
        cost_model=CostModel(ptc=0.0),
    )
    context = PortfolioContext(equity=10_000.0, cash=10_000.0, positions={})
    candidate = TradeCandidate(
        symbol="AAPL",
        direction=Direction.LONG,
        target_position=1,
        price=100.0,
        timestamp=datetime(2025, 1, 1),
        score=2.0,
        strategy_id="TestStrategy",
        risk_per_share=2.0,
    )

    shares = sizer.calculate_shares("AAPL", 100.0, context, candidate=candidate)

    assert shares == pytest.approx(50.0)


def test_volatility_target_sizer_allocates_less_to_higher_volatility() -> None:
    sizer = VolatilityTargetSizer(
        target_volatility=0.10,
        max_pct_equity=1.0,
        cost_model=CostModel(ptc=0.0),
    )
    context = PortfolioContext(equity=10_000.0, cash=10_000.0, positions={})
    calm = TradeCandidate(
        symbol="AAPL",
        direction=Direction.LONG,
        target_position=1,
        price=100.0,
        timestamp=datetime(2025, 1, 1),
        score=1.0,
        strategy_id="TestStrategy",
        volatility=0.10,
    )
    volatile = TradeCandidate(
        symbol="TSLA",
        direction=Direction.LONG,
        target_position=1,
        price=100.0,
        timestamp=datetime(2025, 1, 1),
        score=1.0,
        strategy_id="TestStrategy",
        volatility=0.40,
    )

    calm_shares = sizer.calculate_shares("AAPL", 100.0, context, candidate=calm)
    volatile_shares = sizer.calculate_shares("TSLA", 100.0, context, candidate=volatile)

    assert calm_shares > volatile_shares


def test_drawdown_scaled_sizer_reduces_wrapped_size() -> None:
    base = PercentOfEquitySizer(pct=0.20, cost_model=CostModel(ptc=0.0))
    sizer = DrawdownScaledSizer(
        base_sizer=base,
        soft_drawdown=0.05,
        hard_drawdown=0.15,
        min_scale=0.50,
    )
    context = PortfolioContext(
        equity=10_000.0,
        cash=10_000.0,
        positions={},
        peak_equity=12_000.0,
        drawdown_pct=0.10,
    )

    shares = sizer.calculate_shares("AAPL", 100.0, context)

    assert shares == pytest.approx(15.0)


def test_vectorized_engine_calls_prepare_for_bar_with_strategy_history() -> None:
    sizer = _RecordingSizer()
    engine = VectorizedBacktestEngine(
        strategy=_SingleEntryStrategy(),
        initial_capital=10_000.0,
        cost_model=CostModel(ptc=0.0),
        sizer=sizer,
        warmup_bars=0,
        max_positions=1,
    )
    index = pd.date_range("2025-01-01", periods=3, freq="D")
    data = {
        "AAPL": pd.DataFrame({
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1_000.0, 1_100.0, 1_200.0],
        }, index=index),
    }

    engine.run(data)

    assert len(sizer.prepare_calls) == 1
    call = sizer.prepare_calls[0]
    assert call["timestamp"] == index[-1]
    assert list(call["ticker_closes"]["AAPL"].index) == list(index)
    assert "marker" in call["strategy_data"]["AAPL"].columns
    assert list(call["strategy_data"]["AAPL"].index) == list(index)
    assert call["latest_prices"]["AAPL"] == pytest.approx(102.5)
