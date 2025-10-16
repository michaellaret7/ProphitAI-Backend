"""Pydantic models and field mappings for stock screener."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.db.core.models.market_data_models import (
    AnalystRecommendation,
    ETFInfo,
    FinancialRatio,
    PriceTargetSummary,
    Rating,
    Ticker,
)

# ============================= Constants ============================= #

# Fuzzy matching threshold for normalization
FUZZY_MATCH_CUTOFF = 0.6

# Warning thresholds for validation
HIGH_ROE_THRESHOLD = 0.15
HIGH_DIVIDEND_YIELD_THRESHOLD = 0.015
ROE_DIVIDEND_CONFLICT_ROE = 0.08

# Large number columns for formatting
LARGE_NUMBER_COLUMNS = [
    "market_cap",
    "assets_under_management",
    "avg_volume",
    "dollar_volume",
    "holdings_count",
    "volume",
]

# ============================= Pydantic Models ============================= #

class ScreenerConstraints(BaseModel):
    """Pydantic model for stock screener constraints parsed from natural language."""

    # Valuation filters
    market_cap_min: Optional[float] = Field(None, description="Minimum market cap in dollars")
    market_cap_max: Optional[float] = Field(None, description="Maximum market cap in dollars")
    avg_volume_min: Optional[float] = Field(None, description="Minimum average volume")
    avg_volume_max: Optional[float] = Field(None, description="Maximum average volume")
    pe_ratio_min: Optional[float] = Field(None, description="Minimum P/E ratio")
    pe_ratio_max: Optional[float] = Field(None, description="Maximum P/E ratio")
    pb_ratio_min: Optional[float] = Field(None, description="Minimum price-to-book ratio")
    pb_ratio_max: Optional[float] = Field(None, description="Maximum price-to-book ratio")
    ps_ratio_min: Optional[float] = Field(None, description="Minimum price-to-sales ratio")
    ps_ratio_max: Optional[float] = Field(None, description="Maximum price-to-sales ratio")
    price_to_cash_flow_min: Optional[float] = Field(None, description="Minimum price-to-cash-flow ratio")
    price_to_cash_flow_max: Optional[float] = Field(None, description="Maximum price-to-cash-flow ratio")
    price_to_fcf_min: Optional[float] = Field(None, description="Minimum price-to-free-cash-flow ratio")
    price_to_fcf_max: Optional[float] = Field(None, description="Maximum price-to-free-cash-flow ratio")
    price_to_ocf_min: Optional[float] = Field(None, description="Minimum price-to-operating-cash-flow ratio")
    price_to_ocf_max: Optional[float] = Field(None, description="Maximum price-to-operating-cash-flow ratio")
    peg_ratio_min: Optional[float] = Field(None, description="Minimum PEG ratio")
    peg_ratio_max: Optional[float] = Field(None, description="Maximum PEG ratio")
    enterprise_value_multiple_min: Optional[float] = Field(None, description="Minimum EV/EBITDA")
    enterprise_value_multiple_max: Optional[float] = Field(None, description="Maximum EV/EBITDA")
    price_fair_value_min: Optional[float] = Field(None, description="Minimum price/fair value")
    price_fair_value_max: Optional[float] = Field(None, description="Maximum price/fair value")
    dividend_yield_min: Optional[float] = Field(None, description="Minimum dividend yield (decimal)")
    dividend_yield_max: Optional[float] = Field(None, description="Maximum dividend yield (decimal)")

    # Profitability filters
    roe_min: Optional[float] = Field(None, description="Minimum return on equity (decimal)")
    roe_max: Optional[float] = Field(None, description="Maximum return on equity (decimal)")
    roa_min: Optional[float] = Field(None, description="Minimum return on assets (decimal)")
    roa_max: Optional[float] = Field(None, description="Maximum return on assets (decimal)")
    roic_min: Optional[float] = Field(None, description="Minimum return on invested capital (decimal)")
    roic_max: Optional[float] = Field(None, description="Maximum return on invested capital (decimal)")
    gross_margin_min: Optional[float] = Field(None, description="Minimum gross margin (decimal)")
    gross_margin_max: Optional[float] = Field(None, description="Maximum gross margin (decimal)")
    operating_margin_min: Optional[float] = Field(None, description="Minimum operating margin (decimal)")
    operating_margin_max: Optional[float] = Field(None, description="Maximum operating margin (decimal)")
    net_margin_min: Optional[float] = Field(None, description="Minimum net margin (decimal)")
    net_margin_max: Optional[float] = Field(None, description="Maximum net margin (decimal)")

    # Financial health filters
    debt_to_equity_min: Optional[float] = Field(None, description="Minimum debt-to-equity ratio")
    debt_to_equity_max: Optional[float] = Field(None, description="Maximum debt-to-equity ratio")
    current_ratio_min: Optional[float] = Field(None, description="Minimum current ratio")
    current_ratio_max: Optional[float] = Field(None, description="Maximum current ratio")
    quick_ratio_min: Optional[float] = Field(None, description="Minimum quick ratio")
    quick_ratio_max: Optional[float] = Field(None, description="Maximum quick ratio")
    interest_coverage_min: Optional[float] = Field(None, description="Minimum interest coverage ratio")
    interest_coverage_max: Optional[float] = Field(None, description="Maximum interest coverage ratio")

    # Efficiency filters
    asset_turnover_min: Optional[float] = Field(None, description="Minimum asset turnover ratio")
    asset_turnover_max: Optional[float] = Field(None, description="Maximum asset turnover ratio")
    inventory_turnover_min: Optional[float] = Field(None, description="Minimum inventory turnover ratio")
    inventory_turnover_max: Optional[float] = Field(None, description="Maximum inventory turnover ratio")

    # ETF-specific filters
    expense_ratio_min: Optional[float] = Field(None, description="Minimum expense ratio (for ETFs)")
    expense_ratio_max: Optional[float] = Field(None, description="Maximum expense ratio (for ETFs)")
    assets_under_management_min: Optional[float] = Field(None, description="Minimum AUM (for ETFs)")
    assets_under_management_max: Optional[float] = Field(None, description="Maximum AUM (for ETFs)")
    holdings_count_min: Optional[float] = Field(None, description="Minimum number of holdings (for ETFs)")
    holdings_count_max: Optional[float] = Field(None, description="Maximum number of holdings (for ETFs)")

    # Rating filters
    overall_score_min: Optional[float] = Field(None, description="Minimum overall rating score")
    overall_score_max: Optional[float] = Field(None, description="Maximum overall rating score")
    analyst_rating_score_min: Optional[float] = Field(None, description="Minimum analyst rating score")
    analyst_rating_score_max: Optional[float] = Field(None, description="Maximum analyst rating score")

    # Price target filters
    price_target_last_month_min: Optional[float] = Field(None, description="Minimum analyst price target (last month)")
    price_target_last_month_max: Optional[float] = Field(None, description="Maximum analyst price target (last month)")
    price_target_last_quarter_min: Optional[float] = Field(None, description="Minimum analyst price target (last quarter)")
    price_target_last_quarter_max: Optional[float] = Field(None, description="Maximum analyst price target (last quarter)")
    price_target_last_year_min: Optional[float] = Field(None, description="Minimum analyst price target (last year)")
    price_target_last_year_max: Optional[float] = Field(None, description="Maximum analyst price target (last year)")

    # Classification filters
    sector: Optional[Union[str, List[str]]] = Field(None, description="Sector or list of sectors to INCLUDE")
    industry: Optional[Union[str, List[str]]] = Field(None, description="Industry or list of industries to INCLUDE")
    sub_industry: Optional[Union[str, List[str]]] = Field(None, description="Sub-industry or list of sub-industries to INCLUDE")
    sector_exclude: Optional[Union[str, List[str]]] = Field(None, description="Sector or list of sectors to EXCLUDE")
    industry_exclude: Optional[Union[str, List[str]]] = Field(None, description="Industry or list of industries to EXCLUDE")
    sub_industry_exclude: Optional[Union[str, List[str]]] = Field(None, description="Sub-industry or list of sub-industries to EXCLUDE")

    # Company profile filters
    beta_min: Optional[float] = Field(None, description="Minimum beta")
    beta_max: Optional[float] = Field(None, description="Maximum beta")
    is_actively_trading: Optional[bool] = Field(None, description="Filter for actively trading stocks")
    is_adr: Optional[bool] = Field(None, description="Filter for ADRs (American Depositary Receipts)")
    is_fund: Optional[bool] = Field(None, description="Filter for funds")
    shares_outstanding_min: Optional[float] = Field(None, description="Minimum shares outstanding")
    shares_outstanding_max: Optional[float] = Field(None, description="Maximum shares outstanding")

    # Display options
    limit: int = Field(100, description="Maximum results to return")
    offset: int = Field(0, description="Results to skip")
    sort_by: Optional[List[str]] = Field(None, description="Fields to sort by (prefix with '-' for desc)")
    columns: Optional[List[str]] = Field(None, description="Specific columns to return")


# ============================= Field Mappings ============================= #

def get_field_synonym_mappings() -> Dict[str, Tuple[Any, str]]:
    """
    Get field synonym mappings for screener.

    Returns mapping of friendly_name -> (model_class, db_field_name).
    """
    return {
        # Ticker fields
        "market_cap": (Ticker, "market_cap"),
        "avg_volume": (Ticker, "avg_volume"),
        "sector": (Ticker, "sector"),
        "industry": (Ticker, "industry"),
        "sub_industry": (Ticker, "sub_industry"),
        "beta": (Ticker, "beta"),
        "is_actively_trading": (Ticker, "is_actively_trading"),
        "is_adr": (Ticker, "is_adr"),
        "is_fund": (Ticker, "is_fund"),
        "ipo_date": (Ticker, "ipo_date"),
        "earnings_announcement": (Ticker, "earnings_announcement"),
        "shares_outstanding": (Ticker, "shares_outstanding"),
        # Financial ratio fields
        "pe_ratio": (FinancialRatio, "priceEarningsRatio"),
        "pb_ratio": (FinancialRatio, "priceToBookRatio"),
        "ps_ratio": (FinancialRatio, "priceToSalesRatio"),
        "price_to_book": (FinancialRatio, "priceToBookRatio"),
        "price_to_sales": (FinancialRatio, "priceToSalesRatio"),
        "price_to_cash_flow": (FinancialRatio, "priceCashFlowRatio"),
        "price_to_fcf": (FinancialRatio, "priceToFreeCashFlowsRatio"),
        "price_to_ocf": (FinancialRatio, "priceToOperatingCashFlowsRatio"),
        "peg_ratio": (FinancialRatio, "priceEarningsToGrowthRatio"),
        "roe": (FinancialRatio, "returnOnEquity"),
        "roa": (FinancialRatio, "returnOnAssets"),
        "roic": (FinancialRatio, "returnOnCapitalEmployed"),
        "debt_to_equity": (FinancialRatio, "debtEquityRatio"),
        "current_ratio": (FinancialRatio, "currentRatio"),
        "quick_ratio": (FinancialRatio, "quickRatio"),
        "gross_margin": (FinancialRatio, "grossProfitMargin"),
        "operating_margin": (FinancialRatio, "operatingProfitMargin"),
        "net_margin": (FinancialRatio, "netProfitMargin"),
        "asset_turnover": (FinancialRatio, "assetTurnover"),
        "inventory_turnover": (FinancialRatio, "inventoryTurnover"),
        "interest_coverage": (FinancialRatio, "interestCoverage"),
        "dividend_yield": (FinancialRatio, "dividendYield"),
        "enterprise_value_multiple": (FinancialRatio, "enterpriseValueMultiple"),
        "price_fair_value": (FinancialRatio, "priceFairValue"),
        # ETF fields
        "expense_ratio": (ETFInfo, "expenseRatio"),
        "assets_under_management": (ETFInfo, "assetsUnderManagement"),
        "holdings_count": (ETFInfo, "holdingsCount"),
        "inception_date": (ETFInfo, "inceptionDate"),
        "nav": (ETFInfo, "nav"),
        # Ratings / analyst
        "rating": (Rating, "rating"),
        "overall_score": (Rating, "overallScore"),
        "analyst_rating": (AnalystRecommendation, "ratingRecommendation"),
        "analyst_rating_score": (AnalystRecommendation, "ratingScore"),
        "price_target_last_month": (PriceTargetSummary, "lastMonthAvgPriceTarget"),
        "price_target_last_quarter": (PriceTargetSummary, "lastQuarterAvgPriceTarget"),
        "price_target_last_year": (PriceTargetSummary, "lastYearAvgPriceTarget"),
    }


# Range filter field mappings for auto-generation
RANGE_FILTER_MAPPINGS = [
    ("market_cap", "market_cap_min", "market_cap_max"),
    ("avg_volume", "avg_volume_min", "avg_volume_max"),
    ("pe_ratio", "pe_ratio_min", "pe_ratio_max"),
    ("pb_ratio", "pb_ratio_min", "pb_ratio_max"),
    ("ps_ratio", "ps_ratio_min", "ps_ratio_max"),
    ("price_to_cash_flow", "price_to_cash_flow_min", "price_to_cash_flow_max"),
    ("price_to_fcf", "price_to_fcf_min", "price_to_fcf_max"),
    ("price_to_ocf", "price_to_ocf_min", "price_to_ocf_max"),
    ("peg_ratio", "peg_ratio_min", "peg_ratio_max"),
    ("enterprise_value_multiple", "enterprise_value_multiple_min", "enterprise_value_multiple_max"),
    ("price_fair_value", "price_fair_value_min", "price_fair_value_max"),
    ("dividend_yield", "dividend_yield_min", "dividend_yield_max"),
    ("roe", "roe_min", "roe_max"),
    ("roa", "roa_min", "roa_max"),
    ("roic", "roic_min", "roic_max"),
    ("gross_margin", "gross_margin_min", "gross_margin_max"),
    ("operating_margin", "operating_margin_min", "operating_margin_max"),
    ("net_margin", "net_margin_min", "net_margin_max"),
    ("debt_to_equity", "debt_to_equity_min", "debt_to_equity_max"),
    ("current_ratio", "current_ratio_min", "current_ratio_max"),
    ("quick_ratio", "quick_ratio_min", "quick_ratio_max"),
    ("interest_coverage", "interest_coverage_min", "interest_coverage_max"),
    ("asset_turnover", "asset_turnover_min", "asset_turnover_max"),
    ("inventory_turnover", "inventory_turnover_min", "inventory_turnover_max"),
    ("expense_ratio", "expense_ratio_min", "expense_ratio_max"),
    ("assets_under_management", "assets_under_management_min", "assets_under_management_max"),
    ("holdings_count", "holdings_count_min", "holdings_count_max"),
    ("overall_score", "overall_score_min", "overall_score_max"),
    ("analyst_rating_score", "analyst_rating_score_min", "analyst_rating_score_max"),
    ("price_target_last_month", "price_target_last_month_min", "price_target_last_month_max"),
    ("price_target_last_quarter", "price_target_last_quarter_min", "price_target_last_quarter_max"),
    ("price_target_last_year", "price_target_last_year_min", "price_target_last_year_max"),
    ("beta", "beta_min", "beta_max"),
    ("shares_outstanding", "shares_outstanding_min", "shares_outstanding_max"),
]