"""Automatic data resolution for indicator supplementary data.

Walks a strategy's indicator suite, collects ``DataRequirement`` declarations,
and fetches / attaches all supplementary data (fundamentals, macro, etc.)
before the backtest runs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date as dt_date
from typing import Any

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_algo_trading.indicators.data_requirements import DataRequirement
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec

logger = logging.getLogger(__name__)


# ================================
# --> Helper funcs
# ================================


def _parse_date(value: str | dt_date) -> dt_date:
    """Coerce a string or date into a ``datetime.date``."""

    if isinstance(value, dt_date):
        return value

    return dt_date.fromisoformat(value)


def _build_fundamentals_df(
    result: object,
    ticker: str,
    sector: str,
) -> pd.DataFrame:
    """Convert a ``FundamentalsResult`` into the flat DataFrame expected by
    fundamental indicators.

    Joins income statements, balance sheets, and cash flow statements on their
    period end date to produce one row per fiscal quarter with columns:
        ticker, fiscal_quarter_end_date, accounts_receivable, inventory,
        accounts_payable, revenue, cogs, net_income, operating_cf, gics_sector
    """

    income_by_date: dict[str, dict] = {}
    for row in result.income_statements:
        if getattr(row, "period", "") == "FY":
            continue

        d = str(row.date)
        income_by_date[d] = {
            "revenue": float(row.revenue) if row.revenue is not None else None,
            "cogs": float(row.costOfRevenue) if row.costOfRevenue is not None else None,
            "net_income": float(row.netIncome) if row.netIncome is not None else None,
        }

    balance_by_date: dict[str, dict] = {}
    for row in result.balance_sheets:
        if getattr(row, "period", "") == "FY":
            continue

        d = str(row.date)
        balance_by_date[d] = {
            "accounts_receivable": float(row.netReceivables) if row.netReceivables is not None else None,
            "inventory": float(row.inventory) if row.inventory is not None else None,
            "accounts_payable": float(row.accountPayables) if row.accountPayables is not None else None,
        }

    cashflow_by_date: dict[str, dict] = {}
    for row in result.cash_flow_statements:
        if getattr(row, "period", "") == "FY":
            continue

        d = str(row.date)
        cashflow_by_date[d] = {
            "operating_cf": float(row.operatingCashFlow) if row.operatingCashFlow is not None else None,
        }

    all_dates = sorted(set(income_by_date) | set(balance_by_date) | set(cashflow_by_date))
    rows: list[dict] = []

    for d in all_dates:
        inc = income_by_date.get(d, {})
        bal = balance_by_date.get(d, {})
        cf = cashflow_by_date.get(d, {})

        rows.append({
            "ticker": ticker,
            "fiscal_quarter_end_date": pd.Timestamp(d),
            "accounts_receivable": bal.get("accounts_receivable"),
            "inventory": bal.get("inventory"),
            "accounts_payable": bal.get("accounts_payable"),
            "revenue": inc.get("revenue"),
            "cogs": inc.get("cogs"),
            "net_income": inc.get("net_income"),
            "operating_cf": cf.get("operating_cf"),
            "gics_sector": sector,
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("fiscal_quarter_end_date").reset_index(drop=True)


# ================================
# --> Base provider
# ================================


class BaseDataProvider(ABC):
    """Abstract provider that knows how to fetch and attach one kind of data."""

    @abstractmethod
    def fetch(
        self,
        tickers: list[str],
        start_date: dt_date,
        end_date: dt_date,
        **params: Any,
    ) -> Any:
        """Fetch data for the given tickers and date range."""

    @abstractmethod
    def attach(
        self,
        df: pd.DataFrame,
        ticker: str,
        fetched_data: Any,
        attrs_key: str,
    ) -> None:
        """Attach fetched data to a single ticker's DataFrame attrs."""


# ================================
# --> Standard providers
# ================================


class TickerMetaProvider(BaseDataProvider):
    """Attaches a ``{"symbol", "sector", "industry"}`` dict to ``df.attrs``.

    Bulk-queries the ``Ticker`` model once for the full universe and attaches
    a per-ticker metadata dict. Indicators that need sector/industry for proxy
    routing (e.g. sector-residual indicators) read
    ``df.attrs[attrs_key]["sector"]``. Missing rows return empty strings,
    never ``None``.
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> dict[str, dict[str, str]]:
        meta = self._bulk_meta(tickers)

        return {
            t: {
                "symbol": t,
                "sector": meta.get(t, ("", ""))[0],
                "industry": meta.get(t, ("", ""))[1],
            }
            for t in tickers
        }

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        df.attrs[attrs_key] = fetched_data.get(
            ticker,
            {"symbol": ticker, "sector": "", "industry": ""},
        )

    @staticmethod
    def _bulk_meta(tickers: list[str]) -> dict[str, tuple[str, str]]:
        """Single-query sector + industry lookup for the universe."""

        try:
            from prophitai_data.db.models.market import Ticker as TickerModel
            from prophitai_data.session.decorators import with_session

            @with_session("market")
            def _query(tkrs: list[str], session=None) -> dict[str, tuple[str, str]]:
                rows = (
                    session.query(TickerModel.ticker, TickerModel.sector, TickerModel.industry)
                    .filter(TickerModel.ticker.in_(tkrs))
                    .all()
                )

                return {r.ticker: (r.sector or "", r.industry or "") for r in rows}

            return _query(tickers)
        except Exception:
            logger.warning("Failed to fetch ticker metadata", exc_info=True)
            return {}


class FundamentalsProvider(BaseDataProvider):
    """Fetches quarterly fundamentals via ``get_bulk_fundamentals`` and sector
    metadata from the Ticker model."""

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> dict[str, Any]:
        from prophitai_data.repositories.fundamentals import get_bulk_fundamentals

        try:
            bulk_fund = get_bulk_fundamentals(tickers)
        except Exception:
            logger.warning("Failed to fetch bulk fundamentals", exc_info=True)
            bulk_fund = {}

        # Reason: need GICS sector for each ticker to populate gics_sector column
        sectors = self._get_sectors(tickers)

        return {"fundamentals": bulk_fund, "sectors": sectors}

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        bulk_fund = fetched_data["fundamentals"]
        sectors = fetched_data["sectors"]

        fund_result = bulk_fund.get(ticker)
        if fund_result is None:
            return

        sector = sectors.get(ticker, "")
        fund_df = _build_fundamentals_df(fund_result, ticker, sector)

        if not fund_df.empty:
            df.attrs[attrs_key] = fund_df

    @staticmethod
    def _get_sectors(tickers: list[str]) -> dict[str, str]:
        """Query GICS sector for each ticker from the Ticker model."""

        try:
            from prophitai_data.db.models.market import Ticker as TickerModel
            from prophitai_data.session.decorators import with_session

            @with_session("market")
            def _query(tkrs: list[str], session=None) -> dict[str, str]:
                rows = (
                    session.query(TickerModel.ticker, TickerModel.sector)
                    .filter(TickerModel.ticker.in_(tkrs))
                    .all()
                )

                return {r.ticker: (r.sector or "") for r in rows}

            return _query(tickers)
        except Exception:
            logger.warning("Failed to fetch ticker sectors", exc_info=True)
            return {}


class CommodityProvider(BaseDataProvider):
    """Fetches commodity price series via ``get_commodity_prices``."""

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.Series | None:
        from prophitai_data.repositories.macro import get_commodity_prices

        symbol = params.get("symbol", "")
        if not symbol:
            logger.warning("CommodityProvider requires 'symbol' param")
            return None

        try:
            df = get_commodity_prices(symbol=symbol, start_date=start_date, end_date=end_date)
        except Exception:
            logger.warning("Failed to fetch commodity %s", symbol, exc_info=True)
            return None

        if df.empty or "close" not in df.columns:
            return None

        series = df.set_index("date")["close"]
        series.index = pd.to_datetime(series.index).tz_localize(None).normalize()

        return series

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


class EquityPriceProvider(BaseDataProvider):
    """Fetches an equity or ETF close-price series via ``get_price_data_df``.

    Single-symbol provider, mirroring ``CommodityProvider``. Strategies that
    need SPY / sector ETF / any equity close series as a shared reference
    declare one ``DataRequirement`` per symbol. Attaches a tz-naive
    ``pd.Series`` of closes indexed on calendar dates to ``df.attrs``.
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.Series | None:
        from prophitai_algo_trading.data.repository.price_data import get_price_data_df

        symbol = params.get("symbol", "")
        if not symbol:
            logger.warning("EquityPriceProvider requires 'symbol' param")
            return None

        try:
            df = get_price_data_df(symbol=symbol, start_date=start_date, end_date=end_date, interval="daily")
        except Exception:
            logger.warning("Failed to fetch equity price for %s", symbol, exc_info=True)
            return None

        if df.empty or "close" not in df.columns:
            return None

        series = df["close"].copy()
        series.index = pd.to_datetime(series.index).tz_localize(None).normalize()

        return series

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


class UniverseReturnsProvider(BaseDataProvider):
    """Fetches cross-sectional daily returns for the full backtest universe.

    Builds a single DataFrame (date index × ticker columns) of daily returns
    and attaches it to every ticker's ``df.attrs`` — the same DataFrame
    reference across all tickers. Cross-sectional indicators (dispersion
    regimes, universe-relative z-scores, etc.) can read the full matrix from
    ``df.attrs[attrs_key]``.

    Params:
        return_type: ``"pct"`` (default) or ``"log"``.

    # TODO(perf): Re-fetches OHLCV the backtest already loaded. Add a
    # request-scoped lru_cache wrapper around get_price_data_df inside
    # load_strategy_data() if profiling shows this matters on large universes.
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.DataFrame | None:
        from prophitai_algo_trading.data.repository.price_data import get_price_data_df

        return_type = params.get("return_type", "pct")
        closes: dict[str, pd.Series] = {}

        for ticker in tickers:
            try:
                df = get_price_data_df(symbol=ticker, start_date=start_date, end_date=end_date, interval="daily")
            except Exception:
                logger.warning("Failed to fetch universe price for %s", ticker, exc_info=True)
                continue

            if df.empty or "close" not in df.columns:
                continue

            series = df["close"].copy()
            series.index = pd.to_datetime(series.index).tz_localize(None).normalize()

            closes[ticker] = series

        if not closes:
            return None

        prices = pd.DataFrame(closes).sort_index()

        if return_type == "log":
            import numpy as np

            returns = np.log(prices / prices.shift(1))
        else:
            returns = prices.pct_change()

        return returns

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


class EconomicIndicatorProvider(BaseDataProvider):
    """Fetches economic indicator series via ``get_economic_indicators``."""

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.Series | None:
        from prophitai_data.repositories.macro import get_economic_indicators

        indicator = params.get("indicator", "")
        if not indicator:
            logger.warning("EconomicIndicatorProvider requires 'indicator' param")
            return None

        try:
            df = get_economic_indicators(indicator=indicator, start_date=start_date, end_date=end_date)
        except Exception:
            logger.warning("Failed to fetch economic indicator %s", indicator, exc_info=True)
            return None

        if df.empty:
            return None

        series = df.set_index("date")["value"]
        series.index = pd.to_datetime(series.index).tz_localize(None).normalize()

        return series

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


class FinancialRatiosProvider(BaseDataProvider):
    """Fetches quarterly financial ratios from ``get_bulk_fundamentals``.

    Extracts the ``financial_ratios`` list from each ticker's
    ``FundamentalsResult`` and converts to a flat DataFrame with columns
    like ``date``, ``period``, ``currentRatio``, ``returnOnEquity``, etc.
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> dict[str, pd.DataFrame]:
        from prophitai_data.repositories.fundamentals import get_bulk_fundamentals

        try:
            bulk_fund = get_bulk_fundamentals(tickers)
        except Exception:
            logger.warning("Failed to fetch bulk fundamentals for ratios", exc_info=True)
            return {}

        result: dict[str, pd.DataFrame] = {}

        for ticker, fund in bulk_fund.items():
            rows = []

            for row in fund.financial_ratios:
                if getattr(row, "period", "") == "FY":
                    continue

                row_dict = {
                    col.name: getattr(row, col.name, None)
                    for col in row.__table__.columns
                    if col.name not in ("ticker_id",)
                }
                rows.append(row_dict)

            if rows:
                ratio_df = pd.DataFrame(rows)

                if "date" in ratio_df.columns:
                    ratio_df["date"] = pd.to_datetime(ratio_df["date"])
                    ratio_df = ratio_df.sort_values("date").reset_index(drop=True)

                result[ticker] = ratio_df

        return result

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        ratio_df = fetched_data.get(ticker)

        if ratio_df is not None and not ratio_df.empty:
            df.attrs[attrs_key] = ratio_df


class GovernmentBondRatesProvider(BaseDataProvider):
    """Fetches government bond yield curve via ``get_government_bond_rates``.

    Requires ``params={"country": "US"}`` (or another country code).
    Returns a DataFrame with date + yield columns (m1, m2, m3, m6, y1, ..., y30).
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.DataFrame | None:
        from prophitai_data.repositories.macro import get_government_bond_rates

        country = params.get("country", "")
        if not country:
            logger.warning("GovernmentBondRatesProvider requires 'country' param")
            return None

        try:
            df = get_government_bond_rates(country=country, start_date=start_date, end_date=end_date)
        except Exception:
            logger.warning("Failed to fetch bond rates for %s", country, exc_info=True)
            return None

        if df.empty:
            return None

        if "date" in df.columns:
            df = df.set_index("date")
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()

        return df

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


class EconomicCalendarProvider(BaseDataProvider):
    """Fetches economic calendar events via ``get_economic_calendar``.

    Requires ``params={"country": "US"}``. Optionally accepts ``event`` param
    to filter by specific event type.
    """

    def fetch(self, tickers: list[str], start_date: dt_date, end_date: dt_date, **params: Any) -> pd.DataFrame | None:
        from prophitai_data.repositories.macro import get_economic_calendar

        country = params.get("country", "")
        if not country:
            logger.warning("EconomicCalendarProvider requires 'country' param")
            return None

        event = params.get("event")

        try:
            df = get_economic_calendar(
                country=country,
                start_date=start_date,
                end_date=end_date,
                event=event,
            )
        except Exception:
            logger.warning("Failed to fetch economic calendar for %s", country, exc_info=True)
            return None

        if df.empty:
            return None

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        return df

    def attach(self, df: pd.DataFrame, ticker: str, fetched_data: Any, attrs_key: str) -> None:
        if fetched_data is not None:
            df.attrs[attrs_key] = fetched_data


# ================================
# --> Resolver
# ================================


class DataResolver:
    """Collects data requirements from an indicator suite and resolves them.

    Walks the suite's ``indicator_specs()``, extracts ``data_requirements``
    from each indicator class, deduplicates by ``attrs_key``, and uses
    registered providers to fetch and attach everything to the DataFrames.
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseDataProvider] = {}

    def register(self, kind: str, provider: BaseDataProvider) -> None:
        """Register a provider for a given data kind."""
        self._providers[kind] = provider

    def collect_requirements(self, suite: BaseIndicatorSuite) -> list[DataRequirement]:
        """Walk indicator specs and return deduplicated data requirements."""

        seen: set[str] = set()
        reqs: list[DataRequirement] = []

        for spec in suite.indicator_specs():
            indicator_cls = self._resolve_indicator_cls(spec)

            if indicator_cls is None:
                continue

            for req in indicator_cls.data_requirements:
                if req.attrs_key not in seen:
                    seen.add(req.attrs_key)
                    reqs.append(req)

        return reqs

    def validate(self, suite: BaseIndicatorSuite) -> list[str]:
        """Return warnings for any requirements without a registered provider."""

        warnings: list[str] = []

        for req in self.collect_requirements(suite):
            if req.kind not in self._providers:
                warnings.append(
                    f"No provider registered for kind={req.kind!r} "
                    f"(attrs_key={req.attrs_key!r}). Data will be missing."
                )

        return warnings

    def resolve(
        self,
        suite: BaseIndicatorSuite,
        data: dict[str, pd.DataFrame],
        start_date: str | dt_date,
        end_date: str | dt_date,
    ) -> dict[str, pd.DataFrame]:
        """Fetch and attach all supplementary data declared by the suite's indicators.

        Args:
            suite: The indicator suite whose indicators declare data requirements.
            data: Dict of {ticker: DataFrame} with OHLCV data already loaded.
            start_date: Start of the date range.
            end_date: End of the date range.

        Returns:
            The same ``data`` dict with ``df.attrs`` populated for each ticker.
        """

        requirements = self.collect_requirements(suite)

        if not requirements:
            return data

        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        tickers = list(data.keys())

        # Reason: fetch each requirement once, then attach to all tickers
        fetched_cache: dict[str, Any] = {}

        for req in requirements:
            provider = self._providers.get(req.kind)

            if provider is None:
                logger.warning(
                    "No provider for kind=%r (attrs_key=%r) — skipping",
                    req.kind,
                    req.attrs_key,
                )
                continue

            fetched_cache[req.attrs_key] = provider.fetch(
                tickers, sd, ed, **req.params,
            )

        # Attach to each DataFrame
        for ticker, df in data.items():
            for req in requirements:
                provider = self._providers.get(req.kind)

                if provider is None:
                    continue

                cached = fetched_cache.get(req.attrs_key)

                if cached is not None:
                    provider.attach(df, ticker, cached, req.attrs_key)

        return data

    @staticmethod
    def _resolve_indicator_cls(spec: IndicatorSpec) -> type[BaseIndicator] | None:
        """Extract the indicator class from a spec, resolving string keys via registry."""

        if isinstance(spec.indicator, type) and issubclass(spec.indicator, BaseIndicator):
            return spec.indicator

        # Reason: string keys reference std_lib indicators which typically have
        # no data requirements, but we still resolve them for completeness
        if isinstance(spec.indicator, str):
            try:
                from prophitai_algo_trading.indicators.registry import INDICATOR_REGISTRY

                return INDICATOR_REGISTRY.resolve(spec.indicator)
            except KeyError:
                return None

        return None


# ================================
# --> Factory and convenience
# ================================


def build_default_resolver() -> DataResolver:
    """Create a ``DataResolver`` with all standard providers registered.

    Standard kinds:
        ``"ticker_meta"``          — {symbol, sector, industry} dict attached to df.attrs
        ``"fundamentals"``         — quarterly income/balance/cashflow + sector
        ``"financial_ratios"``     — quarterly financial ratios (PE, ROE, margins, etc.)
        ``"commodity"``            — commodity price series (requires ``symbol`` param)
        ``"equity_price"``         — equity/ETF close series (requires ``symbol`` param)
        ``"universe_returns"``     — cross-sectional daily returns DataFrame (optional ``return_type`` param)
        ``"economic_indicator"``   — economic data series (requires ``indicator`` param)
        ``"government_bond_rates"``— yield curve data (requires ``country`` param)
        ``"economic_calendar"``    — economic event calendar (requires ``country`` param)
    """

    resolver = DataResolver()

    resolver.register("ticker_meta", TickerMetaProvider())
    resolver.register("fundamentals", FundamentalsProvider())
    resolver.register("financial_ratios", FinancialRatiosProvider())
    resolver.register("commodity", CommodityProvider())
    resolver.register("equity_price", EquityPriceProvider())
    resolver.register("universe_returns", UniverseReturnsProvider())
    resolver.register("economic_indicator", EconomicIndicatorProvider())
    resolver.register("government_bond_rates", GovernmentBondRatesProvider())
    resolver.register("economic_calendar", EconomicCalendarProvider())

    return resolver


def load_strategy_data(
    tickers: list[str],
    start_date: str,
    end_date: str,
    interval: str = "daily",
    indicator_suite: BaseIndicatorSuite | None = None,
) -> dict[str, pd.DataFrame]:
    """Load OHLCV price data and automatically resolve all indicator data requirements.

    This is the standard entry point for backtest data loading. It:
    1. Fetches OHLCV price data for each ticker
    2. Walks the indicator suite's ``data_requirements``
    3. Fetches and attaches all supplementary data to ``df.attrs``

    Args:
        tickers: Ticker symbols to load.
        start_date: Start date (ISO string).
        end_date: End date (ISO string).
        interval: Bar interval (e.g. ``"daily"``, ``"hourly"``).
        indicator_suite: The strategy's indicator suite. If provided, its
            indicators' ``data_requirements`` are resolved automatically.

    Returns:
        Dict of {ticker: DataFrame} for tickers with non-empty data.
    """

    from prophitai_algo_trading.data.repository.price_data import get_price_data_df

    data: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = get_price_data_df(
            symbol=ticker,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

        if not df.empty:
            data[ticker] = df

    if not data:
        return data

    # Reason: resolve supplementary data only when a suite is provided
    if indicator_suite is not None:
        resolver = build_default_resolver()

        warnings = resolver.validate(indicator_suite)
        for w in warnings:
            logger.warning(w)

        resolver.resolve(indicator_suite, data, start_date, end_date)

    return data
