"""Common tool schema definitions to eliminate duplication.

Provides reusable parameter schemas for tool registration.
Follows DRY principle by defining schemas once and importing everywhere.
"""

# Portfolio dict parameter schema (used in 18+ tool instances across tool_lib)
PORTFOLIO_DICT_SCHEMA = {
    "type": "object",
    "description": (
        "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
        "Complete portfolio with ALL holdings. "
        "Keys = ticker symbols (e.g., 'AAPL'). "
        "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
        "You MUST include this parameter with all portfolio tickers."
        "\n\n"
        """Example of CORRECT function call:
        function_name(
            portfolio_dict={
                "AAPL": {"allocation": 0.125, "position": "long"},
                "MSFT": {"allocation": 0.125, "position": "long"},
                "AMZN": {"allocation": 0.125, "position": "long"},
                "TSLA": {"allocation": 0.125, "position": "short"},
                "META": {"allocation": 0.125, "position": "short"},
                "SPY": {"allocation": 0.125, "position": "long"},
                "QQQ": {"allocation": 0.125, "position": "long"},
                "IWM": {"allocation": 0.125, "position": "short"}
            }
        )"""
    ),
    "patternProperties": {
        "^[A-Z]{1,5}$": {
            "type": "object",
            "properties": {
                "allocation": {
                    "type": "number",
                    "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                    "minimum": 0,
                    "maximum": 1
                },
                "position": {
                    "type": "string",
                    "description": "Must be 'long' or 'short'",
                    "enum": ["long", "short"]
                }
            },
            "required": ["allocation", "position"],
            "additionalProperties": False
        }
    },
    "minProperties": 1,
    "additionalProperties": False
}
