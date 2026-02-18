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
        provider: str = "gemini",
        model: str = "gemini-3-pro-preview",
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


if __name__ == "__main__":
    builder = PortfolioBuilder(
        user_preferences="Build me a moderate-risk, long-term growth portfolio focused on technology and healthcare with some dividend income.",
        provider="anthropic",
        model="claude-opus-4-6",
    )
    result = builder.run()
    print(result.answer)
