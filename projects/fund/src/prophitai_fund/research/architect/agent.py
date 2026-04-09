"""Strategy Architect Agent — translates idea generator output into a Strategy Manifest.

Reads the algo_trading framework (indicators, sizers, risk controls, signal primitives)
via sandbox read tools to map natural-language strategy descriptions into a structured,
implementation-ready spec. Produces a validated StrategyManifest JSON that downstream
coding agents consume directly.
"""

from functools import partial
from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_fund.research.architect.tool_registry import ARCHITECT_TOOLS
from prophitai_fund.tools import append_memory, retrieve_memory

from prophitai_fund.research.architect.models import StrategyManifest

class StrategyArchitectAgent:
    """Translates idea generator output into a Strategy Manifest.

    Reads the algo_trading framework via sandbox tools to understand
    available indicators, sizers, risk controls, and signal primitives.
    Maps the natural-language strategy description into a structured
    StrategyManifest that downstream coding agents consume.
    """

    DEFAULT_TASK_TEMPLATE = (
        "Translate the following strategy idea into a complete Strategy Manifest. "
        "Use the sandbox tools to read the algo_trading framework and understand "
        "what indicators, sizers, risk controls, and signal primitives are available. "
        "Map every aspect of the idea to concrete framework components.\n\n"
        "---\n\n"
        "{idea_text}"
    )

    def __init__(
        self,
        *,
        sandbox_id: str,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "strategy_architect",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):

        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system_prompt.md"
        system_prompt = prompt_path.read_text().format(date=date, sandbox_id=sandbox_id)

        self.agent = Agent(
            tools=ARCHITECT_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider,
            model=model,
            print_mode=print_mode,
        )

        # Bind memory tools with file paths
        memory_file = Path(__file__).parent / "memory.md"

        self.agent.add_tool(**{**append_memory.tool, "function": partial(append_memory, memory_file)})
        self.agent.add_tool(**{**retrieve_memory.tool, "function": partial(retrieve_memory, memory_file)})

    def run(self, idea_text: str) -> AgentResponse:
        """Translate a strategy idea into a Strategy Manifest.

        Args:
            idea_text: Raw markdown output from the Idea Generator agent.

        Returns:
            AgentResponse with parsed_output containing a StrategyManifest.
        """
        task = self.DEFAULT_TASK_TEMPLATE.format(idea_text=idea_text)

        return self.agent.run(
            task,
            plan_first=True,
            format_output=StrategyManifest,
        )
