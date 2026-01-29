"""Screening tools for equities and ETFs."""

from .equity_screener import (
    equity_screener,
    EQUITY_SCREENER_TOOL,
)
from .etf_screener import (
    etf_screener,
    ETF_SCREENER_TOOL,
)
from .find_similar_section import (
    find_similar_sections,
    format_invalid_sections_error,
)
from .equity.schema import (
    EQUITY_SCREENER_DESCRIPTION,
    EQUITY_SCREENER_PARAMETERS,
    VALID_SECTORS,
    VALID_INDUSTRIES as EQUITY_VALID_INDUSTRIES,
    VALID_SUB_INDUSTRIES as EQUITY_VALID_SUB_INDUSTRIES,
)
from .etf.schema import (
    ETF_SCREENER_DESCRIPTION,
    ETF_SCREENER_PARAMETERS,
    VALID_INDUSTRIES as ETF_VALID_INDUSTRIES,
    VALID_SUB_INDUSTRIES as ETF_VALID_SUB_INDUSTRIES,
)

__all__ = [
    # Main tools
    "equity_screener",
    "EQUITY_SCREENER_TOOL",
    "etf_screener",
    "ETF_SCREENER_TOOL",
    # Equity schema
    "EQUITY_SCREENER_DESCRIPTION",
    "EQUITY_SCREENER_PARAMETERS",
    "VALID_SECTORS",
    "EQUITY_VALID_INDUSTRIES",
    "EQUITY_VALID_SUB_INDUSTRIES",
    # ETF schema
    "ETF_SCREENER_DESCRIPTION",
    "ETF_SCREENER_PARAMETERS",
    "ETF_VALID_INDUSTRIES",
    "ETF_VALID_SUB_INDUSTRIES",
    # Utilities
    "find_similar_sections",
    "format_invalid_sections_error",
]
