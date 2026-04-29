"""Dreamer Agent — autonomous nightly trade idea generator for a user's portfolio."""

from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_dreamer.tool_registry import DREAMER_TOOLS


class DreamerAgent(Agent):
    """Generates a single trade idea for a user's portfolio.

    Runs nightly. Reads the user's brief (holdings, watchlist, preferences),
    researches via curated tools, and produces one structured TradeIdea.
    """

    DEFAULT_TASK = (
        "Review the user's portfolio holdings, run the analytics tools to find "
        "the most actionable observation, and propose a single high-conviction "
        "trade idea with a clear thesis, sizing, and risk factors."
    )

    def __init__(
        self,
        *,
        user_id: str,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "dreamer",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.VERBOSE,
    ):
        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system.md"
        system_prompt = prompt_path.read_text().format(date=date)

        super().__init__(
            tools=DREAMER_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            user_id=user_id,
            provider=provider or "anthropic",
            model=model or "claude-sonnet-4-6",
            print_mode=print_mode,
        )

    def run(self, task: Optional[str] = None) -> AgentResponse:
        """Execute the dreamer agent."""
        return super().run(task or self.DEFAULT_TASK, plan_first=True)


if __name__ == "__main__":
    agent = DreamerAgent(user_id="user_3B61dvXwPyRaSZzFMuwWuw1xj31", provider="anthropic", model="claude-sonnet-4-6")
    response = agent.run()
    print(response)
