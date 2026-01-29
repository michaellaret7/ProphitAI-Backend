"""Sector hierarchy and ticker grouping tools.

This module provides tools for exploring the GICS sector structure and retrieving
tickers at different levels of the hierarchy (sector, industry, sub-industry).
"""

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.core.atlas.tools.responses import success_response
from datetime import datetime
from typing import Optional

def get_group_tickers(group: str, group_type: str = 'sector', _simulation_date: Optional[datetime] = None) -> str:
    """Get all actively trading tickers in a group.

    Args:
        group: Group identifier
        group_type: Type of group (sector, industry, sub_industry)
        _simulation_date: Optional datetime for backtesting (currently unused, ticker list is not time-dependent)

    Returns:
        YAML string with success status and ticker list
    """
    with MarketSession() as session:
        group_info = session.query(Ticker).filter(getattr(Ticker, group_type) == group, Ticker.is_actively_trading == True).all()

        group_info = [{'ticker': ticker.ticker} for ticker in group_info]

        return success_response(group_info)

def get_sector_industries(sector: str, _simulation_date: Optional[datetime] = None) -> str:
    """Get the industry hierarchy for a sector.

    Args:
        sector: GICS sector identifier
        _simulation_date: Optional datetime for backtesting (currently unused, industry structure is not time-dependent)

    Returns:
        YAML string with success status and industry tree
    """
    with MarketSession() as session:
        rows = (
            session.query(Ticker.industry, Ticker.sub_industry)
            .filter(Ticker.sector == sector, Ticker.is_actively_trading == True)
            .all()
        )

        industry_to_subs = {}
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
                "sub_industries": sorted(list(subs)) if subs else []
            }
            for ind, subs in sorted(industry_to_subs.items(), key=lambda kv: kv[0])
        ]

        return success_response(tree)

if __name__ == "__main__":
    print(get_sector_industries("equity_sector_consumer_staples"))

# Tool Schema Constants
GET_GROUP_TICKERS_DESCRIPTION = (
    "Retrieve all actively trading stock tickers within a specified GICS classification group (sector, industry, or sub-industry). "
    "Returns a list of ticker symbols for all stocks that are currently actively trading in the specified group. "
    "Use this flexible function to get tickers at any level of the GICS hierarchy.\n\n"
    "**Use Cases:**\n"
    "  - Sector level: Build broad sector-focused portfolios\n"
    "  - Industry level: Analyze industry composition and trends\n"
    "  - Sub-industry level: Find direct competitors in narrow market segments\n"
    "  - Screen stocks within any GICS classification level\n\n"
    "**Examples:**\n"
    "  - get_group_tickers(group='equity_sector_consumer_staples', group_type='sector')\n"
    "  - get_group_tickers(group='semiconductors_and_semiconductor_equipment', group_type='industry')\n"
    "  - get_group_tickers(group='semiconductors', group_type='sub_industry')"
)

GET_GROUP_TICKERS_PARAMETERS = {
    "type": "object",
    "properties": {
        "group": {
            "type": "string",
            "description": (
                "The GICS classification identifier in snake_case format. "
                "For sectors, use 'equity_sector_*' format (e.g., 'equity_sector_information_technology'). "
                "For industries and sub-industries, use snake_case format (e.g., 'semiconductors_and_semiconductor_equipment'). "
                "Use get_sector_industries() to discover available industries and sub-industries."
            )
        },
        "group_type": {
            "type": "string",
            "description": "The type of GICS classification: 'sector', 'industry', or 'sub_industry'.",
            "enum": ["sector", "industry", "sub_industry"],
            "default": "sector"
        }
    },
    "required": ["group"],
}

GET_GROUP_TICKERS_TOOL = {
    "name": "get_group_tickers",
    "description": GET_GROUP_TICKERS_DESCRIPTION,
    "parameters": GET_GROUP_TICKERS_PARAMETERS,
    "function": get_group_tickers,
}

GET_SECTOR_INDUSTRIES_DESCRIPTION = (
    "Retrieve the complete industry hierarchy for a specified sector, showing all industries and their sub-industries. "
    "Returns a structured tree of industries and sub-industries within the sector. "
    "Use this to understand sector composition and discover available industries/sub-industries for get_group_tickers().\n\n"
    "**Use Cases:**\n"
    "  - Explore sector structure and composition\n"
    "  - Discover industry and sub-industry identifiers for targeted ticker queries\n"
    "  - Understand the breadth of a sector\n"
    "  - Plan industry or sub-industry level strategies\n\n"
    "**Example:** get_sector_industries(sector='equity_sector_consumer_staples')"
)

GET_SECTOR_INDUSTRIES_PARAMETERS = {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": "The GICS sector identifier. Must be one of the 11 valid sector identifiers.",
            "enum": [
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
                "equity_sector_communication_services"
            ]
        }
    },
    "required": ["sector"],
}

GET_SECTOR_INDUSTRIES_TOOL = {
    "name": "get_sector_industries",
    "description": GET_SECTOR_INDUSTRIES_DESCRIPTION,
    "parameters": GET_SECTOR_INDUSTRIES_PARAMETERS,
    "function": get_sector_industries,
}
