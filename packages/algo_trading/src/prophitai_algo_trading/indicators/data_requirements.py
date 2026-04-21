"""Declarative data requirements for indicator supplementary data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


# ================================
# --> Helper funcs
# ================================


# Reason: a recurring indicator-author bug is declaring kind="commodity"
# with symbol="SPY" (or QQQ, sector SPDR, etc.) because SPY resembles a
# continuous series. The commodity provider does not serve equities and
# silently returns empty, producing zero-trade backtests. Guard at
# construction time against any symbol on this whitelist.
_EQUITY_SYMBOLS_REQUIRING_EQUITY_PRICE_KIND: frozenset[str] = frozenset({
    # Broad-market ETFs
    "SPY", "VOO", "IVV", "QQQ", "QQQM", "DIA", "IWM", "IWB", "RSP", "VTI",
    # Sector SPDR ETFs (all 11 GICS)
    "XLC", "XLY", "XLP", "XLE", "XLF", "XLV", "XLI", "XLB", "XLRE", "XLK", "XLU",
    # Common factor / style ETFs
    "MTUM", "QUAL", "VLUE", "SIZE", "USMV", "SPLV",
    # International and bond bellwether ETFs (not commodities)
    "EFA", "EEM", "VEA", "VWO", "AGG", "BND", "TLT", "IEF", "SHY", "HYG", "LQD",
})


# ================================
# --> Public API
# ================================


@dataclass(frozen=True, slots=True)
class DataRequirement:
    """Declares a supplementary data dependency for an indicator.

    Indicators that read from ``df.attrs`` (e.g. fundamentals, macro series)
    declare their needs here so the data resolver can fetch and attach
    everything automatically before the backtest runs.

    Attributes:
        kind: Data source type. Standard kinds:
              ``"fundamentals"`` (raw quarterly line items — revenue,
              operatingIncome, netIncome, ...),
              ``"financial_ratios_ttm"`` (TTM ratios — dividendYield,
              returnOnEquity, priceToFreeCashFlowsRatio, ...; columns are
              also exposed with a ``TTM`` suffix so both naming conventions
              work), ``"commodity"``, ``"equity_price"``
              (use for SPY/QQQ/sector-ETF close series — NOT commodity),
              ``"universe_returns"``, ``"economic_indicator"``,
              ``"government_bond_rates"``,
              ``"economic_calendar"`` (macro events — Fed, CPI — scope=shared,
              requires ``country`` param),
              ``"earnings_calendar"`` (per-ticker quarterly announcement dates
              — scope=per_ticker, no params),
              ``"ticker_meta"``.
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

        if self.kind == "commodity":
            symbol = str(self.params.get("symbol", "")).upper()

            if symbol in _EQUITY_SYMBOLS_REQUIRING_EQUITY_PRICE_KIND:
                raise ValueError(
                    f"DataRequirement(kind='commodity', symbol={symbol!r}) is invalid — "
                    f"the commodity provider does not serve equities or ETFs. "
                    f"Use kind='equity_price' with the same symbol: "
                    f"DataRequirement(kind='equity_price', attrs_key={self.attrs_key!r}, "
                    f"scope={self.scope!r}, params={{'symbol': {symbol!r}}})."
                )
