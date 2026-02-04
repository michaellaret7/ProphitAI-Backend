"""Chat agent prompts for different agent types."""

from .equity_research import get_equity_research_prompt
from .macro_research import get_macro_research_prompt

__all__ = [
    "get_equity_research_prompt",
    "get_macro_research_prompt",
]
