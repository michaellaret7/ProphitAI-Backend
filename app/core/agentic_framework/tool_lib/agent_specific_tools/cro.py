import yaml
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.utils import prepare_portfolio_data, get_portfolio_returns, get_benchmark_returns
from app.utils.gpt_parser import canonical_portfolio
from app.models.portfolio_models import PortfolioInput
from app.db.core.db_config import ProphitAltsSession
from app.db.core.models.prophit_alts_models import FundFinalPosition
from app.utils.decorators.database import with_session

@with_session('prophit')
def get_final_portfolio_dict(session=None) -> str:
    """
    Get the initial portfolio dictionary.
    """
    try:
        positions_query = session.query(FundFinalPosition).filter(FundFinalPosition.fund_name == "consumer_staples_fund").all()

        final_positions = {}
        for position in positions_query:
            final_positions[position.ticker_name] = {
                "ticker": position.ticker_name,
                "allocation": position.portfolio_allocation,
                "position": position.position.value,
                "thesis": position.reasoning,
            }

        return yaml.dump({"success": True, "data": final_positions}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)  

# Tool Schema Constants
GET_FINAL_PORTFOLIO_DICT_DESCRIPTION = (
    "Get the Consumer Staples Fund's final portfolio dictionary from the database with tickers and their allocation levels. "
    "Returns dictionary format with ticker symbols as keys and objects containing 'allocation' (decimal allocation) and 'position' ('long'/'short') as values. "
    "NO PARAMETERS REQUIRED: This tool takes no arguments and should be called with empty parameters '{}'. "
    "WHEN TO USE: (1) ALWAYS START HERE - get the final portfolio before any analysis, (2) Portfolio construction - use as template for modifications, (3) Allocation reference - understand CIO's allocation levels, (4) Comparison base - measure changes against original structure."
)

GET_FINAL_PORTFOLIO_DICT_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False
}

GET_FINAL_PORTFOLIO_DICT_TOOL = {
    "name": "get_final_portfolio_dict",
    "description": GET_FINAL_PORTFOLIO_DICT_DESCRIPTION,
    "parameters": GET_FINAL_PORTFOLIO_DICT_PARAMETERS,
    "function": get_final_portfolio_dict,
}
