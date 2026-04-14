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
              ``"fundamentals"``, ``"commodity"``, ``"economic_indicator"``,
              ``"ticker_meta"``.
        attrs_key: Key in ``df.attrs`` where the fetched data is stored.
        scope: ``"per_ticker"`` when data varies by ticker (e.g. fundamentals),
               ``"shared"`` when the same data applies to all tickers (e.g. VIX).
        params: Provider-specific parameters. For ``"commodity"`` include
                ``{"symbol": "VIXUSD"}``, for ``"economic_indicator"`` include
                ``{"indicator": "initialClaims"}``, etc.
    """

    kind: str
    attrs_key: str
    scope: Literal["per_ticker", "shared"] = "per_ticker"
    params: dict[str, Any] = field(default_factory=dict)
