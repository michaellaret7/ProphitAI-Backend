"""Dashboard controller — aggregates all dashboard data in parallel."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.api.response_envelope import ok_envelope
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.redis.client import cache
from app.repositories.user.account import get_account_activities, get_balances
from app.repositories.user.trading import get_positions
from app.utils.decorators.api_decorators import handle_controller_errors
from app.utils.decorators.database import with_session
from app.utils.serialize_output import serialize_sqlalchemy_obj

logger = logging.getLogger(__name__)

fmp = FMP_API_DATA()

# Cache TTLs (seconds)
TREASURY_CACHE_TTL = 3600   # 1 hour
NEWS_CACHE_TTL = 300         # 5 minutes
BALANCES_CACHE_TTL = 30      # 30 seconds
POSITIONS_CACHE_TTL = 30     # 30 seconds
ACTIVITIES_CACHE_TTL = 60    # 1 minute

# Cache keys
TREASURY_CACHE_KEY = "dashboard:treasury:latest"
NEWS_CACHE_KEY = "dashboard:general_news:latest"
BALANCES_CACHE_KEY = "dashboard:{clerk_id}:balances"
POSITIONS_CACHE_KEY = "dashboard:{clerk_id}:positions"
ACTIVITIES_CACHE_KEY = "dashboard:{clerk_id}:activities"


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _safe_result(result: Any) -> Optional[Any]:
    """Return None if the result is an Exception, otherwise return it."""
    if isinstance(result, Exception):
        logger.warning("Dashboard gather task failed: %s", result)
        return None
    return result


def _pnl_from_positions(positions: Optional[List[Dict]]) -> Optional[Dict[str, float]]:
    """Sum open P&L across all positions as day-P&L."""
    if not positions or not isinstance(positions, list):
        return None

    total_pl = 0.0
    total_cost = 0.0
    for pos in positions:
        pl = float(pos.get("open_pnl") or 0)
        mv = float(pos.get("market_value") or 0)
        total_pl += pl
        total_cost += mv - pl

    if total_cost == 0:
        return None

    return {"dollar": round(total_pl, 2), "percent": round(total_pl / total_cost, 6)}


def _compute_sector_breakdown(
    positions: List[Dict],
    ticker_info_map: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """Group positions by sector, compute weight percentages."""
    sector_mv: Dict[str, float] = {}
    total_mv = 0.0

    for pos in positions:
        ticker = pos.get("ticker", "")
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
        ticker = pos.get("ticker", "")
        info = ticker_info_map.get(ticker, {})
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


def _extract_balances(balances: Optional[List[Dict]]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """Extract equity, buying_power, cash from a single get_balances call."""
    if not balances or not isinstance(balances, list) or len(balances) == 0:
        return None, None, None
    bal = balances[0]
    equity = bal.get("amount") or bal.get("cash")
    buying_power = bal.get("buying_power")
    cash = bal.get("cash")
    return equity, buying_power, cash


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

    # Check caches before building Phase 1 task list
    bal_key = BALANCES_CACHE_KEY.format(clerk_id=clerk_id)
    pos_key = POSITIONS_CACHE_KEY.format(clerk_id=clerk_id)
    act_key = ACTIVITIES_CACHE_KEY.format(clerk_id=clerk_id)

    cached_balances, cached_positions, cached_activities, cached_treasury, cached_news = (
        await asyncio.gather(
            cache.get(bal_key),
            cache.get(pos_key),
            cache.get(act_key),
            _get_cached_treasury(),
            _get_cached_news(),
        )
    )

    # Phase 1: Independent parallel calls — only fetch on cache miss
    # Reason: task_map tracks which slot index maps to which data key
    tasks = []
    task_map: List[str] = []

    if cached_balances is None:
        task_map.append("balances")
        tasks.append(asyncio.to_thread(get_balances, clerk_id=clerk_id))
    if cached_positions is None:
        task_map.append("positions")
        tasks.append(asyncio.to_thread(get_positions, clerk_id=clerk_id))
    if cached_activities is None:
        task_map.append("activities")
        tasks.append(asyncio.to_thread(get_account_activities, clerk_id=clerk_id))

    task_map.append("indices")
    tasks.append(asyncio.to_thread(fmp.get_batch_quote, ["SPY", "QQQ", "DIA", "IWM"]))

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
    activities = cached_activities if cached_activities is not None else fresh.get("activities")
    indices_raw = fresh.get("indices")

    # Cache fresh broker results
    cache_ops = []
    if cached_balances is None and balances is not None:
        cache_ops.append(cache.set(bal_key, balances, BALANCES_CACHE_TTL))
    if cached_positions is None and positions is not None:
        cache_ops.append(cache.set(pos_key, positions, POSITIONS_CACHE_TTL))
    if cached_activities is None and activities is not None:
        cache_ops.append(cache.set(act_key, activities, ACTIVITIES_CACHE_TTL))

    equity, buying_power, cash = _extract_balances(balances)

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

    if positions and isinstance(positions, list) and len(positions) > 0:
        holding_tickers = [p.get("ticker", "") for p in positions if p.get("ticker")]

        if holding_tickers:
            phase2_results = await asyncio.gather(
                asyncio.to_thread(_fetch_ticker_info_batch, holding_tickers),
                asyncio.to_thread(fmp.get_batch_stock_news, holding_tickers, 20),
                return_exceptions=True,
            )
            ticker_info_map = _safe_result(phase2_results[0]) or {}
            holdings_news = _safe_result(phase2_results[1])

    # Phase 3: Derived computations
    day_pnl = _pnl_from_positions(positions)

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
        "account": {
            "equity": equity,
            "buyingPower": buying_power,
            "cash": cash,
            "dayPnl": day_pnl,
        },
        "portfolioPerformance": None,
        "positions": enriched_positions,
        "sectorBreakdown": sector_breakdown,
        "marketOverview": {
            "indices": indices,
            "treasuryRates": treasury_snapshot,
        },
        "recentActivity": activities,
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
