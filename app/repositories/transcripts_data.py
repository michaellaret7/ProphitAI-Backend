from __future__ import annotations

from typing import Dict, Any, Optional, List

from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker, EarningsTranscript


def get_earnings_transcripts(
    ticker: str,
    *,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Fetch earnings transcripts for a ticker.

    You can optionally filter by year range and/or limit the number of most recent transcripts.
    If limit is provided, results are returned in reverse chronological order (most recent first).
    """
    session = MarketSession()
    try:
        q = (
            session.query(EarningsTranscript)
            .join(Ticker)
            .filter(Ticker.ticker == ticker.upper())
        )
        if start_year is not None:
            q = q.filter(EarningsTranscript.year >= int(start_year))
        if end_year is not None:
            q = q.filter(EarningsTranscript.year <= int(end_year))
        # If limiting, fetch most recent first
        if limit is not None and int(limit) > 0:
            q = q.order_by(EarningsTranscript.date.desc()).limit(int(limit))
        else:
            q = q.order_by(EarningsTranscript.date.asc())
        rows: List[EarningsTranscript] = q.all()
        items: List[Dict[str, Any]] = []
        for r in rows:
            items.append({
                "period": getattr(r, "period", None),
                "year": getattr(r, "year", None),
                "date": str(getattr(r, "date", None)) if getattr(r, "date", None) else None,
                "content": getattr(r, "content", None),
            })
        return {"ticker": ticker.upper(), "count": len(items), "items": items}
    finally:
        session.close()


def get_latest_transcript(ticker: str) -> Dict[str, Any]:
    session = MarketSession()
    try:
        row: Optional[EarningsTranscript] = (
            session.query(EarningsTranscript)
            .join(Ticker)
            .filter(Ticker.ticker == ticker.upper())
            .order_by(EarningsTranscript.date.desc())
            .first()
        )
        if not row:
            return {"ticker": ticker.upper(), "found": False}
        return {
            "ticker": ticker.upper(),
            "found": True,
            "period": getattr(row, "period", None),
            "year": getattr(row, "year", None),
            "date": str(getattr(row, "date", None)) if getattr(row, "date", None) else None,
            "content": getattr(row, "content", None),
        }
    finally:
        session.close()
