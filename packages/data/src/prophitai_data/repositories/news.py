from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import (
    Ticker,
    PressRelease,
    StockNews,
    PriceTargetNews,
    StockGradeNews,
)
from prophitai_data.session import with_session


def _serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    try:
        return dt.isoformat() if dt is not None else None
    except Exception:
        return str(dt) if dt is not None else None


@with_session('market')
def get_press_releases(
    ticker: str,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
    session=None,  # Accept session parameter from decorator
) -> Dict[str, Any]:
    """Fetch press releases for a ticker within an optional date range.

    Returns a dict with 'ticker', 'count', and 'items' (list of dicts).
    """
    # session is injected by decorator
    q = (
        session.query(PressRelease)
        .join(Ticker)
        .filter(Ticker.ticker == ticker.upper())
    )
    if start is not None:
        q = q.filter(PressRelease.publishedDate >= start)
    if end is not None:
        q = q.filter(PressRelease.publishedDate <= end)
    q = q.order_by(PressRelease.publishedDate.asc() if ascending else PressRelease.publishedDate.desc())
    if limit is not None and limit > 0:
        q = q.limit(int(limit))
    rows: List[PressRelease] = q.all()
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append({
            "publishedDate": _serialize_dt(r.publishedDate),
            "publisher": getattr(r, "publisher", None),
            "title": getattr(r, "title", None),
            "site": getattr(r, "site", None),
            "text": getattr(r, "text", None),
            "image": getattr(r, "image", None),
            "url": getattr(r, "url", None),
        })
    return {"ticker": ticker.upper(), "count": len(items), "items": items}


@with_session('market')
def get_stock_news(
    ticker: str,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
    session=None,  # Accept session parameter from decorator
) -> Dict[str, Any]:
    """Fetch general stock news for a ticker within an optional date range."""
    q = (
        session.query(StockNews)
        .join(Ticker)
        .filter(Ticker.ticker == ticker.upper())
    )
    if start is not None:
        q = q.filter(StockNews.publishedDate >= start)
    if end is not None:
        q = q.filter(StockNews.publishedDate <= end)
    q = q.order_by(StockNews.publishedDate.asc() if ascending else StockNews.publishedDate.desc())
    if limit is not None and limit > 0:
        q = q.limit(int(limit))
    rows: List[StockNews] = q.all()
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append({
            "publishedDate": _serialize_dt(r.publishedDate),
            "publisher": getattr(r, "publisher", None),
            "title": getattr(r, "title", None),
            "site": getattr(r, "site", None),
            "text": getattr(r, "text", None),
            "image": getattr(r, "image", None),
            "url": getattr(r, "url", None),
        })
    return {"ticker": ticker.upper(), "count": len(items), "items": items}


@with_session('market')
def get_price_target_news(
    ticker: str,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
    session=None,  # Accept session parameter from decorator
) -> Dict[str, Any]:
    """Fetch price target related news for a ticker within an optional date range."""
    q = (
        session.query(PriceTargetNews)
        .join(Ticker)
        .filter(Ticker.ticker == ticker.upper())
    )
    if start is not None:
        q = q.filter(PriceTargetNews.publishedDate >= start)
    if end is not None:
        q = q.filter(PriceTargetNews.publishedDate <= end)
    q = q.order_by(PriceTargetNews.publishedDate.asc() if ascending else PriceTargetNews.publishedDate.desc())
    if limit is not None and limit > 0:
        q = q.limit(int(limit))
    rows: List[PriceTargetNews] = q.all()
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append({
            "publishedDate": _serialize_dt(r.publishedDate),
            "newsTitle": getattr(r, "newsTitle", None),
            "analystName": getattr(r, "analystName", None),
            "priceTarget": getattr(r, "priceTarget", None),
            "adjPriceTarget": getattr(r, "adjPriceTarget", None),
            "priceWhenPosted": getattr(r, "priceWhenPosted", None),
            "newsPublisher": getattr(r, "newsPublisher", None),
            "analystCompany": getattr(r, "analystCompany", None),
            "url": getattr(r, "newsURL", None),
        })
    return {"ticker": ticker.upper(), "count": len(items), "items": items}


@with_session('market')
def get_stock_grade_news(
    ticker: str,
    *,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None,
    ascending: bool = True,
    session=None,  # Accept session parameter from decorator
) -> Dict[str, Any]:
    """Fetch stock grade/rating news for a ticker within an optional date range."""
    q = (
        session.query(StockGradeNews)
        .join(Ticker)
        .filter(Ticker.ticker == ticker.upper())
    )
    if start is not None:
        q = q.filter(StockGradeNews.publishedDate >= start)
    if end is not None:
        q = q.filter(StockGradeNews.publishedDate <= end)
    q = q.order_by(StockGradeNews.publishedDate.asc() if ascending else StockGradeNews.publishedDate.desc())
    if limit is not None and limit > 0:
        q = q.limit(int(limit))
    rows: List[StockGradeNews] = q.all()
    items: List[Dict[str, Any]] = []
    for r in rows:
        items.append({
            "publishedDate": _serialize_dt(r.publishedDate),
            "newsTitle": getattr(r, "newsTitle", None),
            "gradingCompany": getattr(r, "gradingCompany", None),
            "newGrade": getattr(r, "newGrade", None),
            "previousGrade": getattr(r, "previousGrade", None),
            "action": getattr(r, "action", None),
            "priceWhenPosted": getattr(r, "priceWhenPosted", None),
            "newsPublisher": getattr(r, "newsPublisher", None),
            "url": getattr(r, "newsURL", None),
        })
    return {"ticker": ticker.upper(), "count": len(items), "items": items}
