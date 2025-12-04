from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.callbacks import StateCallback
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL

from app.domain.ai_watchlist.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from typing import Optional

class AiWatchlistAgent(BaseAgent):
    def __init__(self, user_preferences: str, state_callback: Optional["StateCallback"] = None):
        self.user_preferences = user_preferences
        self.user_prompt = self._build_user_prompt()
        
        super().__init__(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self.user_prompt,
            max_iterations=50,
            plan_first=True,
            print_mode=PrintMode.DEBUG,
            state_callback=state_callback,
        )
    
        tools = [
            #  Screener Tools
            EQUITY_SCREENER_TOOL,
            ETF_SCREENER_TOOL,

            #  Ticker Analysis Tools

        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )


    def _build_user_prompt(self) -> str:  # ← Now at class level (correct)
        return USER_PROMPT_TEMPLATE.replace("{{USER_PREFERENCES}}", self.user_preferences)