"""Portfolio history tool - historical equity and P&L over time."""

from app.brokers.alpaca.broker import Alpaca
from typing import Optional
from app.core.atlas.tools.responses import success_response, error_response


def portfolio_history(
    period: Optional[str] = None,
    timeframe: Optional[str] = None,
    extended_hours: Optional[bool] = None,
) -> str:
    """Fetch historical portfolio equity and P&L data from Alpaca."""
    alpaca = Alpaca()

    try:
        result = alpaca.get_portfolio_history(
            period=period,
            timeframe=timeframe,
            extended_hours=extended_hours,
        )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to fetch portfolio history: {e}")


# ==============================================================================
# TOOL SCHEMA
# ==============================================================================

PORTFOLIO_HISTORY_DESCRIPTION = (
    "Fetch historical portfolio equity and P&L over time. Returns parallel arrays "
    "of timestamp, equity, profit_loss, and profit_loss_pct.\n"
    "Period options: '1D', '1W', '1M', '3M', '6M', '1A' (1 year), 'all'.\n"
    "Timeframe options: '1Min', '5Min', '15Min', '1H', '1D'.\n"
    "Example: portfolio_history(period='1M', timeframe='1D')\n"
    "Example: portfolio_history(period='1W', timeframe='1H', extended_hours=True)"
)

PORTFOLIO_HISTORY_PARAMETERS = {
    "type": "object",
    "properties": {
        "period": {
            "type": "string",
            "enum": ["1D", "1W", "1M", "3M", "6M", "1A", "all"],
            "description": "Duration of history to retrieve.",
        },
        "timeframe": {
            "type": "string",
            "enum": ["1Min", "5Min", "15Min", "1H", "1D"],
            "description": "Resolution of data points.",
        },
        "extended_hours": {
            "type": "boolean",
            "description": "Include extended hours data. Defaults to false.",
        },
    },
    "required": [],
    "additionalProperties": False,
}

PORTFOLIO_HISTORY_TOOL = {
    "name": "portfolio_history",
    "description": PORTFOLIO_HISTORY_DESCRIPTION,
    "parameters": PORTFOLIO_HISTORY_PARAMETERS,
    "function": portfolio_history,
}
