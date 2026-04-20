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
               Preflight uses this to pick the coverage check (per-ticker
               presence vs. single-blob presence).
        params: Provider-specific parameters. For ``"commodity"`` include
                ``{"symbol": "VIXUSD"}``; for ``"equity_price"`` include
                ``{"symbol": "SPY"}``; for ``"universe_returns"`` optionally
                ``{"return_type": "log"}`` (default ``"pct"``); for
                ``"economic_indicator"`` include ``{"indicator": "initialClaims"}``.
        min_coverage: Fraction of the universe (0.0–1.0) that must have this
            data populated after ``resolver.resolve()`` runs. ``scope="shared"``
            requirements are effectively binary — anything < 1.0 still triggers
            a failure if the blob is missing. Default ``0.8``.
        broadcast_as: When set, ``load_backtest_data()`` will broadcast the
            shared attr into every ticker's DataFrame as a column of this name.
            Only meaningful when ``scope="shared"``. The shared object must be
            a ``pd.Series`` or single-column ``pd.DataFrame`` indexed on dates.
            Example: ``DataRequirement(kind="equity_price", attrs_key="spy",
            scope="shared", params={"symbol": "SPY"}, broadcast_as="spy_close")``.
    """

    kind: str
    attrs_key: str
    scope: Literal["per_ticker", "shared"] = "per_ticker"
    params: dict[str, Any] = field(default_factory=dict)
    min_coverage: float = 0.8
    broadcast_as: str | None = None

    def __post_init__(self) -> None:
        # Reason: params=[] is a repeated builder-agent bug that raises TypeError
        # at provider.fetch(**req.params). Catch it here at construction time
        # with a readable message instead of deep inside the resolver.
        if not isinstance(self.params, dict):
            raise TypeError(
                f"DataRequirement.params must be a dict, got "
                f"{type(self.params).__name__}: {self.params!r}"
            )

        if not 0.0 <= self.min_coverage <= 1.0:
            raise ValueError(
                f"DataRequirement.min_coverage must be in [0.0, 1.0], "
                f"got {self.min_coverage}"
            )

        if self.broadcast_as is not None and self.scope != "shared":
            raise ValueError(
                f"DataRequirement.broadcast_as only valid when scope='shared' "
                f"(attrs_key={self.attrs_key!r}, scope={self.scope!r})"
            )
