"""TTM financial ratios tools.

This module provides tools for fetching trailing twelve months (TTM) financial
ratios for companies, enabling current-state fundamental analysis.
"""

from typing import Optional
from datetime import datetime
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response


@log_simulation_data_range()
def get_ratios_ttm(ticker: str, **kwargs) -> str:
    """Get trailing twelve months (TTM) financial ratios for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        YAML formatted string with TTM financial ratios including:
        - Profitability: ROE, ROA, gross/operating/net profit margins
        - Liquidity: Current ratio, quick ratio, cash ratio
        - Leverage: Debt-to-equity, debt-to-assets, interest coverage
        - Efficiency: Asset turnover, inventory turnover, receivables turnover
        - Valuation: P/E, P/B, P/S, EV/EBITDA, dividend yield
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)

    if not v.is_valid():
        return v.error_response()

    ticker = v.get('ticker')

    fmp = FMP_API_DATA()
    data = fmp.get_ratios_ttm(ticker)

    if data is None or len(data) == 0:
        return error_response(f"No TTM ratios found for {ticker}")

    # Round all numeric values to 4 decimal places
    if isinstance(data, list) and len(data) > 0:
        data[0] = {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in data[0].items()}

    return success_response(data)


# Tool Schema Constants
GET_RATIOS_TTM_DESCRIPTION = (
    "Get trailing twelve months (TTM) financial ratios for a ticker.\n\n"
    "TTM ratios provide a current snapshot of a company's financial health using the most "
    "recent 12 months of data, smoothing out seasonal variations.\n\n"
    "**Ratio Categories:**\n"
    "  - Profitability: ROE, ROA, gross margin, operating margin, net profit margin\n"
    "  - Liquidity: Current ratio, quick ratio, cash ratio\n"
    "  - Leverage: Debt-to-equity, debt-to-assets, interest coverage\n"
    "  - Efficiency: Asset turnover, inventory turnover, receivables turnover\n"
    "  - Valuation: P/E, P/B, P/S, EV/EBITDA, dividend yield\n\n"
    "**Use Cases:**\n"
    "  - Quick financial health assessment\n"
    "  - Peer comparison across key metrics\n"
    "  - Screening for value or quality characteristics\n"
    "  - Identifying red flags (low coverage, high leverage)\n\n"
    "**Example:** get_ratios_ttm(ticker='AAPL')"
)

GET_RATIOS_TTM_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ticker symbol to get TTM ratios for. For example, 'AAPL', 'MSFT', 'KO', etc.",
        },
    },
    "required": ["ticker"],
}

GET_RATIOS_TTM_TOOL = {
    "name": "get_ratios_ttm",
    "description": GET_RATIOS_TTM_DESCRIPTION,
    "parameters": GET_RATIOS_TTM_PARAMETERS,
    "function": get_ratios_ttm,
}

