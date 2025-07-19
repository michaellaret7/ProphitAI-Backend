import pandas as pd
import numpy as np
import random
from typing import Optional
from backend.src.data_models.style_factors_models import ValueFactorMetrics
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import *
from sqlalchemy import desc
from backend.src.utils.ticker_utils import get_most_recent_price

class ValueFactors:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.most_recent_price = get_most_recent_price(self.ticker)

        market_session = MarketSession()
        self.cash_flow_statement = market_session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(CashFlowStatement.date)).all()
        self.balance_sheet = market_session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(BalanceSheet.date)).all()
        self.income_statement = market_session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(IncomeStatement.date)).all()
        self.financial_metrics = market_session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(FinancialRatio.date)).all()
        self.estimates = market_session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(desc(AnalystEstimate.date)).all()
        market_session.close()

        # Simple null-safe data access
        # Calculate book value per share
        try:
            self.book_value_per_share = float(self.balance_sheet[0].totalStockholdersEquity) / float(self.income_statement[0].weightedAverageShsOut) if self.balance_sheet and self.income_statement and self.income_statement[0].weightedAverageShsOut != 0 else None
        except (IndexError, TypeError, ZeroDivisionError):
            self.book_value_per_share = None
            
        self.eps_ttm = float(self.income_statement[0].eps) if self.income_statement and self.income_statement[0].eps else None
        self.eps_forward_next_fy = float(self.estimates[0].epsAvg) if self.estimates and self.estimates[0].epsAvg else None
        self.shares_outstanding = float(self.income_statement[0].weightedAverageShsOut) if self.income_statement and self.income_statement[0].weightedAverageShsOut else None
        self.revenue_ttm = float(self.income_statement[0].revenue) if self.income_statement and self.income_statement[0].revenue else None
        self.operating_cash_flow_ttm = float(self.cash_flow_statement[0].netCashProvidedByOperatingActivities) if self.cash_flow_statement and self.cash_flow_statement[0].netCashProvidedByOperatingActivities else None
        self.free_cash_flow_ttm = float(self.cash_flow_statement[0].freeCashFlow) if self.cash_flow_statement and self.cash_flow_statement[0].freeCashFlow else None
        
        # EBITDA is directly available
        self.ebitda_ttm = float(self.income_statement[0].ebitda) if self.income_statement and self.income_statement[0].ebitda else None
            
        self.ebit_ttm = float(self.income_statement[0].operatingIncome) if self.income_statement and self.income_statement[0].operatingIncome else None
        self.total_debt = float(self.balance_sheet[0].totalDebt) if self.balance_sheet and self.balance_sheet[0].totalDebt else None
        self.cash_and_equivalents = float(self.balance_sheet[0].cashAndCashEquivalents) if self.balance_sheet and self.balance_sheet[0].cashAndCashEquivalents else None
        self.dividends = float(self.cash_flow_statement[0].dividendsPaid) if self.cash_flow_statement and self.cash_flow_statement[0].dividendsPaid else None
        
        # Calculate 5-year EPS growth if we have enough historical data
        if len(self.income_statement) >= 20:  # 20 quarters = 5 years
            current_eps = float(self.income_statement[0].eps) if self.income_statement[0].eps else None
            five_year_ago_eps = float(self.income_statement[19].eps) if self.income_statement[19].eps else None
            if current_eps is not None and five_year_ago_eps is not None and five_year_ago_eps != 0:
                ratio = current_eps / five_year_ago_eps
                if ratio > 0:
                    self.eps_growth_5yr = (ratio ** (1/5) - 1) * 100
                else:
                    self.eps_growth_5yr = None
            else:
                self.eps_growth_5yr = None
        else:
            self.eps_growth_5yr = None
    
    def price_to_book(self) -> Optional[float]:
        """
        Price to book ratio
        """
        if self.book_value_per_share is None or self.most_recent_price is None or self.book_value_per_share <= 0:
            return None
        
        return self.most_recent_price / self.book_value_per_share

    def book_to_market(self) -> Optional[float]:
        """
        Book to market ratio
        """
        if self.most_recent_price is None or self.book_value_per_share is None or self.most_recent_price <= 0:
            return None
        
        return self.book_value_per_share / self.most_recent_price

    def trailing_pe(self) -> Optional[float]:
        """
        Trailing twelve-month price/earnings
        """
        if self.eps_ttm is None or self.most_recent_price is None or self.eps_ttm == 0:
            return None
        return self.most_recent_price / self.eps_ttm


    def forward_pe(self) -> Optional[float]:
        """
        Forward price/earnings
        """
        if self.eps_forward_next_fy is None or self.most_recent_price is None or self.eps_forward_next_fy == 0:
            return None
        return self.most_recent_price / self.eps_forward_next_fy
    
    def earnings_yield(self) -> Optional[float]:
        """
        Earnings yield
        """
        if self.most_recent_price is None or self.eps_forward_next_fy is None or self.most_recent_price == 0:
            return None
        
        return self.eps_forward_next_fy / self.most_recent_price
    
    def price_to_sales(self) -> Optional[float]:
        """
        Price to sales ratio
        """
        if self.revenue_ttm is None or self.shares_outstanding is None or self.shares_outstanding == 0 or self.most_recent_price is None:
            return None
        
        revenue_per_share = self.revenue_ttm / self.shares_outstanding

        if revenue_per_share <= 0:
            return None
        
        return self.most_recent_price / revenue_per_share

    def price_to_cashflow(self) -> Optional[float]:
        """
        Price to cashflow ratio
        """
        if self.operating_cash_flow_ttm is None or self.shares_outstanding is None or self.shares_outstanding == 0 or self.most_recent_price is None:
            return None
        
        ocf_per_share = self.operating_cash_flow_ttm / self.shares_outstanding

        if ocf_per_share <= 0:
            return None
        
        return self.most_recent_price / ocf_per_share
    
    def free_cashflow_yield(self) -> Optional[float]:
        """
        Free-Cash-Flow Yield
        """
        if self.shares_outstanding is None or self.most_recent_price is None or self.free_cash_flow_ttm is None:
            return None
            
        market_cap = self.shares_outstanding * self.most_recent_price

        if market_cap == 0:
            return None
        return self.free_cash_flow_ttm / market_cap
    
    def ev_to_ebitda(self) -> Optional[float]:
        """
        Enterprise Value to EBITDA ratio
        """
        if self.shares_outstanding is None or self.most_recent_price is None or self.total_debt is None or self.cash_and_equivalents is None or self.ebitda_ttm is None:
            return None
            
        market_cap = self.shares_outstanding * self.most_recent_price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if self.ebitda_ttm is None or self.ebitda_ttm <= 0:
            return None
        
        return enterprise_value / self.ebitda_ttm
    
    def ev_to_ebit(self) -> Optional[float]:
        """
        Enterprise Value to EBIT ratio
        """
        if self.shares_outstanding is None or self.most_recent_price is None or self.total_debt is None or self.cash_and_equivalents is None or self.ebit_ttm is None:
            return None
            
        market_cap = self.shares_outstanding * self.most_recent_price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if self.ebit_ttm is None or self.ebit_ttm <= 0:
            return None
        
        return enterprise_value / self.ebit_ttm
    
    def dividend_yield(self) -> Optional[float]:
        """
        Dividend yield
        """
        if self.most_recent_price is None or self.dividends is None or self.shares_outstanding is None or self.most_recent_price == 0 or self.shares_outstanding == 0:
            return None
        
        # Dividends are total paid, need to convert to per share
        dividends_per_share = abs(self.dividends) / self.shares_outstanding  # abs() because dividends are negative in cash flow
        return dividends_per_share / self.most_recent_price
    
    def peg_ratio(self) -> Optional[float]:
        """
        Price/Earnings to Growth ratio
        """
        
        if self.most_recent_price is None or self.eps_ttm is None or self.eps_growth_5yr is None or self.eps_ttm == 0 or self.eps_growth_5yr <= 0:
            return None
        
        pe = self.most_recent_price / self.eps_ttm
        return pe / self.eps_growth_5yr

    def calc_all(self) -> ValueFactorMetrics:
        """
        Calculate all value factor metrics at once.
        
        Parameters
        ----------
        All parameters are optional. Pass None or omit parameters for metrics you cannot calculate.
        
        Returns
        -------
        ValueFactorMetrics
            Pydantic model containing all calculated value metrics
        """
        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None"""
            return round(value, decimals) if value is not None else None

        return ValueFactorMetrics(
            price_to_book=safe_round(self.price_to_book()),
            book_to_market=safe_round(self.book_to_market()),
            trailing_pe=safe_round(self.trailing_pe()),
            forward_pe=safe_round(self.forward_pe()),
            earnings_yield=safe_round(self.earnings_yield()),
            price_to_sales=safe_round(self.price_to_sales()),
            price_to_cashflow=safe_round(self.price_to_cashflow()),
            free_cashflow_yield=safe_round(self.free_cashflow_yield()),
            ev_to_ebitda=safe_round(self.ev_to_ebitda()),
            ev_to_ebit=safe_round(self.ev_to_ebit()),
            dividend_yield=safe_round(self.dividend_yield()),
            peg_ratio=safe_round(self.peg_ratio())
        )

if __name__ == "__main__":
    # Initialize with current stock price
    value_calc = ValueFactors(ticker='AAPL')

    # Calculate all value metrics at once
    all_metrics = value_calc.calc_all()
    print(all_metrics)



