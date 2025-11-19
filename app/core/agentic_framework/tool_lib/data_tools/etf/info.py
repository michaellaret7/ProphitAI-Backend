from typing import Optional
from datetime import datetime
from app.repositories.etf_data import (
    get_etf_info as _get_etf_info
)
from app.utils.decorators.tool_validation import validate_ticker_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.token_count import get_token_count
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

@validate_ticker_arg()
@log_simulation_data_range()
def get_etf_info(ticker: str, _simulation_date: Optional[datetime] = None) -> str:
    """Get comprehensive ETF information including metadata and characteristics.

    Args:
        ticker: ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML string with success status and ETF information including:
        - Basic info: name, description, issuer
        - Characteristics: expense ratio, AUM, inception date
        - Focus: sector focus, asset class, geography
    """
    try:
        data = _get_etf_info(ticker)
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to retrieve ETF info for {ticker}: {str(e)}")

if __name__ == "__main__":
    x = get_etf_info(ticker='QQQ')
    print(x)
    print(get_token_count(x))

# Tool Schema Constants
GET_ETF_INFO_DESCRIPTION = (
    "Retrieve comprehensive ETF information including metadata, characteristics, and focus areas. "
    "Returns detailed information about the ETF's structure, costs, and investment strategy.\n\n"
    "**Data Returned:**\n"
    "  - Basic info: name, description, issuer/provider\n"
    "  - Characteristics: expense ratio, AUM (assets under management), inception date\n"
    "  - Investment focus: sector focus, asset class, geographic region\n"
    "  - Trading info: exchange, currency\n\n"
    "**Use Cases:**\n"
    "  - Compare ETF expense ratios and costs\n"
    "  - Understand ETF investment strategy and focus\n"
    "  - Research ETF providers and fund size\n"
    "  - Validate ETF characteristics before portfolio inclusion\n\n"
    "**Examples:**\n"
    "  get_etf_info(ticker='SPY')  # S&P 500 ETF\n"
    "  get_etf_info(ticker='QQQ')  # Nasdaq-100 ETF\n"
    "  get_etf_info(ticker='VTI')  # Total Stock Market ETF"
)

GET_ETF_INFO_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ETF ticker symbol. For example, 'SPY', 'QQQ', 'VTI', etc.",
        }
    },
    "required": ["ticker"],
}

GET_ETF_INFO_TOOL = {
    "name": "get_etf_info",
    "description": GET_ETF_INFO_DESCRIPTION,
    "parameters": GET_ETF_INFO_PARAMETERS,
    "function": get_etf_info,
}