from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

import pandas as pd

from backend.src.repositories.price_data import (
    get_price_data_daily,
    fetch_bulk_price_data_for_tickers,
)
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import (
    Dividend,
    Ticker,
    CashFlowStatement,
    BalanceSheet,
    IncomeStatement,
    FinancialRatio,
    AnalystEstimate,
)

from .exceptions import DataFetchError
from .models import PriceData, DividendsData, FundamentalData


class DataService:
    """Single source of truth for calculations data with simple in-memory caching.

    This service reads from existing repository/database utilities. It does not
    perform any heavy transformations; calculators remain responsible for
    computation on top of the returned structures.
    """

    def __init__(self) -> None:
        self._price_cache: Dict[tuple[str, datetime, datetime], pd.DataFrame] = {}
        self._div_cache: Dict[tuple[str, datetime, datetime], pd.Series] = {}
        self._fund_cache: Dict[str, FundamentalData] = {}

    # ----------------------------- Price Data ----------------------------- #
    def get_price_data(self, ticker: str, start_date: datetime, end_date: datetime) -> PriceData:
        key = (ticker.upper(), start_date, end_date)
        if key not in self._price_cache:
            df = get_price_data_daily(ticker, start_date, end_date)
            if df is None or df.empty:
                raise DataFetchError(f"No price data for {ticker} between {start_date} and {end_date}")
            # Ensure datetime index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            self._price_cache[key] = df
        return PriceData(ticker=ticker.upper(), frame=self._price_cache[key])

    def get_bulk_close_series(self, tickers: Iterable[str], start_date: datetime, end_date: datetime) -> Dict[str, pd.Series]:
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        return fetch_bulk_price_data_for_tickers([t.upper() for t in tickers], start_str, end_str, frequency='daily')

    # ---------------------------- Dividends ------------------------------- #
    def get_dividends(self, ticker: str, start_date: datetime, end_date: datetime) -> DividendsData:
        key = (ticker.upper(), start_date, end_date)
        if key not in self._div_cache:
            session = MarketSession()
            try:
                start = start_date.date()
                end = end_date.date()
                divs = (
                    session.query(Dividend)
                    .join(Ticker)
                    .filter(
                        Ticker.ticker == ticker.upper(),
                        Dividend.date >= start,
                        Dividend.date <= end,
                    )
                    .order_by(Dividend.date)
                    .all()
                )
                series = pd.Series(0.0, index=pd.to_datetime([d.date for d in divs]))
                for d in divs:
                    amount = d.adjDividend if d.adjDividend is not None else d.dividend
                    series.loc[pd.to_datetime(d.date)] = float(amount or 0.0)
                self._div_cache[key] = series
            finally:
                session.close()
        return DividendsData(ticker=ticker.upper(), series=self._div_cache[key])

    # -------------------------- Fundamentals ---------------------------- #
    def get_fundamentals(self, ticker: str) -> FundamentalData:
        tkr = ticker.upper()
        if tkr in self._fund_cache:
            return self._fund_cache[tkr]
        session = MarketSession()
        try:
            income = (
                session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == tkr).order_by(IncomeStatement.date.desc()).all()
            )
            balance = (
                session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == tkr).order_by(BalanceSheet.date.desc()).all()
            )
            cashflow = (
                session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == tkr).order_by(CashFlowStatement.date.desc()).all()
            )
            ratios = (
                session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == tkr).order_by(FinancialRatio.date.desc()).all()
            )
            estimates = (
                session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == tkr).order_by(AnalystEstimate.date.desc()).all()
            )
            data = FundamentalData(
                ticker=tkr,
                income_statements=income,
                balance_sheets=balance,
                cash_flow_statements=cashflow,
                financial_ratios=ratios,
                analyst_estimates=estimates,
            )
            self._fund_cache[tkr] = data
            return data
        finally:
            session.close()


