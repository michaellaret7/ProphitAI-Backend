from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import (
    Ticker,
    StockGradesIndividual,
    StockGradesSummary,
    Rating,
    AnalystRecommendation,
    PriceTargetSummary,
)


def _serialize_date(d) -> Optional[str]:
    try:
        return d.isoformat() if d is not None else None
    except Exception:
        return str(d) if d is not None else None


def get_stock_grades_individual(ticker: str, *, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Dict[str, Any]:
    session = MarketSession()
    try:
        q = session.query(StockGradesIndividual).join(Ticker).filter(Ticker.ticker == ticker.upper())
        if start is not None:
            q = q.filter(StockGradesIndividual.date >= start)
        if end is not None:
            q = q.filter(StockGradesIndividual.date <= end)
        q = q.order_by(StockGradesIndividual.date.asc())
        rows: List[StockGradesIndividual] = q.all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append({
                "date": _serialize_date(r.date),
                "gradingCompany": getattr(r, "gradingCompany", None),
                "previousGrade": getattr(r, "previousGrade", None),
                "newGrade": getattr(r, "newGrade", None),
                "action": getattr(r, "action", None),
            })
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    finally:
        session.close()


def get_stock_grades_summary(ticker: str, *, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Dict[str, Any]:
    session = MarketSession()
    try:
        q = session.query(StockGradesSummary).join(Ticker).filter(Ticker.ticker == ticker.upper())
        if start is not None:
            q = q.filter(StockGradesSummary.date >= start)
        if end is not None:
            q = q.filter(StockGradesSummary.date <= end)
        q = q.order_by(StockGradesSummary.date.asc())
        rows: List[StockGradesSummary] = q.all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append({
                "date": _serialize_date(r.date),
                "strong_buy": getattr(r, "analystRatingsStrongBuy", None),
                "buy": getattr(r, "analystRatingsBuy", None),
                "hold": getattr(r, "analystRatingsHold", None),
                "sell": getattr(r, "analystRatingsSell", None),
                "strong_sell": getattr(r, "analystRatingsStrongSell", None),
            })
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    finally:
        session.close()


def get_ratings(ticker: str, *, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Dict[str, Any]:
    session = MarketSession()
    try:
        q = session.query(Rating).join(Ticker).filter(Ticker.ticker == ticker.upper())
        if start is not None:
            q = q.filter(Rating.date >= start)
        if end is not None:
            q = q.filter(Rating.date <= end)
        q = q.order_by(Rating.date.asc())
        rows: List[Rating] = q.all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append({
                "date": _serialize_date(r.date),
                "rating": getattr(r, "rating", None),
                "overallScore": getattr(r, "overallScore", None),
                "dcf": getattr(r, "discountedCashFlowScore", None),
                "roe": getattr(r, "returnOnEquityScore", None),
                "roa": getattr(r, "returnOnAssetsScore", None),
                "de": getattr(r, "debtToEquityScore", None),
                "pe": getattr(r, "priceToEarningsScore", None),
                "pb": getattr(r, "priceToBookScore", None),
            })
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    finally:
        session.close()


def get_analyst_recommendations(ticker: str, *, start: Optional[datetime] = None, end: Optional[datetime] = None) -> Dict[str, Any]:
    session = MarketSession()
    try:
        q = session.query(AnalystRecommendation).join(Ticker).filter(Ticker.ticker == ticker.upper())
        if start is not None:
            q = q.filter(AnalystRecommendation.date >= start)
        if end is not None:
            q = q.filter(AnalystRecommendation.date <= end)
        q = q.order_by(AnalystRecommendation.date.asc())
        rows: List[AnalystRecommendation] = q.all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append({
                "date": _serialize_date(r.date),
                "rating": getattr(r, "rating", None),
                "ratingScore": getattr(r, "ratingScore", None),
                "ratingRecommendation": getattr(r, "ratingRecommendation", None),
            })
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    finally:
        session.close()


def get_price_target_summary(ticker: str) -> Dict[str, Any]:
    session = MarketSession()
    try:
        row: Optional[PriceTargetSummary] = (
            session.query(PriceTargetSummary)
            .join(Ticker)
            .filter(Ticker.ticker == ticker.upper())
            .first()
        )
        if not row:
            return {"ticker": ticker.upper(), "found": False}
        return {
            "ticker": ticker.upper(),
            "found": True,
            "lastMonthCount": getattr(row, "lastMonthCount", None),
            "lastMonthAvgPriceTarget": getattr(row, "lastMonthAvgPriceTarget", None),
            "lastQuarterCount": getattr(row, "lastQuarterCount", None),
            "lastQuarterAvgPriceTarget": getattr(row, "lastQuarterAvgPriceTarget", None),
            "lastYearCount": getattr(row, "lastYearCount", None),
            "lastYearAvgPriceTarget": getattr(row, "lastYearAvgPriceTarget", None),
            "allTimeCount": getattr(row, "allTimeCount", None),
            "allTimeAvgPriceTarget": getattr(row, "allTimeAvgPriceTarget", None),
            "publishers": getattr(row, "publishers", None),
        }
    finally:
        session.close()
