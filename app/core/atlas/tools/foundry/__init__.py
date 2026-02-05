"""
Foundry Tools - RAG and document retrieval tools for agents.

Tools for searching and retrieving information from the Foundry knowledge base:
- Macro research reports (economic outlook, rates, central banks)
- Credit research reports (bonds, spreads, high yield, leveraged loans)
- Earnings call transcripts (company guidance, performance, outlook)
- User uploaded documents (user-specific document search)
- Tax documents (IRS forms, instructions, publications)
"""

from .macro_research import (
    macro_research_search,
    MACRO_RESEARCH_SEARCH_DESCRIPTION,
    MACRO_RESEARCH_SEARCH_PARAMETERS,
    MACRO_RESEARCH_SEARCH_TOOL,
)

from .credit_research import (
    credit_research_search,
    CREDIT_RESEARCH_SEARCH_DESCRIPTION,
    CREDIT_RESEARCH_SEARCH_PARAMETERS,
    CREDIT_RESEARCH_SEARCH_TOOL,
)

from .earnings_calls import (
    earnings_call_search,
    EARNINGS_CALL_SEARCH_DESCRIPTION,
    EARNINGS_CALL_SEARCH_PARAMETERS,
    EARNINGS_CALL_SEARCH_TOOL,
)

from .user_uploads import (
    user_upload_search,
    USER_UPLOAD_SEARCH_DESCRIPTION,
    USER_UPLOAD_SEARCH_PARAMETERS,
    USER_UPLOAD_SEARCH_TOOL,
)

from .tax_research import (
    tax_research_search,
    TAX_RESEARCH_SEARCH_DESCRIPTION,
    TAX_RESEARCH_SEARCH_PARAMETERS,
    TAX_RESEARCH_SEARCH_TOOL,
)

__all__ = [
    # Macro Research
    "macro_research_search",
    "MACRO_RESEARCH_SEARCH_DESCRIPTION",
    "MACRO_RESEARCH_SEARCH_PARAMETERS",
    "MACRO_RESEARCH_SEARCH_TOOL",
    # Credit Research
    "credit_research_search",
    "CREDIT_RESEARCH_SEARCH_DESCRIPTION",
    "CREDIT_RESEARCH_SEARCH_PARAMETERS",
    "CREDIT_RESEARCH_SEARCH_TOOL",
    # Earnings Calls
    "earnings_call_search",
    "EARNINGS_CALL_SEARCH_DESCRIPTION",
    "EARNINGS_CALL_SEARCH_PARAMETERS",
    "EARNINGS_CALL_SEARCH_TOOL",
    # User Uploads
    "user_upload_search",
    "USER_UPLOAD_SEARCH_DESCRIPTION",
    "USER_UPLOAD_SEARCH_PARAMETERS",
    "USER_UPLOAD_SEARCH_TOOL",
    # Tax Research
    "tax_research_search",
    "TAX_RESEARCH_SEARCH_DESCRIPTION",
    "TAX_RESEARCH_SEARCH_PARAMETERS",
    "TAX_RESEARCH_SEARCH_TOOL",
]
