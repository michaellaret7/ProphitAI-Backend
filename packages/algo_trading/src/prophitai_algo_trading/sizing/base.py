"""Base contract for position sizing policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.models import (
    PortfolioContext,
    SizingDecision,
    TradeCandidate,
)


class BasePositionSizer(ABC):
    """Abstract base for position sizing strategies."""

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        """Optional hook called once per bar before sizing decisions.

        Allows sizers to refresh internal state (e.g., volatility estimates)
        from current price data. Default does nothing.

        Args:
            ticker_closes: Mapping of ticker -> close price Series up to current bar.
            latest_prices: Latest known price per ticker.
            strategy_data: Latest per-ticker DataFrames with indicators.
            timestamp: Current bar timestamp.
        """

    def size_trade(
        self,
        candidate: TradeCandidate,
        context: PortfolioContext,
    ) -> SizingDecision:
        """Convert a trade candidate into a sizing decision."""
        shares = self.calculate_shares(
            candidate.symbol,
            candidate.price,
            context,
            candidate=candidate,
        )
        shares_f = float(shares) if not pd.isna(shares) else 0.0
        if shares_f <= 0:
            return SizingDecision(
                shares=0.0,
                target_notional=0.0,
                skip_reason="sizer returned no shares",
            )

        return SizingDecision(
            shares=shares_f,
            target_notional=shares_f * candidate.price,
        )

    @abstractmethod
    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        """Calculate the number of shares to trade.

        Args:
            symbol: Ticker symbol being traded.
            price: Current price per share.
            context: Current portfolio state (equity, cash, positions).
            candidate: Standardized trade candidate with sizing hints.

        Returns:
            Number of shares to trade.
        """
