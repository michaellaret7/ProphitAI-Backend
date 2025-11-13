"""Agent tool interface for stock screener with parsing and validation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from app.utils.gpt_parser import parse_with_gpt

from .models import (
    HIGH_DIVIDEND_YIELD_THRESHOLD,
    HIGH_ROE_THRESHOLD,
    RANGE_FILTER_MAPPINGS,
    ROE_DIVIDEND_CONFLICT_ROE,
    ScreenerConstraints,
)
from .query_builder import StockScreener
from .utils import (
    SCREENER_SYSTEM_PROMPT,
    normalize_industry_names,
    normalize_sector_names,
)

logger = logging.getLogger(__name__)


# ============================= Parsing ============================= #

def _correct_misplaced_classifications(parsed: ScreenerConstraints, original_text: str) -> ScreenerConstraints:
    """
    Fix common issues where sector tokens are mistakenly parsed into industry/sub_industry
    and infer ETFs from the original text when sector is missing.
    """
    def _is_sector_token(s: str) -> bool:
        return isinstance(s, str) and s.startswith("equity_sector_")

    def _move_tokens(value, dst_attr: str):
        moved = []
        if isinstance(value, str) and _is_sector_token(value):
            moved.append(value)
            value = None
        elif isinstance(value, list):
            keep = []
            for v in value:
                if _is_sector_token(v):
                    moved.append(v)
                else:
                    keep.append(v)
            value = keep or None
        if moved:
            current = getattr(parsed, dst_attr)
            if current is None:
                setattr(parsed, dst_attr, moved[0] if len(moved) == 1 else moved)
            else:
                if isinstance(current, str):
                    cur_list = [current]
                else:
                    cur_list = list(current)
                for v in moved:
                    if v not in cur_list:
                        cur_list.append(v)
                setattr(parsed, dst_attr, cur_list[0] if len(cur_list) == 1 else cur_list)
        return value

    # Move sector identifiers out of industry/sub_industry fields
    parsed.industry = _move_tokens(parsed.industry, "sector")
    parsed.sub_industry = _move_tokens(parsed.sub_industry, "sector")
    parsed.industry_exclude = _move_tokens(parsed.industry_exclude, "sector_exclude")
    parsed.sub_industry_exclude = _move_tokens(parsed.sub_industry_exclude, "sector_exclude")

    # Infer ETF sector from query text when not explicitly parsed
    if isinstance(original_text, str) and "etf" in original_text.lower() and parsed.sector is None:
        parsed.sector = "etf"

    return parsed


def parse_screener_constraints(constraints: str) -> ScreenerConstraints:
    """
    Parse natural language screening criteria into structured constraints.

    Args:
        constraints: Natural language description of screening criteria

    Returns:
        Parsed and normalized ScreenerConstraints object
    """
    # Parse with GPT
    parsed = parse_with_gpt(constraints, ScreenerConstraints, SCREENER_SYSTEM_PROMPT)

    # Correct common misplacements (e.g., sector tokens in industry)
    parsed = _correct_misplaced_classifications(parsed, constraints)

    # Normalize sector and industry names using fuzzy matching
    logger.info("Normalizing sector/industry names...")
    parsed.sector = normalize_sector_names(parsed.sector)
    parsed.sector_exclude = normalize_sector_names(parsed.sector_exclude)
    parsed.industry = normalize_industry_names(parsed.industry)
    parsed.industry_exclude = normalize_industry_names(parsed.industry_exclude)

    return parsed


def build_criteria_dict(parsed: ScreenerConstraints) -> Dict[str, Any]:
    """
    Convert parsed constraints to screener criteria dictionary.

    Uses introspection over RANGE_FILTER_MAPPINGS to avoid repetition.

    Args:
        parsed: Parsed ScreenerConstraints object

    Returns:
        Dictionary of filter criteria for StockScreener
    """
    criteria_dict = {}

    # Reason: Add all range filters using introspection to avoid repetition
    for field_name, min_attr, max_attr in RANGE_FILTER_MAPPINGS:
        min_val = getattr(parsed, min_attr, None)
        max_val = getattr(parsed, max_attr, None)
        if min_val is not None or max_val is not None:
            criteria_dict[field_name] = (min_val, max_val)

    # Add classification filters (include)
    if parsed.sector is not None:
        criteria_dict["sector"] = parsed.sector
    if parsed.industry is not None:
        criteria_dict["industry"] = parsed.industry
    if parsed.sub_industry is not None:
        criteria_dict["sub_industry"] = parsed.sub_industry

    # Add classification filters (exclude)
    if parsed.sector_exclude is not None:
        criteria_dict["sector_exclude"] = parsed.sector_exclude
    if parsed.industry_exclude is not None:
        criteria_dict["industry_exclude"] = parsed.industry_exclude
    if parsed.sub_industry_exclude is not None:
        criteria_dict["sub_industry_exclude"] = parsed.sub_industry_exclude

    # Add company profile filters
    if parsed.is_actively_trading is not None:
        criteria_dict["is_actively_trading"] = parsed.is_actively_trading
    if parsed.is_adr is not None:
        criteria_dict["is_adr"] = parsed.is_adr
    if parsed.is_fund is not None:
        criteria_dict["is_fund"] = parsed.is_fund

    # Add display options
    criteria_dict["limit"] = parsed.limit
    criteria_dict["offset"] = parsed.offset
    if parsed.sort_by is not None:
        criteria_dict["sort_by"] = parsed.sort_by
    if parsed.columns is not None:
        criteria_dict["columns"] = parsed.columns

    return criteria_dict


# ============================= Validation ============================= #

def generate_warnings(
    df: pd.DataFrame,
    parsed: ScreenerConstraints,
    criteria: Dict[str, Any]
) -> List[str]:
    """
    Generate user-facing warnings for potentially problematic filters.

    Args:
        df: Results dataframe
        parsed: Parsed constraints object
        criteria: Criteria dictionary used for screening

    Returns:
        List of warning messages
    """
    warnings = []

    if len(df) == 0:
        warnings.extend(_check_roe_dividend_conflict(parsed))
        warnings.extend(_check_high_roe_threshold(parsed))
        warnings.extend(_check_industry_mismatch(parsed, criteria))

    return warnings


def _check_roe_dividend_conflict(parsed: ScreenerConstraints) -> List[str]:
    """Check for conflicting high ROE + high dividend yield requirements."""
    warnings = []
    roe_min = parsed.roe_min
    div_min = parsed.dividend_yield_min

    if roe_min and roe_min > ROE_DIVIDEND_CONFLICT_ROE and div_min and div_min > HIGH_DIVIDEND_YIELD_THRESHOLD:
        warnings.append(
            f"High ROE (>{roe_min*100:.1f}%) + High Dividend Yield (>{div_min*100:.1f}%) "
            "combination is rare. Consider lowering ROE threshold for dividend-focused stocks."
        )

    return warnings


def _check_high_roe_threshold(parsed: ScreenerConstraints) -> List[str]:
    """Check for unrealistically high ROE thresholds."""
    warnings = []
    roe_min = parsed.roe_min

    if roe_min and roe_min > HIGH_ROE_THRESHOLD:
        warnings.append(
            f"Very high ROE threshold (>{roe_min*100:.1f}%). "
            "Consider lowering to ~5-10% for broader results."
        )

    return warnings


def _check_industry_mismatch(parsed: ScreenerConstraints, criteria: Dict) -> List[str]:
    """Check if industry filter eliminated all results."""
    warnings = []
    industry = parsed.industry

    if industry and isinstance(industry, list) and len(industry) > 0:
        # Reason: Test if removing industry filter yields results
        test_criteria = {k: v for k, v in criteria.items() if k != 'industry'}
        df_test = StockScreener().screen(**test_criteria)

        if len(df_test) > 0:
            warnings.append(
                f"Industry filter {industry} eliminated all results. "
                "Verify industry names match database values (e.g., 'insurance' not 'insurers')."
            )

    return warnings


def _check_etf_metadata_coverage(parsed: ScreenerConstraints, criteria: Dict[str, Any]) -> List[str]:
    """Warn when ETF metadata filters likely exclude due to sparse coverage."""
    warnings: List[str] = []

    def _has(prefix: str) -> bool:
        return any(k == prefix or k.startswith(f"{prefix}_") for k in criteria.keys())

    def _is_etf_sector(sector_val: Any) -> bool:
        if sector_val is None:
            return False
        if isinstance(sector_val, str):
            return sector_val.lower() == "etf"
        if isinstance(sector_val, list):
            return any(isinstance(s, str) and s.lower() == "etf" for s in sector_val)
        return False

    if _is_etf_sector(parsed.sector) and (_has("expense_ratio") or _has("assets_under_management")):
        warnings.append(
            "ETF filters on expense ratio or AUM may exclude funds due to missing metadata. "
            "Try relaxing thresholds or removing one of these filters."
        )

    return warnings


# ============================= Main Tool Interface ============================= #

def screener(constraints: str, *, _simulation_date: Optional[datetime] = None) -> str:
    """
    Screen stocks based on fundamental criteria using natural language.

    Args:
        constraints: Natural language description of screening criteria
            Examples:
            - "Find large-cap tech stocks with PE < 20 and ROE > 15%"
            - "Show profitable food companies with market cap over $5B, sorted by dividend yield"
            - "Mid-cap value stocks with low debt and high margins"
        _simulation_date: INTERNAL USE ONLY - Not currently used. Screener queries
                         most recent fundamental data snapshot only. Historical
                         fundamental data screening not yet supported.

    Returns:
        YAML string with success status and screener results

    Note:
        Simulation mode is not currently supported for the stock screener.
        The tool always returns results based on the most recent fundamental
        data available in the database, regardless of simulation_date.
    """
    try:
        # Parse natural language to structured constraints
        parsed = parse_screener_constraints(constraints)

        # Build criteria dictionary
        criteria = build_criteria_dict(parsed)

        # Log parsed constraints for debugging
        _log_parsed_constraints(constraints, parsed, criteria)

        # Execute screen
        df = StockScreener().screen(**criteria)

        # Generate warnings for edge cases
        warnings = generate_warnings(df, parsed, criteria)

        # Log results summary
        _log_results_summary(df, warnings)

        # Format response
        return _format_success_response(df, warnings)

    except Exception as e:
        logger.exception(f"Stock screening failed for constraints: {constraints}")
        return _format_error_response(e)


# ============================= Logging Helpers ============================= #

def _log_parsed_constraints(constraints: str, parsed: ScreenerConstraints, criteria: Dict):
    """Log parsed constraints for debugging."""
    logger.debug("=" * 80)
    logger.debug("STOCK SCREENER - Parsed Constraints")
    logger.debug("=" * 80)
    logger.debug(f"Original query: {constraints}")
    logger.debug(f"Parsed constraints: {parsed.model_dump(exclude_none=True)}")
    logger.debug(f"Criteria dict: {criteria}")
    logger.debug("=" * 80)


def _log_results_summary(df: pd.DataFrame, warnings: List[str]):
    """Log results summary for debugging."""
    logger.info("=" * 80)
    logger.info("STOCK SCREENER - Results Summary")
    logger.info("=" * 80)
    logger.info(f"Total results found: {len(df)}")
    if len(df) > 0:
        logger.info(f"Columns: {list(df.columns)}")
        logger.debug(f"Sample results:\n{df.head(3)}")
    else:
        logger.warning("No results found - query may be too restrictive or data may be missing")
        if warnings:
            logger.warning(f"Warnings: {warnings}")
    logger.info("=" * 80)


# ============================= Response Formatting ============================= #

def _format_success_response(df: pd.DataFrame, warnings: List[str]) -> str:
    """Format successful screening response as YAML."""
    # Return a failure message if no results were found
    if df is None or len(df) == 0:
        result = {
            "success": False,
            "error": "No results found. Alter your query and try again."
        }
        if warnings:
            result["warnings"] = warnings
        return yaml.dump(result, default_flow_style=False)

    result = {
        "success": True,
        "data": df.to_dict('records'),
        "warnings": warnings if warnings else None
    }
    return yaml.dump(result, default_flow_style=False)


def _format_error_response(error: Exception) -> str:
    """Format error response as YAML."""
    result = {
        "success": False,
        "error": f"Stock screening failed: {str(error)}",
        "error_type": type(error).__name__,
    }
    return yaml.dump(result, default_flow_style=False)


# ============================= Tool Schema ============================= #

STOCK_SCREENER_DESCRIPTION = (
    "⚠️ SNAPSHOT DATA ONLY - NO TIME-SERIES OR GROWTH METRICS ⚠️\n"
    "\nScreen stocks based on CURRENT FUNDAMENTAL DATA using natural language.\n"
    "\n**CRITICAL LIMITATIONS - This tool provides POINT-IN-TIME data only:**"
    "\n\n❌ UNAVAILABLE - No time-series analysis:"
    "\n  • Alpha, Sharpe ratio, Sortino ratio, volatility, standard deviation"
    "\n  • Returns over ANY period (1M, 3M, 6M, 1Y, YTD, annualized)"
    "\n  • Momentum, correlation, price trends, drawdowns"
    "\n  • Revenue growth, EPS growth, earnings growth (any period)"
    "\n  • Sales growth, profit growth, EBITDA growth, FCF growth"
    "\n  • ANY metric requiring historical comparison or growth rates"
    "\n\n✓ AVAILABLE - Current snapshot metrics only:"
    "\n  • Beta (point-in-time estimate)"
    "\n  • Current valuation ratios (P/E, P/B, P/S, PEG, EV/EBITDA, dividend yield)"
    "\n  • Current profitability (ROE, ROA, ROIC, margins)"
    "\n  • Current financial health (debt ratios, liquidity ratios)"
    "\n  • Static attributes (sector, industry, market cap, shares outstanding)"
    "\n\n**Workflow for time-series metrics:**"
    "\n  1. Use stock_screener to filter by current fundamentals (ROE, margins, debt, beta)"
    "\n  2. Get the resulting ticker list"
    "\n  3. THEN use separate tools for growth/returns/volatility analysis on those tickers"
    "\n\n**Supported Criteria (all current values):**"
    "\n  • Valuation: market cap, avg volume, P/E, P/B, P/S, PEG, EV/EBITDA, price/FCF, dividend yield"
    "\n  • Profitability: ROE, ROA, ROIC, gross/operating/net margins"
    "\n  • Financial Health: debt-to-equity, current/quick ratio, interest coverage"
    "\n  • Efficiency: asset turnover, inventory turnover"
    "\n  • Classification: sector, industry, sub_industry"
    "\n  • Company Profile: beta, is_actively_trading, is_adr, shares_outstanding"
    "\n  • ETF Filters: Use sector='etf' to find ETFs (NOT is_fund). ETF-specific: expense ratio, AUM, holdings count"
    "\n  • Ratings: analyst ratings, price targets"
    "\n  • Display: limit, offset, sort_by, columns"
    "\n\n**Examples:**"
    "\n  • stock_screener(constraints='Find large-cap tech stocks with PE ratio under 20 and ROE above 15%')"
    "\n  • stock_screener(constraints='Show profitable food companies with market cap over $5B, sorted by dividend yield')"
    "\n  • stock_screener(constraints='Mid-cap value stocks with low debt and high margins')"
    "\n  • stock_screener(constraints='High dividend stocks in healthcare sector with strong balance sheets')"
    "\n  • stock_screener(constraints='Stocks with ROE > 20%, operating margin > 15%, beta < 1.0, limit 20 results')"
    "\n\n**Tips:**"
    "\n  • Use descriptive terms: 'large-cap' ($10B+), 'mid-cap' ($2-10B), 'small-cap' (<$2B)"
    "\n  • Percentages work: 'ROE > 15%', 'dividend yield above 3%'"
    "\n  • Natural comparisons: 'PE < 20', 'debt-to-equity under 0.5'"
    "\n  • Sorting: 'sorted by market cap', 'order by dividend yield descending'"
    "\n  • Result control: 'show 50 results', 'limit 20'"
    "\n  • DO NOT request growth rates, returns, or any time-series metrics"
)

STOCK_SCREENER_PARAMETERS = {
    "type": "object",
    "properties": {
        "constraints": {
            "type": "string",
            "description": (
                "Natural language description of stock screening criteria using CURRENT SNAPSHOT DATA ONLY. "
                "⚠️ NO TIME-SERIES METRICS: DO NOT include revenue growth, EPS growth, earnings growth, "
                "sales growth, returns (any period), Sharpe ratio, volatility, momentum, correlation, "
                "alpha, or ANY metric requiring historical comparison. "
                "✓ SNAPSHOT METRICS ONLY: Use P/E, P/B, ROE, ROA, ROIC, margins, debt ratios, market cap, "
                "beta, sector, industry, dividend yield, current ratios. "
                "For growth/time-series analysis, first screen by current fundamentals, then analyze tickers separately. "
                "Examples: 'large-cap tech stocks with PE < 20 and ROE > 15%', "
                "'profitable dividend stocks sorted by yield', "
                "'companies with strong current margins and low debt'."
            )
        }
    },
    "required": ["constraints"],
    "additionalProperties": False
}

STOCK_SCREENER_TOOL = {
    "name": "stock_screener",
    "description": STOCK_SCREENER_DESCRIPTION,
    "parameters": STOCK_SCREENER_PARAMETERS,
    "function": screener,
}
