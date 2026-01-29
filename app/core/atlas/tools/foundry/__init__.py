"""
Foundry Tools - RAG and document retrieval tools for agents.

Tools for searching and retrieving information from the Foundry knowledge base:
- Macro research reports (economic outlook, rates, central banks)
- Earnings call transcripts (company guidance, performance, outlook)
"""

from .macro_research import (
    macro_research_search,
    MACRO_RESEARCH_SEARCH_DESCRIPTION,
    MACRO_RESEARCH_SEARCH_PARAMETERS,
    MACRO_RESEARCH_SEARCH_TOOL,
)

from .earnings_calls import (
    earnings_call_search,
    EARNINGS_CALL_SEARCH_DESCRIPTION,
    EARNINGS_CALL_SEARCH_PARAMETERS,
    EARNINGS_CALL_SEARCH_TOOL,
)

__all__ = [
    # Macro Research
    "macro_research_search",
    "MACRO_RESEARCH_SEARCH_DESCRIPTION",
    "MACRO_RESEARCH_SEARCH_PARAMETERS",
    "MACRO_RESEARCH_SEARCH_TOOL",
    # Earnings Calls
    "earnings_call_search",
    "EARNINGS_CALL_SEARCH_DESCRIPTION",
    "EARNINGS_CALL_SEARCH_PARAMETERS",
    "EARNINGS_CALL_SEARCH_TOOL",
]
