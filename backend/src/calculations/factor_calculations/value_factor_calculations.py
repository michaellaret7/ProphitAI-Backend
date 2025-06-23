import pandas as pd
import numpy as np
import random
from typing import Optional
from backend.src.data_models.style_factors_models import ValueFactorMetrics

class ValueFactors:
    def __init__(self, most_recent_price: float):
        self.most_recent_price = most_recent_price
    
    def price_to_book(self, book_value_per_share: float) -> Optional[float]:
        """
        Price to book ratio
        """
        if book_value_per_share <= 0:
            return None
        
        return round(self.most_recent_price / book_value_per_share, 4)

    def book_to_market(self, book_value_per_share: float) -> Optional[float]:
        """
        Book to market ratio
        """
        if self.most_recent_price <= 0:
            return None
        
        return round(book_value_per_share / self.most_recent_price, 4)

    def trailing_pe(self, eps_ttm: float) -> Optional[float]:
        """
        Trailing twelve-month price/earnings
        """
        if eps_ttm == 0:
            return None
        return round(self.most_recent_price / eps_ttm, 4)


    def forward_pe(self, eps_forward_next_fy: float) -> Optional[float]:
        """
        Forward price/earnings
        """
        if eps_forward_next_fy == 0:
            return None
        return round(self.most_recent_price / eps_forward_next_fy, 4)
    
    def earnings_yield(self, eps_forward_next_fy: float) -> Optional[float]:
        """
        Earnings yield
        """
        if self.most_recent_price == 0:
            return None
        
        return round(eps_forward_next_fy / self.most_recent_price, 4)
    
    def price_to_sales(self, revenue_ttm: float, shares_outstanding: float) -> Optional[float]:
        """
        Price to sales ratio
        """
        revenue_per_share = revenue_ttm / shares_outstanding

        if revenue_per_share <= 0:
            return None
        
        return round(self.most_recent_price / revenue_per_share, 4)

    def price_to_cashflow(self, operating_cash_flow_ttm: float, shares_outstanding: float) -> Optional[float]:
        """
        Price to cashflow ratio
        """
        ocf_per_share = operating_cash_flow_ttm / shares_outstanding

        if ocf_per_share <= 0:
            return None
        
        return round(self.most_recent_price / ocf_per_share, 4)
    
    def free_cashflow_yield(self, free_cash_flow_ttm: float, shares_outstanding: float) -> Optional[float]:
        """
        Free-Cash-Flow Yield
        """
        market_cap = shares_outstanding * self.most_recent_price

        if market_cap == 0:
            return None
        return round(free_cash_flow_ttm / market_cap, 4)
    
    def ev_to_ebitda(self, shares_outstanding: float, total_debt: float, cash_and_equivalents: float, ebitda_ttm: float) -> Optional[float]:
        """
        Enterprise Value to EBITDA ratio
        """
        market_cap = shares_outstanding * self.most_recent_price
        net_debt = total_debt - cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if ebitda_ttm <= 0:
            return None
        
        return round(enterprise_value / ebitda_ttm, 4)
    
    def ev_to_ebit(self, shares_outstanding: float, total_debt: float, cash_and_equivalents: float, ebit_ttm: float) -> Optional[float]:
        """
        Enterprise Value to EBIT ratio
        """
        market_cap = shares_outstanding * self.most_recent_price
        net_debt = total_debt - cash_and_equivalents
        enterprise_value = market_cap + net_debt

        if ebit_ttm <= 0:
            return None
        
        return round(enterprise_value / ebit_ttm, 4)
    
    def dividend_yield(self, annual_dividend_per_share: float) -> Optional[float]:
        """
        Dividend yield
        """
        if self.most_recent_price == 0:
            return None
        return round(annual_dividend_per_share / self.most_recent_price, 4)
    
    def peg_ratio(self, eps_ttm: float, eps_growth_5yr: float) -> Optional[float]:
        """
        Price/Earnings to Growth ratio
        """
        
        if eps_ttm == 0 or eps_growth_5yr <= 0:
            return None
        
        pe = self.most_recent_price / eps_ttm
        return round(pe / eps_growth_5yr, 4)

    def calc_all(
        self,
        # Basic per-share data
        book_value_per_share: Optional[float] = None,
        eps_ttm: Optional[float] = None,
        eps_forward_next_fy: Optional[float] = None,
        annual_dividend_per_share: Optional[float] = None,
        shares_outstanding: Optional[float] = None,
        
        # Income statement items
        revenue_ttm: Optional[float] = None,
        operating_cash_flow_ttm: Optional[float] = None,
        free_cash_flow_ttm: Optional[float] = None,
        ebitda_ttm: Optional[float] = None,
        ebit_ttm: Optional[float] = None,
        
        # Balance sheet items
        total_debt: Optional[float] = None,
        cash_and_equivalents: Optional[float] = None,
        
        # Growth metrics
        eps_growth_5yr: Optional[float] = None,
    ) -> ValueFactorMetrics:
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
        
        return ValueFactorMetrics(
            price_to_book=self.price_to_book(book_value_per_share) if book_value_per_share is not None else None,
            book_to_market=self.book_to_market(book_value_per_share) if book_value_per_share is not None else None,
            trailing_pe=self.trailing_pe(eps_ttm) if eps_ttm is not None else None,
            forward_pe=self.forward_pe(eps_forward_next_fy) if eps_forward_next_fy is not None else None,
            earnings_yield=self.earnings_yield(eps_forward_next_fy) if eps_forward_next_fy is not None else None,
            price_to_sales=self.price_to_sales(revenue_ttm, shares_outstanding) if revenue_ttm is not None and shares_outstanding is not None else None,
            price_to_cashflow=self.price_to_cashflow(operating_cash_flow_ttm, shares_outstanding) if operating_cash_flow_ttm is not None and shares_outstanding is not None else None,
            free_cashflow_yield=self.free_cashflow_yield(free_cash_flow_ttm, shares_outstanding) if free_cash_flow_ttm is not None and shares_outstanding is not None else None,
            ev_to_ebitda=self.ev_to_ebitda(shares_outstanding, total_debt, cash_and_equivalents, ebitda_ttm) if all(x is not None for x in [shares_outstanding, total_debt, cash_and_equivalents, ebitda_ttm]) else None,
            ev_to_ebit=self.ev_to_ebit(shares_outstanding, total_debt, cash_and_equivalents, ebit_ttm) if all(x is not None for x in [shares_outstanding, total_debt, cash_and_equivalents, ebit_ttm]) else None,
            dividend_yield=self.dividend_yield(annual_dividend_per_share) if annual_dividend_per_share is not None else None,
            peg_ratio=self.peg_ratio(eps_ttm, eps_growth_5yr) if eps_ttm is not None and eps_growth_5yr is not None else None,
        )

if __name__ == "__main__":
    # Initialize with current stock price
    value_calc = ValueFactors(most_recent_price=150.0)

    # Calculate all value metrics at once
    all_metrics = value_calc.calc_all(
        book_value_per_share=25.0,
        eps_ttm=8.50,
        eps_forward_next_fy=9.20,
        shares_outstanding=1_000_000_000,
        revenue_ttm=50_000_000_000,
        operating_cash_flow_ttm=9_200_000_000,  # $9.2B operating cash flow
        free_cash_flow_ttm=8_000_000_000,
        ebitda_ttm=12_000_000_000,
        ebit_ttm=10_500_000_000,  # $10.5B EBIT (EBITDA minus D&A)
        total_debt=5_000_000_000,
        cash_and_equivalents=2_000_000_000,
        annual_dividend_per_share=2.40,
        eps_growth_5yr=15.0
    )


