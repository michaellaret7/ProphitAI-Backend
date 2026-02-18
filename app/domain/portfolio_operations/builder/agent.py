"""PortfolioBuilder - Constructs diversified portfolios via orchestrator delegation."""

from typing import Optional

from app.core.atlas.agents import OrchestratorAgent
from app.core.atlas.models import PrintMode
from app.core.atlas.models.callbacks import ChatCallback
from app.domain.portfolio_operations.builder.prompts import PORTFOLIO_BUILDER_PROMPT

class PortfolioBuilder(OrchestratorAgent):
    """Portfolio construction agent - builds allocated portfolios via orchestration."""

    def __init__(
        self,
        user_preferences: str,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        provider: str = "anthropic",
        model: str = "claude-opus-4-6",
        chat_callback: Optional[ChatCallback] = None,
        session_id: str = "portfolio_builder",
    ):
        task = PORTFOLIO_BUILDER_PROMPT.format(user_preferences=user_preferences)

        super().__init__(
            task=task,
            print_mode=print_mode,
            provider=provider,
            model=model,
            chat_callback=chat_callback,
            session_id=session_id,
        )



