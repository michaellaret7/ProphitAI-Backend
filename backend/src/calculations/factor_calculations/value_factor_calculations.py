import pandas as pd
import numpy as np
import random
from typing import Optional
from backend.src.data_models.style_factors_models import ValueFactorMetrics
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
from backend.src.utils.ticker_utils import get_most_recent_price

class ValueFactors:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.most_recent_price = get_most_recent_price(self.ticker)

        self.fundamental_repository = FundamentalDataRepository()
        self.cash_flow_statement = self.fundamental_repository.fetch_cash_flow_statement(self.ticker)
        self.balance_sheet = self.fundamental_repository.fetch_balance_sheet(self.ticker)
        self.income_statement = self.fundamental_repository.fetch_income_statement(self.ticker)
        self.financial_metrics = self.fundamental_repository.fetch_financial_metrics(self.ticker)
        self.estimates = self.fundamental_repository.fetch_fundamental_estimates(self.ticker)

        self.book_value_per_share = self.financial_metrics[0]['book_value_per_share']
        self.eps_ttm = self.financial_metrics[0]['earnings_per_share']
        self.eps_forward_next_fy = self.estimates[0]['eps']
        self.shares_outstanding = self.balance_sheet[0]['outstanding_shares']
        self.revenue_ttm = self.income_statement[0]['revenue']
        self.operating_cash_flow_ttm = self.cash_flow_statement[0]['net_cash_flow_from_operations']
        self.free_cash_flow_ttm = self.cash_flow_statement[0]['free_cash_flow']
        self.ebitda_ttm = self.income_statement[0]['operating_income'] + self.cash_flow_statement[0]['depreciation_and_amortization']
        self.ebit_ttm = self.income_statement[0]['ebit']
        self.total_debt = self.balance_sheet[0]['total_debt']
        self.cash_and_equivalents = self.balance_sheet[0]['cash_and_equivalents']
        self.dividends = self.cash_flow_statement[0]['dividends_and_other_cash_distributions']
        self.eps_growth_5yr = self.financial_metrics[0]['earnings_per_share_growth'] 
    
    def price_to_book(self) -> Optional[float]:
        """
        Price to book ratio
        """
        if self.book_value_per_share <= 0:
            return None
        
        return self.most_recent_price / self.book_value_per_share

    def book_to_market(self) -> Optional[float]:
        """
        Book to market ratio
        """
        if self.most_recent_price <= 0:
            return None
        
        return self.book_value_per_share / self.most_recent_price

    def trailing_pe(self) -> Optional[float]:
        """
        Trailing twelve-month price/earnings
        """
        if self.eps_ttm == 0:
            return None
        return self.most_recent_price / self.eps_ttm


    def forward_pe(self) -> Optional[float]:
        """
        Forward price/earnings
        """
        if self.eps_forward_next_fy == 0:
            return None
        return self.most_recent_price / self.eps_forward_next_fy
    
    def earnings_yield(self) -> Optional[float]:
        """
        Earnings yield
        """
        if self.most_recent_price == 0:
            return None
        
        return self.eps_forward_next_fy / self.most_recent_price
    
    def price_to_sales(self) -> Optional[float]:
        """
        Price to sales ratio
        """
        revenue_per_share = self.revenue_ttm / self.shares_outstanding

        if revenue_per_share <= 0:
            return None
        
        return self.most_recent_price / revenue_per_share

    def price_to_cashflow(self) -> Optional[float]:
        """
        Price to cashflow ratio
        """
        ocf_per_share = self.operating_cash_flow_ttm / self.shares_outstanding

        if ocf_per_share <= 0:
            return None
        
        return self.most_recent_price / ocf_per_share
    
    def free_cashflow_yield(self) -> Optional[float]:
        """
        Free-Cash-Flow Yield
        """
        market_cap = self.shares_outstanding * self.most_recent_price

        if market_cap == 0:
            return None
        return self.free_cash_flow_ttm / market_cap
    
    def ev_to_ebitda(self) -> Optional[float]:
        """
        Enterprise Value to EBITDA ratio
        """
        market_cap = self.shares_outstanding * self.most_recent_price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if self.ebitda_ttm <= 0:
            return None
        
        return enterprise_value / self.ebitda_ttm
    
    def ev_to_ebit(self) -> Optional[float]:
        """
        Enterprise Value to EBIT ratio
        """
        market_cap = self.shares_outstanding * self.most_recent_price
        net_debt = self.total_debt - self.cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if self.ebit_ttm <= 0:
            return None
        
        return enterprise_value / self.ebit_ttm
    
    def dividend_yield(self) -> Optional[float]:
        """
        Dividend yield
        """
        if self.most_recent_price == 0:
            return None
        return self.dividends / self.most_recent_price
    
    def peg_ratio(self) -> Optional[float]:
        """
        Price/Earnings to Growth ratio
        """
        
        if self.eps_ttm == 0 or self.eps_growth_5yr <= 0:
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
    value_calc = ValueFactors(most_recent_price=150.0, ticker='AAPL')

    # Calculate all value metrics at once
    all_metrics = value_calc.calc_all()
    print(all_metrics)
    print(value_calc.cash_flow_statement[0])
    print(value_calc.balance_sheet[0])
    print(value_calc.income_statement[0])
    print(value_calc.financial_metrics[0])
    print(value_calc.estimates[0])


