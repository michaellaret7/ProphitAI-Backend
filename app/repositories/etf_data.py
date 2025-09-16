from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker, ETFInfo, ETFHolding


def get_etf_info(ticker: str) -> Dict[str, Any]:
    """Fetch ETFInfo for a given ticker."""
    session = MarketSession()
    try:
        row: Optional[ETFInfo] = (
            session.query(ETFInfo)
            .join(Ticker)
            .filter(Ticker.ticker == ticker.upper())
            .first()
        )
        if not row:
            return {"ticker": ticker.upper(), "found": False}
        return {
            "ticker": ticker.upper(),
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
    finally:
        session.close()


def get_etf_holdings(ticker: str) -> Dict[str, Any]:
    """Fetch ETF holdings for a given ticker."""
    session = MarketSession()
    try:
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
    finally:
        session.close()
