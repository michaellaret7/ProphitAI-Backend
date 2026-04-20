"""Declarative data requirements for indicator supplementary data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class DataRequirement:
    """Declares a supplementary data dependency for an indicator.

    Indicators that read from ``df.attrs`` (e.g. fundamentals, macro series)
    declare their needs here so the data resolver can fetch and attach
    everything automatically before the backtest runs.

    Attributes:
        kind: Data source type. Standard kinds:
              ``"fundamentals"``, ``"financial_ratios"``, ``"commodity"``,
              ``"equity_price"``, ``"universe_returns"``,
              ``"economic_indicator"``, ``"government_bond_rates"``,
              ``"economic_calendar"``, ``"ticker_meta"``.
        attrs_key: Key in ``df.attrs`` where the fetched data is stored.
        scope: ``"per_ticker"`` when data varies by ticker (e.g. fundamentals),
               ``"shared"`` when the same data applies to all tickers (e.g. VIX).
               Informational only today — ``resolver.resolve()`` attaches the
               same fetched object to every ticker regardless. See
               ``resolver.py:455``.
        params: Provider-specific parameters. For ``"commodity"`` include
                ``{"symbol": "VIXUSD"}``; for ``"equity_price"`` include
                ``{"symbol": "SPY"}``; for ``"universe_returns"`` optionally
                ``{"return_type": "log"}`` (default ``"pct"``); for
                ``"economic_indicator"`` include ``{"indicator": "initialClaims"}``.
    """

    kind: str
    attrs_key: str
    scope: Literal["per_ticker", "shared"] = "per_ticker"
    params: dict[str, Any] = field(default_factory=dict)
