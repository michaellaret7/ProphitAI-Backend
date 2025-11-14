from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
import yaml
from datetime import datetime
from typing import Optional

def get_sector_tickers(sector: str, _simulation_date: Optional[datetime] = None) -> str:
    """Get all actively trading tickers in a sector.

    Args:
        sector: GICS sector identifier
        _simulation_date: Optional datetime for backtesting (currently unused, ticker list is not time-dependent)

    Returns:
        YAML string with success status and ticker list
    """
    with MarketSession() as session:
        sector_info = session.query(Ticker).filter(Ticker.sector == sector, Ticker.is_actively_trading == True).all()

        sector_info = [{'ticker': ticker.ticker} for ticker in sector_info]

        return yaml.dump({"success": True, "data": sector_info}, default_flow_style=False)

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

        return yaml.dump({"success": True, "data": tree}, default_flow_style=False)


# Tool Schema Constants
GET_SECTOR_TICKERS_DESCRIPTION = (
    "Retrieve all actively trading stock tickers within a specified sector. Use this to get a comprehensive list of stocks in a sector for analysis, screening, or portfolio construction.\n\n"
    "Example: get_sector_tickers(sector='equity_sector_consumer_staples')"
)

GET_SECTOR_TICKERS_PARAMETERS = {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": "The sector identifier. Must be one of the valid GICS sector identifiers.",
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

GET_SECTOR_TICKERS_TOOL = {
    "name": "get_sector_tickers",
    "description": GET_SECTOR_TICKERS_DESCRIPTION,
    "parameters": GET_SECTOR_TICKERS_PARAMETERS,
    "function": get_sector_tickers,
}

GET_SECTOR_INDUSTRIES_DESCRIPTION = (
    "Retrieve the complete industry hierarchy for a specified sector, showing all industries and their sub-industries. "
    "Use this to understand sector composition, focus on specific industries within a sector, or build industry-targeted portfolios.\n\n"
    "Example: get_sector_industries(sector='equity_sector_consumer_staples')"
)

GET_SECTOR_INDUSTRIES_PARAMETERS = {
    "type": "object",
    "properties": {
        "sector": {
            "type": "string",
            "description": "The sector identifier. Must be one of the valid GICS sector identifiers.",
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

