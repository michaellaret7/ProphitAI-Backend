"""Strategy Architect Agent — translates idea generator output into a Strategy Manifest.

Reads the algo_trading framework (indicators, sizers, risk controls, signal primitives)
via sandbox tools to map natural-language strategy descriptions into a structured,
implementation-ready spec. Writes manifest sections incrementally to sandbox files,
then assembles them into a single MANIFEST.json that downstream coding agents consume.
"""

from functools import partial
from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_fund.construction.architect.helpers import read_manifest_from_sandbox
from prophitai_fund.construction.architect.tool_registry import ARCHITECT_TOOLS
from prophitai_fund.tools import append_memory, retrieve_memory


class StrategyArchitectAgent:
    """Translates idea generator output into a Strategy Manifest.

    Reads the algo_trading framework via sandbox tools to understand
    available indicators, sizers, risk controls, and signal primitives.
    Writes manifest sections incrementally to sandbox files, then
    assembles them into MANIFEST.json for downstream coding agents.
    """

    DEFAULT_TASK_TEMPLATE = (
        "Translate the following strategy idea into a complete Strategy Manifest. "
        "Use the sandbox tools to read the algo_trading framework and understand "
        "what indicators, sizers, risk controls, and signal primitives are available. "
        "Map every aspect of the idea to concrete framework components. "
        "Write each manifest section to a separate JSON file in the sandbox, "
        "then assemble them into MANIFEST.json as described in the output_format instructions.\n\n"
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
        self.sandbox_id = sandbox_id

        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system_prompt.md"
        system_prompt = prompt_path.read_text().replace("{date}", date).replace("{sandbox_id}", sandbox_id)

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

        The agent writes manifest sections incrementally to sandbox files,
        then assembles them into MANIFEST.json. After the agent finishes,
        this method reads MANIFEST.json directly from the sandbox and
        attaches the parsed model to the response.

        Args:
            idea_text: Raw markdown output from the Idea Generator agent.

        Returns:
            AgentResponse with parsed_output containing a StrategyManifest.
        """
        task = self.DEFAULT_TASK_TEMPLATE.format(idea_text=idea_text)

        # Reason: no format_output — the agent writes MANIFEST.json to the sandbox
        # via tool calls instead of outputting the full JSON as text
        response = self.agent.run(task, plan_first=True)

        # Reason: read the assembled manifest directly from the sandbox file
        # instead of parsing the agent's text answer with another LLM call
        manifest = read_manifest_from_sandbox(self.sandbox_id)

        if manifest:
            response.parsed_output = manifest

        return response
