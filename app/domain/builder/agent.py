"""PortfolioBuilder - Constructs diversified portfolios via orchestrator delegation."""

from typing import Optional

from app.core.atlas.agents import OrchestratorAgent
from app.core.atlas.models import PrintMode
from app.core.atlas.models.callbacks import ChatCallback
from app.domain.builder.models import PortfolioResponse
from app.domain.builder.prompts import PORTFOLIO_BUILDER_PROMPT

class PortfolioBuilder(OrchestratorAgent):
    """Portfolio construction agent - builds allocated portfolios via orchestration."""

    def __init__(
        self,
        user_preferences: str,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        provider: str = "fireworks",
        model: str = "Kimi-K2.5",
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
            format_output=PortfolioResponse,
        )


if __name__ == "__main__":
    from app.domain.builder.clarify import run_interactive_clarification

    user_query = input("Describe your portfolio goal:\n> ").strip()
    if not user_query:
        user_query = "Build me a growth-focused tech portfolio"

    enriched_brief = run_interactive_clarification(user_query)

    print("\n--- Enriched Brief ---")
    print(enriched_brief)
    print("----------------------\n")

    # agent = PortfolioBuilder(user_preferences=enriched_brief)
    # response = agent.run()

    # print("\n--- Portfolio Response ---")
    # print(response.answer)
    # print("----------------------\n")