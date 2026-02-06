"""Base data retrieval functions for fundamentals."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
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
from app.utils.decorators.database import with_session


@with_session('market')
def get_fundamentals_raw(ticker: str, session=None) -> FundamentalsResult:
    """Fetch all fundamental data for a ticker directly from the database.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        session: Database session (injected by decorator)

    Returns:
        FundamentalsResult containing all fundamental data types
    """
    tkr = ticker.upper()

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

    return FundamentalsResult(
        ticker=tkr,
        income_statements=income,
        balance_sheets=balance,
        cash_flow_statements=cashflow,
        financial_ratios=ratios,
        analyst_estimates=estimates,
    )


def get_bulk_fundamentals(
    tickers: Iterable[str], max_workers: int = 16
) -> Dict[str, FundamentalsResult]:
    """Fetch fundamentals for multiple tickers in parallel.

    Args:
        tickers: Iterable of ticker symbols
        max_workers: Maximum number of parallel threads

    Returns:
        Dict mapping ticker to FundamentalsResult for successful fetches
    """
    # Deduplicate and normalize tickers
    unique = []
    seen = set()
    for t in tickers:
        if not t:
            continue
        u = t.upper()
        if u not in seen:
            seen.add(u)
            unique.append(u)

    if not unique:
        return {}

    results: Dict[str, FundamentalsResult] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(get_fundamentals_raw, t): t for t in unique
        }
        for fut in as_completed(future_to_ticker):
            tkr = future_to_ticker[fut]
            try:
                data = fut.result()
                if data is not None:
                    results[tkr] = data
            except Exception:
                # Skip ticker on error
                pass

    return results
