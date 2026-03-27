"""Domain agents for the ProphitAI API."""

from .watchlist import WatchlistAgent
from .portfolio_builder import PortfolioBuilderAgent
from .clarify import generate_clarifying_questions, compose_enriched_brief
from .models import (
    WatchlistResponse,
    WatchlistItem,
    PortfolioResponse,
    PortfolioPosition,
    ClarificationResponse,
    ClarifyingQuestion,
    ClarifyRequest,
    ClarifyResult,
    ClarifyAnswer,
    BuildRequest,
)

__all__ = [
    "WatchlistAgent",
    "PortfolioBuilderAgent",
    "generate_clarifying_questions",
    "compose_enriched_brief",
    "WatchlistResponse",
    "WatchlistItem",
    "PortfolioResponse",
    "PortfolioPosition",
    "ClarificationResponse",
    "ClarifyingQuestion",
    "ClarifyRequest",
    "ClarifyResult",
    "ClarifyAnswer",
    "BuildRequest",
]
