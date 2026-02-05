"""Chat agent prompts for different agent types."""

from .equity_research import get_equity_research_prompt
from .macro_research import get_macro_research_prompt
from .tax_research import get_tax_research_prompt
from .user_uploads import get_user_uploads_prompt

__all__ = [
    "get_equity_research_prompt",
    "get_macro_research_prompt",
    "get_tax_research_prompt",
    "get_user_uploads_prompt",
]
