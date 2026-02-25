"""Sector hierarchy and ticker grouping tools.

Provides tools for exploring the GICS sector structure and retrieving
tickers at different levels of the hierarchy (sector, industry, sub-industry).
"""

from typing import Literal

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker


# ================================
# --> Tools
# ================================

@agent_tool(name="get_sector_industries")
def get_sector_industries(
    sector: Literal[
        "equity_sector_information_technology",
        "equity_sector_consumer_staples",
        "equity_sector_consumer_discretionary",
        "equity_sector_financials",
        "equity_sector_health_care",
        "equity_sector_industrials",
        "equity_sector_materials",
        "equity_sector_energy",
        "equity_sector_utilities",
        "equity_sector_real_estate",
        "equity_sector_communication_services",
    ],
) -> str:
    """
    Retrieve the complete industry hierarchy for a GICS sector.

    Returns a structured tree of industries and their sub-industries within the
    specified sector. Use this to understand sector composition and discover
    available industries/sub-industries for get_group_tickers().

    **Data Returned:**
    - List of industries, each with a sorted list of sub-industries

    **Use Cases:**
    - Explore sector structure and composition
    - Discover industry and sub-industry identifiers for targeted ticker queries
    - Understand the breadth of a sector before drilling down
    - Plan industry or sub-industry level portfolio strategies

    Args:
        sector: GICS sector identifier (e.g., 'equity_sector_consumer_staples')

    Returns:
        Sorted list of industries with their sub-industries

    Examples:
        get_sector_industries(sector='equity_sector_consumer_staples')
        >>> {"success": True, "data": [{"industry": "food_products", "sub_industries": ["packaged_foods", ...]}, ...]}

        get_sector_industries(sector='equity_sector_information_technology')
        >>> {"success": True, "data": [{"industry": "semiconductors_and_semiconductor_equipment", ...}, ...]}
    """
    try:
        with MarketSession() as session:
            rows = (
                session.query(Ticker.industry, Ticker.sub_industry)
                .filter(Ticker.sector == sector, Ticker.is_actively_trading == True)
                .all()
            )

        industry_to_subs: dict[str, set[str]] = {}
        for industry, sub_industry in rows:
            if not industry:
                continue
            if industry not in industry_to_subs:
                industry_to_subs[industry] = set()
            if sub_industry:
                industry_to_subs[industry].add(sub_industry)

        tree = [
            {
                "industry": ind,
                "sub_industries": sorted(list(subs)) if subs else [],
            }
            for ind, subs in sorted(industry_to_subs.items(), key=lambda kv: kv[0])
        ]

        return success_response(tree)
    except Exception as e:
        return error_response(f"Failed to retrieve sector industries: {str(e)}")


@agent_tool(name="get_group_tickers")
def get_group_tickers(
    group: str,
    group_type: Literal["sector", "industry", "sub_industry"] = "sector",
) -> str:
    """
    Retrieve all actively trading tickers within a GICS classification group.

    Returns a list of ticker symbols for all stocks currently actively trading
    in the specified sector, industry, or sub-industry.

    **Use Cases:**
    - Sector level: Build broad sector-focused portfolios
    - Industry level: Analyze industry composition and trends
    - Sub-industry level: Find direct competitors in narrow market segments
    - Screen stocks within any GICS classification level

    Args:
        group: GICS classification identifier in snake_case format.
            For sectors use 'equity_sector_*' format (e.g., 'equity_sector_information_technology').
            For industries and sub-industries use snake_case (e.g., 'semiconductors_and_semiconductor_equipment').
            Use get_sector_industries() to discover available identifiers.
        group_type: Level of the GICS hierarchy to query (default: 'sector')

    Returns:
        List of ticker dicts for all actively trading stocks in the group

    Examples:
        get_group_tickers(group='equity_sector_consumer_staples', group_type='sector')
        >>> {"success": True, "data": [{"ticker": "PG"}, {"ticker": "KO"}, ...]}

        get_group_tickers(group='semiconductors', group_type='sub_industry')
        >>> {"success": True, "data": [{"ticker": "NVDA"}, {"ticker": "AMD"}, ...]}
    """
    try:
        with MarketSession() as session:
            tickers = (
                session.query(Ticker)
                .filter(
                    getattr(Ticker, group_type) == group,
                    Ticker.is_actively_trading == True,
                )
                .all()
            )

        return success_response([{"ticker": t.ticker} for t in tickers])
    except AttributeError:
        return error_response(
            f"Invalid group_type '{group_type}'. Must be 'sector', 'industry', or 'sub_industry'."
        )
    except Exception as e:
        return error_response(f"Failed to retrieve group tickers: {str(e)}")
