"""Dashboard controller — aggregates all dashboard data in parallel."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_data.db.models.market import Ticker
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_api.cache.redis_client import cache
from prophitai_api.services.broker.account import get_balances
from prophitai_api.services.broker.trading import get_positions, get_orders, get_portfolio_performance
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_data.repositories.user.account import get_connection_status
from prophitai_data.session.decorators import with_session
from prophitai_api.utils.serialize_output import serialize_sqlalchemy_obj

logger = logging.getLogger(__name__)

fmp = FMP_API_DATA()

# Cache TTLs (seconds)
TREASURY_CACHE_TTL = 3600   # 1 hour
NEWS_CACHE_TTL = 300         # 5 minutes
BALANCES_CACHE_TTL = 30      # 30 seconds
POSITIONS_CACHE_TTL = 30     # 30 seconds
ORDERS_CACHE_TTL = 60        # 1 minute
PERFORMANCE_CACHE_TTL = 300  # 5 minutes

# Cache keys
TREASURY_CACHE_KEY = "dashboard:treasury:latest"
NEWS_CACHE_KEY = "dashboard:general_news:latest"
BALANCES_CACHE_KEY = "dashboard:{clerk_id}:balances"
POSITIONS_CACHE_KEY = "dashboard:{clerk_id}:positions"
ORDERS_CACHE_KEY = "dashboard:{clerk_id}:orders"
PERFORMANCE_CACHE_KEY = "dashboard:{clerk_id}:performance"


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _safe_result(result: Any) -> Optional[Any]:
    """Return None if the result is an Exception, otherwise return it."""
    if isinstance(result, Exception):
        logger.warning("Dashboard gather task failed: %s", result)
        return None
    return result


def _compute_sector_breakdown(
    positions: List[Dict],
    ticker_info_map: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """Group positions by sector, compute weight percentages."""
    sector_mv: Dict[str, float] = {}
    total_mv = 0.0

    for pos in positions:
        # Reason: option positions use underlying_ticker for sector lookup
        ticker = (
            pos.get("underlying_ticker") or pos.get("ticker", "")
            if pos.get("position_type") == "option"
            else pos.get("ticker", "")
        )
        mv = float(pos.get("market_value") or 0)
        info = ticker_info_map.get(ticker, {})
        sector = info.get("sector") or "Unknown"

        sector_mv[sector] = sector_mv.get(sector, 0.0) + mv
        total_mv += mv

    if total_mv == 0:
        return []

    return [
        {
            "sector": sector,
            "weight": round(mv / total_mv, 4),
            "marketValue": round(mv, 2),
        }
        for sector, mv in sorted(sector_mv.items(), key=lambda x: x[1], reverse=True)
    ]


def _compute_industry_breakdown(
    positions: List[Dict],
    ticker_info_map: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """Group positions by industry, compute weight percentages."""
    industry_mv: Dict[str, float] = {}
    total_mv = 0.0

    for pos in positions:
        # Reason: option positions use underlying_ticker for industry lookup
        ticker = (
            pos.get("underlying_ticker") or pos.get("ticker", "")
            if pos.get("position_type") == "option"
            else pos.get("ticker", "")
        )
        mv = float(pos.get("market_value") or 0)
        info = ticker_info_map.get(ticker, {})
        industry = info.get("industry") or "Unknown"

        industry_mv[industry] = industry_mv.get(industry, 0.0) + mv
        total_mv += mv

    if total_mv == 0:
        return []

    return [
        {
            "industry": industry,
            "weight": round(mv / total_mv, 4),
            "marketValue": round(mv, 2),
        }
        for industry, mv in sorted(industry_mv.items(), key=lambda x: x[1], reverse=True)
    ]


@with_session('market')
def _fetch_ticker_info_batch(tickers: List[str], session=None) -> Dict[str, Dict]:
    """Single DB query for ticker metadata. Returns {ticker: serialized_dict}."""
    rows = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    result: Dict[str, Dict] = {}
    for row in rows:
        serialized = serialize_sqlalchemy_obj(row)
        if serialized is not None:
            result[str(row.ticker)] = serialized
    return result


def _enrich_positions(
    positions: List[Dict],
    ticker_info_map: Dict[str, Dict],
) -> List[Dict]:
    """Merge sector/industry/beta/tickerName from ticker info into each position."""
    enriched = []
    for pos in positions:
        # Reason: option positions use underlying_ticker for metadata lookup
        lookup_ticker = (
            pos.get("underlying_ticker") or pos.get("ticker", "")
            if pos.get("position_type") == "option"
            else pos.get("ticker", "")
        )
        info = ticker_info_map.get(lookup_ticker, {})
        enriched.append({
            **pos,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "beta": info.get("beta"),
            "tickerName": info.get("ticker_name"),
        })
    return enriched


def _extract_treasury_snapshot(rates: Optional[Any]) -> Optional[Dict]:
    """Extract latest treasury rates entry."""
    if not rates or not isinstance(rates, list) or len(rates) == 0:
        return None
    latest = rates[0]
    return {
        "date": latest.get("date"),
        "year2": latest.get("year2"),
        "year10": latest.get("year10"),
        "year30": latest.get("year30"),
    }


def _extract_balances(balances: Optional[List[Dict]]) -> tuple[Optional[float], Optional[float]]:
    """Extract buying_power and cash from a single get_balances call."""
    if not balances or not isinstance(balances, list) or len(balances) == 0:
        return None, None
    bal = balances[0]
    buying_power = bal.get("buying_power")
    cash = bal.get("cash")
    return buying_power, cash


def _compute_equity(cash: Optional[float], positions: Optional[List[Dict]]) -> Optional[float]:
    """Compute total equity as cash + sum of position market values."""
    total_mv = sum(float(p.get("market_value") or 0) for p in positions) if positions else 0.0
    return round((cash or 0) + total_mv, 2)


def _compute_day_pnl(
    positions: List[Dict],
    quotes: List[Dict],
) -> Optional[Dict[str, float]]:
    """Compute today's P&L from FMP batch quotes and position units."""
    if not positions or not quotes:
        return None

    change_map = {q["symbol"]: float(q.get("change") or 0) for q in quotes}

    total_daily_change = 0.0
    prev_total_value = 0.0
    for pos in positions:
        # Reason: option positions use underlying_ticker for price lookup
        ticker = (
            pos.get("underlying_ticker") or pos.get("ticker", "")
            if pos.get("position_type") == "option"
            else pos.get("ticker", "")
        )
        units = float(pos.get("units") or 0)
        mv = float(pos.get("market_value") or 0)
        change = change_map.get(ticker, 0.0)

        pos_daily = change * units
        total_daily_change += pos_daily
        prev_total_value += mv - pos_daily

    if prev_total_value == 0:
        return None

    return {
        "dollar": round(total_daily_change, 2),
        "percent": round(total_daily_change / prev_total_value, 6),
    }


async def _get_cached_treasury() -> Optional[Any]:
    """Return cached treasury rates or None."""
    return await cache.get(TREASURY_CACHE_KEY)


async def _get_cached_news() -> Optional[Any]:
    """Return cached general news or None."""
    return await cache.get(NEWS_CACHE_KEY)


# ════════════════════════════════════════════════════════════
# --> Controller
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_dashboard_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Aggregate all dashboard data into a single response."""
    if not clerk_id:
        raise ValueError("clerk_id is required")

    # Reason: skip broker API calls entirely when no broker is connected
    broker_connected = get_connection_status(clerk_id=clerk_id).get("connected", False)

    # Check caches before building Phase 1 task list
    bal_key = BALANCES_CACHE_KEY.format(clerk_id=clerk_id)
    pos_key = POSITIONS_CACHE_KEY.format(clerk_id=clerk_id)
    ord_key = ORDERS_CACHE_KEY.format(clerk_id=clerk_id)
    perf_key = PERFORMANCE_CACHE_KEY.format(clerk_id=clerk_id)

    (
        cached_balances, cached_positions,
        cached_orders, cached_performance,
        cached_treasury, cached_news,
    ) = await asyncio.gather(
        cache.get(bal_key),
        cache.get(pos_key),
        cache.get(ord_key),
        cache.get(perf_key),
        _get_cached_treasury(),
        _get_cached_news(),
    )

    # Phase 1: Independent parallel calls — only fetch on cache miss
    # Reason: task_map tracks which slot index maps to which data key
    tasks = []
    task_map: List[str] = []

    if broker_connected and cached_balances is None:
        task_map.append("balances")
        tasks.append(asyncio.to_thread(get_balances, clerk_id=clerk_id))
    if broker_connected and cached_positions is None:
        task_map.append("positions")
        tasks.append(asyncio.to_thread(get_positions, clerk_id=clerk_id))
    if broker_connected and cached_orders is None:
        task_map.append("orders")
        tasks.append(asyncio.to_thread(get_orders, clerk_id=clerk_id))
    if broker_connected and cached_performance is None:
        task_map.append("performance")
        tasks.append(asyncio.to_thread(get_portfolio_performance, clerk_id=clerk_id))

    task_map.append("indices")
    tasks.append(asyncio.to_thread(fmp.get_batch_quote, ["SPY", "QQQ", "DIA", "IWM", "GLD"]))

    if cached_treasury is None:
        task_map.append("treasury")
        tasks.append(asyncio.to_thread(fmp.get_treasury_rates))
    if cached_news is None:
        task_map.append("news")
        tasks.append(asyncio.to_thread(fmp.get_general_news, 10))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Reason: build a dict from task_map so we can look up results by name
    fresh: Dict[str, Any] = {}
    for i, key in enumerate(task_map):
        fresh[key] = _safe_result(results[i])

    # Resolve broker data from cache or fresh fetch, cache on miss
    balances = cached_balances if cached_balances is not None else fresh.get("balances")
    positions = cached_positions if cached_positions is not None else fresh.get("positions")
    orders = cached_orders if cached_orders is not None else fresh.get("orders")
    performance = cached_performance if cached_performance is not None else fresh.get("performance")
    indices_raw = fresh.get("indices")

    # Cache fresh broker results
    cache_ops = []
    if cached_balances is None and balances is not None:
        cache_ops.append(cache.set(bal_key, balances, BALANCES_CACHE_TTL))
    if cached_positions is None and positions is not None:
        cache_ops.append(cache.set(pos_key, positions, POSITIONS_CACHE_TTL))
    if cached_orders is None and orders is not None:
        cache_ops.append(cache.set(ord_key, orders, ORDERS_CACHE_TTL))
    if cached_performance is None and performance is not None:
        cache_ops.append(cache.set(perf_key, performance, PERFORMANCE_CACHE_TTL))

    buying_power, cash = _extract_balances(balances)

    # Resolve treasury and news from cache or fresh fetch
    if cached_treasury is not None:
        treasury_raw = cached_treasury
    else:
        treasury_raw = fresh.get("treasury")
        if treasury_raw is not None:
            cache_ops.append(cache.set(TREASURY_CACHE_KEY, treasury_raw, TREASURY_CACHE_TTL))

    if cached_news is not None:
        general_news = cached_news
    else:
        general_news = fresh.get("news")
        if general_news is not None:
            cache_ops.append(cache.set(NEWS_CACHE_KEY, general_news, NEWS_CACHE_TTL))

    # Reason: fire all cache.set calls in parallel without blocking
    if cache_ops:
        await asyncio.gather(*cache_ops)

    # Phase 2: Dependent calls (need position tickers)
    ticker_info_map: Dict[str, Dict] = {}
    holdings_news = None
    holdings_quotes: List[Dict] = []

    if positions and isinstance(positions, list) and len(positions) > 0:
        # Reason: use underlying_ticker for options so DB lookup finds the equity metadata
        holding_tickers = list({
            p.get("underlying_ticker") or p.get("ticker", "")
            if p.get("position_type") == "option"
            else p.get("ticker", "")
            for p in positions
            if p.get("ticker") or p.get("underlying_ticker")
        })

        if holding_tickers:
            phase2_results = await asyncio.gather(
                asyncio.to_thread(_fetch_ticker_info_batch, holding_tickers),
                asyncio.to_thread(fmp.get_batch_stock_news, holding_tickers, 20),
                asyncio.to_thread(fmp.get_batch_quote, holding_tickers),
                return_exceptions=True,
            )
            ticker_info_map = _safe_result(phase2_results[0]) or {}
            holdings_news = _safe_result(phase2_results[1])
            holdings_quotes = _safe_result(phase2_results[2]) or []

    # Reason: equity = cash + sum(position market_values), not the balance "amount"
    equity = _compute_equity(cash, positions)

    # Phase 3: Derived computations
    day_pnl = _compute_day_pnl(positions or [], holdings_quotes)

    enriched_positions = (
        _enrich_positions(positions, ticker_info_map)
        if positions and isinstance(positions, list)
        else None
    )

    sector_breakdown = (
        _compute_sector_breakdown(positions, ticker_info_map)
        if positions and isinstance(positions, list)
        else None
    )

    industry_breakdown = (
        _compute_industry_breakdown(positions, ticker_info_map)
        if positions and isinstance(positions, list)
        else None
    )

    treasury_snapshot = _extract_treasury_snapshot(treasury_raw)

    # Build indices list from batch quote
    indices = None
    if indices_raw and isinstance(indices_raw, list):
        indices = [
            {
                "symbol": q.get("symbol"),
                "price": q.get("price"),
                "changesPercentage": q.get("changesPercentage"),
            }
            for q in indices_raw
        ]

    # Assemble payload
    payload = {
        "brokerConnected": broker_connected,
        "account": {
            "equity": equity,
            "buyingPower": buying_power,
            "cash": cash,
            "dayPnl": day_pnl,
        },
        "portfolioPerformance": performance,
        "positions": enriched_positions,
        "sectorBreakdown": sector_breakdown,
        "industryBreakdown": industry_breakdown,
        "marketOverview": {
            "indices": indices,
            "treasuryRates": treasury_snapshot,
        },
        "recentOrders": orders,
        "news": {
            "general": general_news,
            "holdings": holdings_news,
        },
    }

    return ok_envelope(
        kind="dashboard#overview",
        self_link="/api/dashboard",
        message="Dashboard data retrieved successfully",
        payload=payload,
    )
