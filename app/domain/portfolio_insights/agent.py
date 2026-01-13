from app.core.agentic_framework.base_agent.agent import BaseAgent

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.callbacks.state_callback import StateCallback
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.domain.ai_watchlist.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from typing import Optional

from app.domain.portfolio_insights.tool_registry import register_portfolio_insights_tools
from .models import InsightsResponseModel

class PortfolioInsightsAgent(BaseAgent):
    response_model = InsightsResponseModel

    def __init__(
        self,
        user_preferences: str,
        print_mode: str = PrintMode.VERBOSE,
        state_callback: Optional[StateCallback] = None,
    ):
        if not user_preferences or not user_preferences.strip():
            raise ValueError("user_preferences is required and cannot be empty")

        self.user_preferences = user_preferences.strip()

        dynamic_user_prompt = self._build_user_prompt()

        super().__init__(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=dynamic_user_prompt,
            max_iterations=200,
            plan_first=True,
            print_mode=print_mode,
            state_callback=state_callback,
        )

        register_portfolio_insights_tools(self)

    def _build_user_prompt(self) -> str:
        return USER_PROMPT_TEMPLATE.format(user_query=self.user_preferences)

