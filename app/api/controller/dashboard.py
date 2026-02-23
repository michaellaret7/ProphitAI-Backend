"""Dashboard controller — aggregates all dashboard data in parallel."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.api.response_envelope import ok_envelope
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.redis.client import cache
from app.repositories.user.account import (
    get_account_activities,
    get_buying_power,
    get_cash_balance,
    get_equity,
)
from app.repositories.user.portfolio import get_portfolio_history
from app.repositories.user.trading import get_orders, get_positions
from app.utils.decorators.api_decorators import handle_controller_errors
from app.utils.decorators.database import with_session
from app.utils.serialize_output import serialize_sqlalchemy_obj

logger = logging.getLogger(__name__)

fmp = FMP_API_DATA()

# Cache TTLs (seconds)
TREASURY_CACHE_TTL = 3600   # 1 hour
NEWS_CACHE_TTL = 300         # 5 minutes

# Cache keys
TREASURY_CACHE_KEY = "dashboard:treasury:latest"
NEWS_CACHE_KEY = "dashboard:general_news:latest"


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _safe_result(result: Any) -> Optional[Any]:
    """Return None if the result is an Exception, otherwise return it."""
    if isinstance(result, Exception):
        logger.warning("Dashboard gather task failed: %s", result)
        return None
    return result


def _compute_day_pnl(
    intraday_history: Optional[Dict],
    positions: Optional[List[Dict]],
) -> Optional[Dict[str, float]]:
    """
    Compute day P&L from intraday portfolio history.

    Uses base_value (prior close equity) when available. For new accounts where
    base_value is 0, falls back to summing unrealized P&L from positions — this
    gives real trading P&L without being polluted by same-day deposits.
    """
    if not intraday_history:
        return _pnl_from_positions(positions)

    equity_list = intraday_history.get("equity") or []
    current = equity_list[-1] if equity_list else None
    if current is None:
        return _pnl_from_positions(positions)

    base = intraday_history.get("base_value")
    if not base or base == 0:
        # Reason: base_value is 0 for brand-new accounts (no prior close).
        # Summing unrealized P&L from positions is the most accurate fallback.
        return _pnl_from_positions(positions)

    dollar = current - base
    percent = dollar / base
    return {"dollar": round(dollar, 2), "percent": round(percent, 6)}


def _pnl_from_positions(positions: Optional[List[Dict]]) -> Optional[Dict[str, float]]:
    """Sum unrealized P&L across all positions as a day-P&L fallback."""
    if not positions or not isinstance(positions, list):
        return None

    total_pl = 0.0
    total_cost = 0.0
    for pos in positions:
        pl = float(pos.get("unrealized_pl") or 0)
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
        symbol = pos.get("symbol", "")
        mv = float(pos.get("market_value") or pos.get("marketValue") or 0)
        info = ticker_info_map.get(symbol, {})
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
        symbol = pos.get("symbol", "")
        info = ticker_info_map.get(symbol, {})
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
    cached_treasury = await _get_cached_treasury()
    cached_news = await _get_cached_news()

    # Phase 1: Independent parallel calls
    tasks = [
        asyncio.to_thread(get_equity, clerk_id),                                    # 0
        asyncio.to_thread(get_buying_power, clerk_id),                              # 1
        asyncio.to_thread(get_cash_balance, clerk_id),                              # 2
        asyncio.to_thread(get_portfolio_history, clerk_id, period="1M", timeframe="1D", extended_hours=False),  # 3
        asyncio.to_thread(get_positions, clerk_id),                                 # 4
        asyncio.to_thread(get_orders, clerk_id, "open"),                            # 5
        asyncio.to_thread(get_orders, clerk_id, "closed"),                          # 6
        asyncio.to_thread(get_account_activities, clerk_id),                        # 7
        asyncio.to_thread(fmp.get_batch_quote, ["SPY", "QQQ", "DIA", "IWM"]),      # 8
        asyncio.to_thread(get_portfolio_history, clerk_id, period="1D", timeframe="5Min", extended_hours=False),  # 9
    ]

    # Only fetch treasury/news if not cached
    if cached_treasury is None:
        tasks.append(asyncio.to_thread(fmp.get_treasury_rates))                     # 10
    if cached_news is None:
        tasks.append(asyncio.to_thread(fmp.get_general_news, 10))                   # 11

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unpack Phase 1 results
    equity = _safe_result(results[0])
    buying_power = _safe_result(results[1])
    cash = _safe_result(results[2])
    portfolio_history = _safe_result(results[3])
    positions = _safe_result(results[4])
    open_orders = _safe_result(results[5])
    closed_orders = _safe_result(results[6])
    activities = _safe_result(results[7])
    indices_raw = _safe_result(results[8])
    intraday_history = _safe_result(results[9])

    # Resolve treasury and news from cache or fresh fetch
    # Reason: next_idx tracks the next dynamic slot after the 10 base tasks
    next_idx = 10
    if cached_treasury is not None:
        treasury_raw = cached_treasury
    else:
        treasury_raw = _safe_result(results[next_idx])
        if treasury_raw is not None:
            await cache.set(TREASURY_CACHE_KEY, treasury_raw, TREASURY_CACHE_TTL)
        next_idx += 1

    if cached_news is not None:
        general_news = cached_news
    else:
        general_news = _safe_result(results[next_idx])
        if general_news is not None:
            await cache.set(NEWS_CACHE_KEY, general_news, NEWS_CACHE_TTL)

    # Phase 2: Dependent calls (need position tickers)
    ticker_info_map: Dict[str, Dict] = {}
    holdings_news = None

    if positions and isinstance(positions, list) and len(positions) > 0:
        holding_tickers = [p.get("symbol", "") for p in positions if p.get("symbol")]

        if holding_tickers:
            phase2_results = await asyncio.gather(
                asyncio.to_thread(_fetch_ticker_info_batch, holding_tickers),
                asyncio.to_thread(fmp.get_batch_stock_news, holding_tickers, 20),
                return_exceptions=True,
            )
            ticker_info_map = _safe_result(phase2_results[0]) or {}
            holdings_news = _safe_result(phase2_results[1])

    # Phase 3: Derived computations
    day_pnl = _compute_day_pnl(intraday_history, positions)

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
        "portfolioHistory": portfolio_history,
        "intradayHistory": intraday_history,
        "positions": enriched_positions,
        "sectorBreakdown": sector_breakdown,
        "marketOverview": {
            "indices": indices,
            "treasuryRates": treasury_snapshot,
        },
        "orders": {
            "open": open_orders,
            "closed": closed_orders,
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
