"""Indicator composition for RSI mean reversion strategy."""

from __future__ import annotations

from collections.abc import Sequence

from prophitai_algo_trading.indicators import BaseIndicatorSuite, IndicatorSpec


class RSIMeanReversionIndicatorSuite(BaseIndicatorSuite):
    """Compose shared indicators for the RSI mean-reversion strategy."""

    def __init__(
        self,
        rsi_period: int,
        trend_sma_period: int,
        exit_sma_period: int,
    ):
        self.rsi_period = rsi_period
        self.trend_sma_period = trend_sma_period
        self.exit_sma_period = exit_sma_period
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        return (
            IndicatorSpec(
                indicator="rsi",
                params={"period": self.rsi_period},
                description="Fast RSI oscillator for mean-reversion entries.",
            ),
            IndicatorSpec(
                indicator="sma",
                params={
                    "window": self.trend_sma_period,
                    "output_column": "sma_trend",
                },
                description="Trend filter moving average.",
            ),
            IndicatorSpec(
                indicator="sma",
                params={
                    "window": self.exit_sma_period,
                    "output_column": "sma_exit",
                },
                description="Fast exit moving average.",
            ),
        )
