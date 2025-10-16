"""Utility functions for stock screener: normalization, formatting, and prompts."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from difflib import get_close_matches
from typing import Any, List, Optional, Union

import pandas as pd

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

from .models import FUZZY_MATCH_CUTOFF, LARGE_NUMBER_COLUMNS

logger = logging.getLogger(__name__)

# ============================= Database Session Management ============================= #

@contextmanager
def market_session():
    """
    Context manager for MarketSession.

    Ensures proper cleanup of database connections.
    """
    session = MarketSession()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass


# ============================= Field Normalization ============================= #

def normalize_field_names(
    values: Union[str, List[str], None],
    field_name: str,
    model: Any = Ticker,
    cutoff: float = FUZZY_MATCH_CUTOFF
) -> Union[str, List[str], None]:
    """
    Normalize field values by fuzzy matching against database values.

    Uses dynamic database query to get valid field values, then fuzzy matches
    input against them. More robust than static mapping.

    Args:
        values: Single value or list of values to normalize
        field_name: Database field name ('sector', 'industry', 'sub_industry')
        model: SQLAlchemy model containing the field
        cutoff: Fuzzy matching threshold (0.0-1.0)

    Returns:
        Normalized value(s) or original if no close match found
    """
    if values is None:
        return None

    # Get all valid field values from database
    with market_session() as session:
        field = getattr(model, field_name)
        valid_values = [row[0] for row in session.query(field).distinct().all() if row[0]]

    def normalize_single(value: str) -> str:
        """Normalize a single value with fuzzy matching."""
        # First try exact match (case-insensitive)
        value_lower = value.lower()
        for valid in valid_values:
            if valid and valid.lower() == value_lower:
                return valid

        # Try fuzzy matching with cutoff threshold
        matches = get_close_matches(value, valid_values, n=1, cutoff=cutoff)
        if matches:
            normalized = matches[0]
            logger.info(f"[{field_name} normalization] '{value}' -> '{normalized}'")
            return normalized

        # No match found, return original
        logger.warning(f"[{field_name} normalization] '{value}' has no close match in database")
        return value

    # Handle list vs single string
    if isinstance(values, list):
        return [normalize_single(v) for v in values]
    else:
        return normalize_single(values)


def normalize_industry_names(industries: Union[str, List[str], None]) -> Union[str, List[str], None]:
    """
    Normalize industry names by fuzzy matching against database values.

    Args:
        industries: Single industry string or list of industry strings

    Returns:
        Normalized industry name(s) or original if no close match found
    """
    return normalize_field_names(industries, 'industry')


def normalize_sector_names(sectors: Union[str, List[str], None]) -> Union[str, List[str], None]:
    """
    Normalize sector names by fuzzy matching against database values.

    Args:
        sectors: Single sector string or list of sector strings

    Returns:
        Normalized sector name(s) or original if no close match found
    """
    return normalize_field_names(sectors, 'sector')


def normalize_sub_industry_names(sub_industries: Union[str, List[str], None]) -> Union[str, List[str], None]:
    """
    Normalize sub-industry names by fuzzy matching against database values.

    Args:
        sub_industries: Single sub-industry string or list of sub-industry strings

    Returns:
        Normalized sub-industry name(s) or original if no close match found
    """
    return normalize_field_names(sub_industries, 'sub_industry')


# ============================= Result Formatting ============================= #

def format_screener_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format screening results for display.

    Applies comma separators to large number columns for readability.

    Args:
        df: Raw screening results

    Returns:
        Formatted dataframe with readable large numbers
    """
    df_display = df.copy()

    def _format_large_number(x: Any) -> Any:
        """Format large numbers with comma separators."""
        if pd.isna(x):
            return None
        try:
            return f"{int(round(float(x))):,}"
        except Exception:
            return x

    # Format large number columns if present
    for col in LARGE_NUMBER_COLUMNS:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(_format_large_number)

    return df_display


# ============================= System Prompt ============================= #

SCREENER_SYSTEM_PROMPT = """Parse stock screening criteria into structured format.
Convert natural language descriptions into specific numeric constraints.

⚠️ CRITICAL LIMITATIONS - SNAPSHOT DATA ONLY, NO TIME-SERIES ANALYSIS:

❌ UNAVAILABLE - All price-based time-series metrics:
• Alpha, Sharpe ratio, Sortino ratio (risk-adjusted returns)
• Volatility, annualized volatility, standard deviation (price variability)
• Returns over ANY time period (1M, 3M, 6M, 1Y, YTD, annualized)
• Correlation to any index, sector, or stock
• Momentum, relative strength, price trends
• VaR, CVaR, drawdowns, tracking error, information ratio

❌ UNAVAILABLE - All growth/change metrics requiring historical comparison:
• Revenue growth (any period: 1Y, 3Y, 5Y, YoY, QoQ)
• EPS growth, earnings growth, profit growth
• Sales growth, EBITDA growth, FCF growth
• Any metric comparing current vs. historical values
• Trailing growth rates, forward growth rates

✅ AVAILABLE - Current snapshot data only:
• Beta (single point-in-time estimate)
• Current financial ratios (P/E, P/B, ROE, margins, debt ratios, etc.)
• Current market data (market cap, price, volume)
• Static company info (sector, industry, shares outstanding)

If the user requests ANY unavailable metrics:
1. Set them to null/None
2. DO NOT include them in sort_by
3. DO NOT include them in columns
4. DO NOT attempt to approximate them with fundamental metrics
5. IGNORE any growth-related criteria completely

This screener EXCLUSIVELY supports point-in-time fundamental snapshot data.

Example queries:
- "Find large-cap technology stocks with P/E ratio under 20, ROE above 15%, and beta less than 1.2"
- "Show profitable healthcare companies with market cap over $5B, sorted by dividend yield, exclude ADRs"
- "Mid-cap value stocks with low debt-to-equity (under 0.5), high operating margins (over 15%), and actively trading"
- "Growth stocks in consumer staples with ROE > 20%, gross margin > 30%, beta between 0.8 and 1.5, not funds"
- "High dividend defensive stocks: dividend yield above 3%, beta under 1.0, current ratio above 1.5, shares outstanding over 100M"

For percentages, ALWAYS convert to decimals (15% → 0.15, 3% → 0.03).
For dollar amounts, use full numbers (1B → 1000000000, 5M → 5000000).

**CRITICAL - Sector/Industry Naming Conventions:**

• EXACT sector names (use these EXACTLY as written):
  - equity_sector_communication_services
  - equity_sector_consumer_discretionary
  - equity_sector_consumer_staples
  - equity_sector_energy
  - equity_sector_financials
  - equity_sector_health_care (NOT healthcare!)
  - equity_sector_industrials
  - equity_sector_information_technology (NOT just technology!)
  - equity_sector_materials
  - equity_sector_real_estate
  - equity_sector_utilities

• Industry names use underscores and full names (case-sensitive):
  - Banks → "banks" (NOT "banking" or "insurers")
  - Insurance → "insurance" (NOT "insurers" or "insurer")
  - Capital Markets → "capital_markets"
  - Financial Services → "financial_services"
  - Consumer Finance → "consumer_finance"
  - REITs → "diversified_reits", "specialized_reits", "mortgage_reits"
  - Technology → "software", "semiconductors_and_semiconductor_equipment", "it_services"
  - Healthcare → "biotechnology", "pharmaceuticals", "health_care_equipment_and_supplies"
  - Note: The system will attempt fuzzy matching if exact match fails, but prefer exact names

• Sub-industries also use underscores (e.g., "semiconductors", "beverages", "food_products")

• "Defensive" stocks are NOT a sector - use: equity_sector_consumer_staples, equity_sector_utilities, equity_sector_health_care

**CRITICAL - ETF Identification:**
• To find ETFs: set sector = "etf" (NOT is_fund = True!)
• is_fund = True includes MLPs, BDCs, closed-end funds, REITs (NOT traditional ETFs)
• ETF industries: "equity_etfs", "fixed_income_etfs", "commodity_etfs", "alternative_etfs", "cryptocurrency_etfs"
• Example: "Show ETFs" → sector: "etf"

**CRITICAL - Include vs. Exclude:**
• Use "sector", "industry", "sub_industry" fields for stocks TO INCLUDE
• Use "sector_exclude", "industry_exclude", "sub_industry_exclude" for stocks TO EXCLUDE
• When query says "exclude X" or "avoid Y" → use the _exclude fields
• Examples:
  - "Exclude REITs and banks" → industry_exclude: ["diversified_reits", "banks"]
  - "Only tech stocks" → industry: ["software", "semiconductors_and_semiconductor_equipment"]
  - "Show ETFs" → sector: "etf"

Sort descending with "-" prefix (e.g., ["-market_cap"], ["-dividend_yield"]).

Extract ALL relevant criteria from the query, but ONLY use supported fundamental metrics.
"""