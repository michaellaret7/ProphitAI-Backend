"""Smoke tests for the strategy scaffold package."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.execution.models import PortfolioContext
from prophitai_algo_trading.strategies.template import (
    TemplateRiskControlConfig,
    TemplateStrategy,
    build_event_backtest_engine,
    build_position_sizer,
    build_risk_controls,
    build_vectorized_backtest_engine,
)


def _build_price_frame() -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=160, freq="D")
    close = pd.Series(
        [100.0 + (i * 0.35) + ((i % 9) - 4) * 0.25 for i in range(len(index))],
        index=index,
        dtype=float,
    )
    return pd.DataFrame(
        {
            "open": close - 0.4,
            "high": close + 0.8,
            "low": close - 0.9,
            "close": close,
            "volume": 1_000_000.0,
        },
        index=index,
    )


def test_template_strategy_enriches_data_and_builds_candidates() -> None:
    strategy = TemplateStrategy()
    df = _build_price_frame()

    enriched = strategy.calculate_indicators(df)
    signals = strategy.generate_signals(enriched)
    scores = strategy.score_entries(enriched)
    latest_row = enriched.iloc[-1]
    latest_score = float(scores.iloc[-1])

    assert "ema_fast" in enriched.columns
    assert "ema_slow" in enriched.columns
    assert "rsi" in enriched.columns
    assert "trend_gap" in enriched.columns
    assert "stop_long" in enriched.columns
    assert "stop_short" in enriched.columns
    assert "regime" in enriched.columns
    assert set(signals) == {
        "long_entry",
        "long_exit",
        "short_entry",
        "short_exit",
    }
    assert len(scores) == len(enriched)
    assert strategy.min_bars_required == 50

    candidate = strategy.build_entry_candidate(
        symbol="AAPL",
        row=latest_row,
        target_position=1,
        timestamp=enriched.index[-1],
        score=latest_score,
    )

    assert candidate.symbol == "AAPL"
    assert candidate.stop_price is not None
    assert candidate.strategy_id == "TemplateStrategy"


def test_template_wiring_builds_engines_sizers_and_risk_controls() -> None:
    event_engine = build_event_backtest_engine()
    vector_engine = build_vectorized_backtest_engine()
    risk_controls = build_risk_controls(
        TemplateRiskControlConfig(
            enable_reentry_cooldown=True,
            enable_trailing_stop=True,
        )
    )

    sizer = build_position_sizer()
    shares = sizer.calculate_shares(
        symbol="AAPL",
        price=100.0,
        context=PortfolioContext(equity=100_000.0, cash=100_000.0, positions={}),
    )

    assert event_engine is not None
    assert vector_engine is not None
    assert len(risk_controls) == 2
    assert shares > 0
