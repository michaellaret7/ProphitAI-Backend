"""Base data retrieval functions for fundamentals."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, Iterable

from app.db.core.models.market_data_models import (
    Ticker,
    CashFlowStatement,
    BalanceSheet,
    IncomeStatement,
    FinancialRatio,
    AnalystEstimate,
)
from app.repositories.fundamentals.models import FundamentalsResult
from app.utils.cache.data_cache import get_cache
from app.utils.decorators.database import with_session

logger = logging.getLogger(__name__)


@with_session('market')
def get_fundamentals_raw(ticker: str, session=None) -> FundamentalsResult:
    """Fetch all fundamental data for a ticker, checking process-level cache first.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        session: Database session (injected by decorator)

    Returns:
        FundamentalsResult containing all fundamental data types
    """
    tkr = ticker.upper()

    # Reason: check process-level cache before hitting DB
    cache = get_cache()
    cached, missing = cache.get_fundamentals([tkr])
    if not missing:
        return cached[tkr]

    income = (
        session.query(IncomeStatement)
        .join(Ticker)
        .filter(Ticker.ticker == tkr)
        .order_by(IncomeStatement.date.desc())
        .all()
    )
    balance = (
        session.query(BalanceSheet)
        .join(Ticker)
        .filter(Ticker.ticker == tkr)
        .order_by(BalanceSheet.date.desc())
        .all()
    )
    cashflow = (
        session.query(CashFlowStatement)
        .join(Ticker)
        .filter(Ticker.ticker == tkr)
        .order_by(CashFlowStatement.date.desc())
        .all()
    )
    ratios = (
        session.query(FinancialRatio)
        .join(Ticker)
        .filter(Ticker.ticker == tkr)
        .order_by(FinancialRatio.date.desc())
        .all()
    )
    estimates = (
        session.query(AnalystEstimate)
        .join(Ticker)
        .filter(Ticker.ticker == tkr)
        .order_by(AnalystEstimate.date.desc())
        .all()
    )

    result = FundamentalsResult(
        ticker=tkr,
        income_statements=income,
        balance_sheets=balance,
        cash_flow_statements=cashflow,
        financial_ratios=ratios,
        analyst_estimates=estimates,
    )
    cache.put_fundamentals({tkr: result})
    return result


@with_session('market')
def get_bulk_fundamentals(
    tickers: Iterable[str], session=None,
) -> Dict[str, FundamentalsResult]:
    """Fetch fundamentals for multiple tickers in a single session.

    Uses bulk IN-clause queries (6 total: 1 ticker resolve + 5 statement types)
    instead of N individual fetches per ticker. Checks the process-level cache first
    and only fetches missing tickers from the database.

    Args:
        tickers: Iterable of ticker symbols.
        session: Database session (injected by decorator).

    Returns:
        Dict mapping ticker to FundamentalsResult for successful fetches.
    """
    # Deduplicate and normalize tickers
    unique: list[str] = []
    seen: set[str] = set()
    for t in tickers:
        if not t:
            continue
        u = t.upper()
        if u not in seen:
            seen.add(u)
            unique.append(u)

    if not unique:
        return {}

    # Reason: check process-level cache before querying DB
    cache = get_cache()

    cached, missing = cache.get_fundamentals(unique)
    if not missing:
        return cached
    fetched = _fetch_fundamentals_from_db(missing, session)
    cache.put_fundamentals(fetched)
    return {**cached, **fetched}


def _fetch_fundamentals_from_db(
    tickers: list[str], session,
) -> Dict[str, FundamentalsResult]:
    """Fetch fundamentals from the database for the given tickers.

    Args:
        tickers: Pre-deduplicated, uppercased ticker list.
        session: Active DB session.

    Returns:
        Dict mapping ticker -> FundamentalsResult.
    """
    # Reason: resolve all ticker_ids in one query instead of JOINing per statement query
    ticker_rows = (
        session.query(Ticker.id, Ticker.ticker)
        .filter(Ticker.ticker.in_(tickers))
        .all()
    )
    if not ticker_rows:
        return {}

    id_to_ticker = {row.id: row.ticker for row in ticker_rows}
    ids = list(id_to_ticker.keys())

    # Reason: 5 bulk queries (one per statement type) instead of 5N individual queries
    statement_models = [
        ('income', IncomeStatement),
        ('balance', BalanceSheet),
        ('cashflow', CashFlowStatement),
        ('ratios', FinancialRatio),
        ('estimates', AnalystEstimate),
    ]

    grouped: dict[str, dict[str, list]] = {
        key: defaultdict(list) for key, _ in statement_models
    }

    for key, model in statement_models:
        try:
            rows = (
                session.query(model)
                .filter(model.ticker_id.in_(ids))
                .order_by(model.ticker_id, model.date.desc())
                .all()
            )
            for row in rows:
                tkr = id_to_ticker.get(row.ticker_id)
                if tkr:
                    grouped[key][tkr].append(row)
        except Exception as e:
            logger.warning("Failed to fetch %s statements in bulk: %s", key, e)

    results: Dict[str, FundamentalsResult] = {}
    for tkr in tickers:
        if tkr not in id_to_ticker.values():
            continue
        results[tkr] = FundamentalsResult(
            ticker=tkr,
            income_statements=grouped['income'].get(tkr, []),
            balance_sheets=grouped['balance'].get(tkr, []),
            cash_flow_statements=grouped['cashflow'].get(tkr, []),
            financial_ratios=grouped['ratios'].get(tkr, []),
            analyst_estimates=grouped['estimates'].get(tkr, []),
        )

    return results
