"""Tax Harvester Agent — autonomous tax-loss harvesting analyst for a user's portfolio."""

from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_tax_harvester.tool_registry import TAX_HARVESTER_TOOLS


class TaxHarvesterAgent(Agent):
    """Generates tax-loss harvesting proposals for a user's portfolio.

    Scans the user's holdings for unrealized losses, vets each loss against the
    wash-sale rule, and proposes replacement securities that preserve market
    exposure while crystallizing the deductible loss.
    """

    DEFAULT_TASK = (
        "Review the user's portfolio holdings, identify all positions with "
        "harvestable unrealized losses, and produce a structured tax-loss "
        "harvesting plan: which lots to sell, the wash-sale rule check, and "
        "the replacement security that maintains exposure without triggering "
        "a wash sale."
    )

    def __init__(
        self,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "tax_harvester",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.VERBOSE,
    ):
        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system.md"
        system_prompt = prompt_path.read_text().format(date=date)

        super().__init__(
            tools=TAX_HARVESTER_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider or "anthropic",
            model=model or "claude-sonnet-4-6",
            print_mode=print_mode,
        )

    def run(self, task: Optional[str] = None, **kwargs) -> AgentResponse:
        """Execute the tax harvester agent."""
        return super().run(task or self.DEFAULT_TASK, plan_first=True, **kwargs)


if __name__ == "__main__":
    agent = TaxHarvesterAgent(provider="anthropic", model="claude-opus-4-7")
    response = agent.run()
    print(response)
