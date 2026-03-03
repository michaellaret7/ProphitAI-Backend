from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, ETFInfo, ETFHolding
from app.utils.decorators.database import with_session


@with_session('market')
def get_etf_info(tickers: List[str], session=None) -> Dict[str, Dict[str, Any]]:
    """Fetch ETFInfo for one or more tickers.

    Returns:
        Dict keyed by ticker. Missing tickers get {"found": False}.
    """
    upper_tickers = [t.upper() for t in tickers]

    rows: List[ETFInfo] = (
        session.query(ETFInfo)
        .join(Ticker)
        .filter(Ticker.ticker.in_(upper_tickers))
        .all()
    )

    # Reason: build lookup by ticker symbol for O(1) access
    row_map: Dict[str, ETFInfo] = {}
    for row in rows:
        ticker_sym = row.ticker.ticker if row.ticker else None
        if ticker_sym:
            row_map[ticker_sym] = row

    result: Dict[str, Dict[str, Any]] = {}
    for t in upper_tickers:
        row = row_map.get(t)
        if not row:
            result[t] = {"ticker": t, "found": False}
            continue
        result[t] = {
            "ticker": t,
            "found": True,
            "name": getattr(row, "name", None),
            "description": getattr(row, "description", None),
            "isin": getattr(row, "isin", None),
            "assetClass": getattr(row, "assetClass", None),
            "securityCusip": getattr(row, "securityCusip", None),
            "domicile": getattr(row, "domicile", None),
            "website": getattr(row, "website", None),
            "etfCompany": getattr(row, "etfCompany", None),
            "expenseRatio": getattr(row, "expenseRatio", None),
            "aum": getattr(row, "assetsUnderManagement", None),
            "avgVolume": getattr(row, "avgVolume", None),
            "inceptionDate": str(getattr(row, "inceptionDate", None)) if getattr(row, "inceptionDate", None) else None,
            "nav": getattr(row, "nav", None),
            "navCurrency": getattr(row, "navCurrency", None),
            "holdingsCount": getattr(row, "holdingsCount", None),
            "updatedAt": str(getattr(row, "updatedAt", None)) if getattr(row, "updatedAt", None) else None,
            "sectorsList": getattr(row, "sectorsList", None),
        }

    return result


@with_session('market')
def get_etf_holdings(ticker: str, session=None) -> Dict[str, Any]:
    """Fetch ETF holdings for a given ticker."""
    rows: List[ETFHolding] = (
        session.query(ETFHolding)
        .join(Ticker)
        .filter(Ticker.ticker == ticker.upper())
        .all()
    )
    if not rows:
        return {"ticker": ticker.upper(), "count": 0, "items": []}
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append({
            "asset": getattr(r, "asset", None),
            "name": getattr(r, "name", None),
            "isin": getattr(r, "isin", None),
            "securityCusip": getattr(r, "securityCusip", None),
            "sharesNumber": getattr(r, "sharesNumber", None),
            "weightPercentage": getattr(r, "weightPercentage", None),
            "marketValue": getattr(r, "marketValue", None),
            "updatedAt": str(getattr(r, "updatedAt", None)) if getattr(r, "updatedAt", None) else None,
        })
    return {"ticker": ticker.upper(), "count": len(items), "items": items}
