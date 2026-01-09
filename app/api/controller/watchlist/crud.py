"""Watchlist data controller functions for charts and metrics."""

import asyncio
from datetime import timedelta
import hashlib
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List

from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.redis.client import cache
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_current_utc_time, get_utc_days_ago
from app.core.calculations.portfolio.correlation import CorrelationAnalysis


def _safe_round(value: Any, decimals: int = 4) -> Any:
    """Safely round numeric values, returning None for non-numeric types."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if np.isnan(value) or np.isinf(value):
            return None
        return round(value, decimals)
    return value


def _calculate_max_drawdown(prices: pd.Series) -> Optional[float]:
    """Calculate maximum drawdown from a price series.

    Returns the max drawdown as a negative decimal (e.g., -0.25 for 25% drawdown).
    """
    if prices is None or prices.empty or len(prices) < 2:
        return None
    prices = prices.dropna()
    if prices.empty:
        return None
    # Normalize to start at 1
    equity = prices / prices.iloc[0]
    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1.0
    max_dd = float(drawdown.min())
    return max_dd if np.isfinite(max_dd) else None


def _calculate_cagr(prices: pd.Series, years: float) -> Optional[float]:
    """Calculate Compound Annual Growth Rate from a price series.

    Args:
        prices: Price series
        years: Number of years for CAGR calculation

    Returns:
        CAGR as a decimal (e.g., 0.15 for 15% CAGR)
    """
    if prices is None or prices.empty or len(prices) < 2:
        return None
    prices = prices.dropna()
    if prices.empty or years <= 0:
        return None
    start_price = prices.iloc[0]
    end_price = prices.iloc[-1]
    if start_price <= 0:
        return None
    total_return = end_price / start_price
    cagr = (total_return ** (1.0 / years)) - 1.0
    return float(cagr) if np.isfinite(cagr) else None


def _calculate_performance_from_prices(
    prices: pd.Series,
    current_date: pd.Timestamp
) -> Dict[str, Optional[float]]:
    """Calculate CAGR and max drawdown metrics from historical price data.

    Args:
        prices: Full historical price series for a ticker
        current_date: Current UTC date for period calculations

    Returns:
        Dictionary with calculated performance metrics
    """
    result = {
        "5Y_CAGR": None,
        "3M_MaxDD": None,
        "6M_MaxDD": None,
        "1Y_MaxDD": None,
        "5Y_MaxDD": None,
        "ITD_MaxDD": None,
    }

    if prices is None or prices.empty:
        return result

    # Ensure index is DatetimeIndex
    if not isinstance(prices.index, pd.DatetimeIndex):
        return result

    prices = prices.sort_index()

    # Define lookback periods in days
    periods = {
        "3M": 63,    # ~3 months trading days
        "6M": 126,   # ~6 months trading days
        "1Y": 252,   # ~1 year trading days
        "5Y": 1260,  # ~5 years trading days
    }

    # Calculate max drawdown for each period
    for period_name, lookback_days in periods.items():
        lookback_date = current_date - pd.Timedelta(days=int(lookback_days * 365 / 252))
        period_prices = prices[prices.index >= lookback_date]
        if len(period_prices) >= 2:
            max_dd = _calculate_max_drawdown(period_prices)
            result[f"{period_name}_MaxDD"] = max_dd

    # ITD (Inception-to-date) max drawdown - use all available data
    result["ITD_MaxDD"] = _calculate_max_drawdown(prices)

    # 5Y CAGR calculation
    five_years_ago = current_date - pd.Timedelta(days=5 * 365)
    five_year_prices = prices[prices.index >= five_years_ago]
    if len(five_year_prices) >= 252:  # At least 1 year of data
        actual_days = (five_year_prices.index[-1] - five_year_prices.index[0]).days
        actual_years = actual_days / 365.0
        if actual_years >= 1.0:
            result["5Y_CAGR"] = _calculate_cagr(five_year_prices, actual_years)

    return result


def _build_metrics_for_ticker(
    ticker: str,
    quote_data: Dict[str, Any],
    ratios_data: Dict[str, Any],
    key_metrics_data: Dict[str, Any],
    price_change_data: Dict[str, Any],
    calculated_performance: Optional[Dict[str, Optional[float]]] = None,
) -> Dict[str, Any]:
    """Build structured metrics response for a single ticker.

    Organizes FMP data into frontend-friendly categories matching UI tabs.

    Args:
        ticker: Stock ticker symbol
        quote_data: Quote data from FMP
        ratios_data: TTM ratios from FMP
        key_metrics_data: Key metrics from FMP
        price_change_data: Price change percentages from FMP
        calculated_performance: CAGR and max drawdown metrics calculated from historical prices
    """
    if calculated_performance is None:
        calculated_performance = {}

    # Performance metrics (price change percentages + calculated metrics)
    performance = {
        "1D": _safe_round(price_change_data.get("1D")),
        "5D": _safe_round(price_change_data.get("5D")),
        "1M": _safe_round(price_change_data.get("1M")),
        "3M": _safe_round(price_change_data.get("3M")),
        "6M": _safe_round(price_change_data.get("6M")),
        "YTD": _safe_round(price_change_data.get("ytd")),
        "1Y": _safe_round(price_change_data.get("1Y")),
        "3Y": _safe_round(price_change_data.get("3Y")),
        "5Y": _safe_round(price_change_data.get("5Y")),
        # Calculated metrics from historical price data
        "5Y_CAGR": _safe_round(calculated_performance.get("5Y_CAGR")),
        "3M_MaxDD": _safe_round(calculated_performance.get("3M_MaxDD")),
        "6M_MaxDD": _safe_round(calculated_performance.get("6M_MaxDD")),
        "1Y_MaxDD": _safe_round(calculated_performance.get("1Y_MaxDD")),
        "5Y_MaxDD": _safe_round(calculated_performance.get("5Y_MaxDD")),
        "ITD_MaxDD": _safe_round(calculated_performance.get("ITD_MaxDD")),
    }

    # Valuation metrics
    valuation = {
        "price": _safe_round(quote_data.get("price"), 2),
        "marketCap": quote_data.get("marketCap"),
        "divYield": _safe_round(ratios_data.get("dividendYielTTM")),
        "pe": _safe_round(ratios_data.get("peRatioTTM"), 2),
        "peg": _safe_round(ratios_data.get("pegRatioTTM"), 2),
        "pb": _safe_round(ratios_data.get("priceToBookRatioTTM"), 2),
        "pSales": _safe_round(ratios_data.get("priceToSalesRatioTTM"), 2),
        "pFcf": _safe_round(ratios_data.get("priceToFreeCashFlowsRatioTTM"), 2),
        "pOcf": _safe_round(ratios_data.get("priceToOperatingCashFlowsRatioTTM"), 2),
        "evEbitda": _safe_round(ratios_data.get("enterpriseValueMultipleTTM"), 2),
        "payout": _safe_round(ratios_data.get("payoutRatioTTM")),
    }

    # Profitability metrics
    profitability = {
        "grossMargin": _safe_round(ratios_data.get("grossProfitMarginTTM")),
        "opMargin": _safe_round(ratios_data.get("operatingProfitMarginTTM")),
        "pretaxMargin": _safe_round(ratios_data.get("pretaxProfitMarginTTM")),
        "netMargin": _safe_round(ratios_data.get("netProfitMarginTTM")),
        "effTaxRate": _safe_round(ratios_data.get("effectiveTaxRateTTM")),
        "roa": _safe_round(ratios_data.get("returnOnAssetsTTM")),
        "roe": _safe_round(ratios_data.get("returnOnEquityTTM")),
        "roce": _safe_round(ratios_data.get("returnOnCapitalEmployedTTM")),
        # NI/EBT approximation: 1 - effective tax rate
        "niEbt": _safe_round(1 - ratios_data.get("effectiveTaxRateTTM", 0)) if ratios_data.get("effectiveTaxRateTTM") is not None else None,
        # EBT/EBIT: Use ebtPerEbitTTM if available, otherwise approximate
        "ebtEbit": _safe_round(ratios_data.get("ebtPerEbitTTM")),
    }

    # Cash Flow & Leverage metrics
    cash_flow_leverage = {
        "ocfPerShare": _safe_round(key_metrics_data.get("operatingCashFlowPerShareTTM"), 2),
        "fcfPerShare": _safe_round(key_metrics_data.get("freeCashFlowPerShareTTM"), 2),
        "cashPerShare": _safe_round(key_metrics_data.get("cashPerShareTTM"), 2),
        "ocfSales": _safe_round(ratios_data.get("operatingCashFlowSalesRatioTTM")),
        "fcfOcf": _safe_round(ratios_data.get("freeCashFlowOperatingCashFlowRatioTTM")),
        "capexCov": _safe_round(ratios_data.get("capitalExpenditureCoverageRatioTTM"), 2),
        # Div+CapEx Coverage: Use dividendPaidAndCapexCoverageRatioTTM
        "divCapexCov": _safe_round(ratios_data.get("dividendPaidAndCapexCoverageRatioTTM"), 2),
        "debtRatio": _safe_round(ratios_data.get("debtRatioTTM")),
        "de": _safe_round(ratios_data.get("debtEquityRatioTTM"), 2),
        "ltDebtCap": _safe_round(ratios_data.get("longTermDebtToCapitalizationTTM")),
        "debtCap": _safe_round(ratios_data.get("totalDebtToCapitalizationTTM")),
        "intCov": _safe_round(ratios_data.get("interestCoverageTTM"), 2),
        # Additional metrics
        "cfDebt": _safe_round(ratios_data.get("cashFlowToDebtRatioTTM"), 2),
        "stCov": _safe_round(ratios_data.get("shortTermCoverageRatiosTTM"), 2),
        "eqMult": _safe_round(ratios_data.get("companyEquityMultiplierTTM"), 2),
    }

    # Operating Metrics
    operating_metrics = {
        "currentRatio": _safe_round(ratios_data.get("currentRatioTTM"), 2),
        "quickRatio": _safe_round(ratios_data.get("quickRatioTTM"), 2),
        "cashRatio": _safe_round(ratios_data.get("cashRatioTTM"), 2),
        "dso": _safe_round(ratios_data.get("daysOfSalesOutstandingTTM"), 2),
        "dio": _safe_round(ratios_data.get("daysOfInventoryOutstandingTTM"), 2),
        "opCycle": _safe_round(ratios_data.get("operatingCycleTTM"), 2),
        "dpo": _safe_round(ratios_data.get("daysOfPayablesOutstandingTTM"), 2),
        "ccc": _safe_round(ratios_data.get("cashConversionCycleTTM"), 2),
        "recvTurn": _safe_round(ratios_data.get("receivablesTurnoverTTM"), 2),
        "payTurn": _safe_round(ratios_data.get("payablesTurnoverTTM"), 2),
        "invTurn": _safe_round(ratios_data.get("inventoryTurnoverTTM"), 2),
        "faTurn": _safe_round(ratios_data.get("fixedAssetTurnoverTTM"), 2),
        "assetTurn": _safe_round(ratios_data.get("assetTurnoverTTM"), 2),
    }

    return {
        "ticker": ticker,
        "name": quote_data.get("name", ""),
        "performance": performance,
        "valuation": valuation,
        "profitability": profitability,
        "cashFlowLeverage": cash_flow_leverage,
        "operatingMetrics": operating_metrics,
    }


@handle_controller_errors
async def get_watchlist_metrics_controller(
    *,
    tickers: List[str],
) -> Dict[str, Any]:
    """Get all financial metrics for a list of tickers.

    Fetches TTM ratios, key metrics, quotes, and price changes in parallel
    to provide all data needed for watchlist metrics tables.

    Cache TTL: 5 minutes (300s) - balances freshness with API rate limits.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        Response envelope with metrics organized by ticker and category
    """
    if not tickers:
        raise ValueError("tickers list cannot be empty")

    # Normalize tickers to uppercase and deduplicate
    tickers = list(set(t.upper() for t in tickers))

    # Generate cache key from sorted tickers using deterministic hash
    sorted_tickers = sorted(tickers)
    tickers_hash = hashlib.md5(",".join(sorted_tickers).encode()).hexdigest()[:16]
    cache_key = f"watchlist:metrics:{tickers_hash}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    fmp = FMP_API_DATA()

    # Fetch batch quote for all tickers at once
    batch_quotes = await asyncio.to_thread(fmp.get_batch_quote, tickers)
    quote_map = {}
    if batch_quotes:
        for quote in batch_quotes:
            symbol = quote.get("symbol")
            if symbol:
                quote_map[symbol] = quote

    # Define async fetchers for per-ticker data
    async def fetch_ratios(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_ratios_ttm, ticker)

    async def fetch_key_metrics(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_key_metrics_ttm, ticker)

    async def fetch_price_change(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_stock_price_change, ticker)

    async def fetch_historical_prices():
        """Fetch 5+ years of historical price data for CAGR and drawdown calculations."""
        current_date = get_current_utc_time()
        # Fetch 6 years of data to ensure 5Y calculations are accurate
        start_date = get_utc_days_ago(365 * 6)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = current_date.strftime("%Y-%m-%d")
        return await asyncio.to_thread(
            fetch_bulk_price_data_for_tickers,
            tickers,
            start_str,
            end_str,
            "daily"
        )

    # Fetch all data in parallel (including historical prices)
    ratios_results, metrics_results, price_results, historical_prices = await asyncio.gather(
        asyncio.gather(*[fetch_ratios(t) for t in tickers], return_exceptions=True),
        asyncio.gather(*[fetch_key_metrics(t) for t in tickers], return_exceptions=True),
        asyncio.gather(*[fetch_price_change(t) for t in tickers], return_exceptions=True),
        fetch_historical_prices(),
    )

    # Handle case where historical_prices fetch failed
    if isinstance(historical_prices, Exception):
        historical_prices = pd.DataFrame()

    # Process results into maps
    ratios_map = {}
    for result in ratios_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            ratios_map[ticker] = data[0]
        else:
            ratios_map[ticker] = {}

    metrics_map = {}
    for result in metrics_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            metrics_map[ticker] = data[0]
        else:
            metrics_map[ticker] = {}

    price_change_map = {}
    for result in price_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            price_change_map[ticker] = data[0]
        else:
            price_change_map[ticker] = {}

    # Calculate performance metrics from historical prices
    current_date = pd.Timestamp(get_current_utc_time())
    calculated_performance_map = {}
    for ticker in tickers:
        prices = historical_prices[ticker] if ticker in historical_prices.columns else None
        if prices is not None and not prices.empty:
            calculated_performance_map[ticker] = _calculate_performance_from_prices(
                prices, current_date
            )
        else:
            calculated_performance_map[ticker] = {}

    # Build response for each ticker
    payload = {}
    errors = []

    for ticker in tickers:
        quote_data = quote_map.get(ticker, {})
        ratios_data = ratios_map.get(ticker, {})
        key_metrics_data = metrics_map.get(ticker, {})
        price_change_data = price_change_map.get(ticker, {})
        calculated_performance = calculated_performance_map.get(ticker, {})

        # Check if we have any data for this ticker
        if not quote_data and not ratios_data:
            errors.append(ticker)
            continue

        payload[ticker] = _build_metrics_for_ticker(
            ticker=ticker,
            quote_data=quote_data,
            ratios_data=ratios_data,
            key_metrics_data=key_metrics_data,
            price_change_data=price_change_data,
            calculated_performance=calculated_performance,
        )

    # Build response envelope
    response = ok_envelope(
        message=f"Watchlist metrics retrieved successfully ({len(payload)} tickers)",
        kind="watchlists#metrics",
        self_link="/api/watchlists/metrics",
        counts={"totalItems": len(payload), "errors": len(errors)},
        payload={
            "data": payload,
            "errors": errors if errors else None,
        },
    )

    # Cache for 24 hours - ratios/metrics don't change frequently
    await cache.set(cache_key, response, ttl=86400)

    return response


async def get_watchlist_charts_controller(tickers: List[str]) -> Dict[str, Any]:
    """Get charts for a list of tickers."""

    # First check cache for the charts data
    tickers_hash = hashlib.md5(",".join(sorted(tickers)).encode()).hexdigest()
    cache_key = f"watchlist:charts:{tickers_hash}"
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    end_date = get_current_utc_time()
    start_date = end_date - timedelta(days=365 * 5)  # 5 years
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    prices = await asyncio.to_thread(fetch_bulk_price_data_for_tickers, tickers, start_date_str, end_date_str, "daily")

    # Convert pandas Series to dict with date strings as keys for JSON serialization
    # Reason: pandas Series serialize with numeric indices by default, not date strings
    prices_serializable = {}
    for ticker in prices.columns:
        series = prices[ticker]
        if series is not None and not series.empty:
            # Convert DatetimeIndex to date strings and values to floats
            prices_serializable[ticker] = {
                date.strftime("%Y-%m-%d"): round(float(price), 2)
                for date, price in series.items()
            }

    # Calculate multi-period correlations from returns
    if len(prices.columns) > 1:
        price_df = prices  # Already a DataFrame
        returns_df = price_df.pct_change().dropna()
        correlations = CorrelationAnalysis.multi_period_correlations(
            returns_df,
            matrix_periods=["1M", "3M", "6M", "9M", "1Y"],
            rolling_periods=["1M", "3M", "6M", "1Y", "5Y"]
        )
    else:
        correlations = {"matrix": {}, "rolling": {}}

    # Build response envelope
    response = ok_envelope(
        message=f"Watchlist charts retrieved successfully ({len(prices_serializable)} tickers)",
        kind="watchlists#charts",
        self_link="/api/watchlists/charts",
        counts={"totalItems": len(prices_serializable)},
        payload={
            "data": prices_serializable,
            "correlations": correlations,
        },
    )

    # Cache for 3 hours - price data updates throughout the day
    await cache.set(cache_key, response, ttl=10800)

    return response
