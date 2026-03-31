"""Drawdown-aware wrapper for any base position sizer."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.models import PortfolioContext, TradeCandidate
from prophitai_algo_trading.sizing.base import BasePositionSizer


class DrawdownScaledSizer(BasePositionSizer):
    """Scale down another sizer as portfolio drawdown deepens."""

    def __init__(
        self,
        base_sizer: BasePositionSizer,
        soft_drawdown: float = 0.05,
        hard_drawdown: float = 0.15,
        min_scale: float = 0.25,
    ):
        self.base_sizer = base_sizer
        self.soft_drawdown = soft_drawdown
        self.hard_drawdown = hard_drawdown
        self.min_scale = min_scale

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        """Forward market prep to the wrapped sizer."""
        self.base_sizer.prepare_for_bar(
            ticker_closes,
            latest_prices=latest_prices,
            strategy_data=strategy_data,
            timestamp=timestamp,
        )

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        """Scale the wrapped sizer by current drawdown."""
        base_shares = self.base_sizer.calculate_shares(
            symbol,
            price,
            context,
            candidate=candidate,
        )
        if pd.isna(base_shares) or base_shares <= 0:
            return base_shares

        drawdown = max(0.0, context.drawdown_pct)
        if drawdown <= self.soft_drawdown:
            scale = 1.0
        elif drawdown >= self.hard_drawdown:
            scale = self.min_scale
        elif self.hard_drawdown <= self.soft_drawdown:
            scale = self.min_scale
        else:
            span = self.hard_drawdown - self.soft_drawdown
            progress = (drawdown - self.soft_drawdown) / span
            scale = 1.0 - progress * (1.0 - self.min_scale)

        return base_shares * scale
