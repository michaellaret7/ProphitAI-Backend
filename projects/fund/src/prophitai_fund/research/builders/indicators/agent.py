"""Indicator Builder Agent — writes indicator code from a Strategy Manifest.

Takes the StrategyManifest produced by the Strategy Architect and writes
production-quality indicator code files into an E2B sandbox: custom
BaseIndicator subclasses, a BaseIndicatorSuite configuration, derived
feature functions, and module exports. Produces an IndicatorBuildResult
for downstream agents.
"""

from functools import partial
from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_atlas.tools.base.worker_agent.deploy_scoped import (
    DEPLOY_SCOPED_WORKER_TOOL,
    deploy_scoped_worker,
)

from prophitai_fund.research.architect.models import StrategyManifest
from prophitai_fund.research.builders.indicators.models import IndicatorBuildResult
from prophitai_fund.research.builders.indicators.tool_registry import INDICATOR_BUILDER_TOOLS
from prophitai_fund.tools import append_memory, retrieve_memory
from prophitai_fund.tools.worker_registry import WORKERS


class IndicatorBuilderAgent:
    """Writes indicator code files from a Strategy Manifest.

    Reads the algo_trading framework via sandbox tools and codebase_researcher
    workers, then writes custom BaseIndicator subclasses, a BaseIndicatorSuite,
    derived features, and module exports into the sandbox.
    """

    DEFAULT_TASK_TEMPLATE = (
        "Build all indicator code files for the following strategy manifest. "
        "The manifest contains the complete spec for indicators, derived features, "
        "and their dependencies. Write production-quality code that follows the "
        "framework conventions exactly.\n\n"
        "---\n\n"
        "STRATEGY MANIFEST:\n"
        "{manifest_json}"
    )

    def __init__(
        self,
        *,
        sandbox_id: str,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "indicator_builder",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):

        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system_prompt.md"
        system_prompt = prompt_path.read_text().format(date=date, sandbox_id=sandbox_id)

        self.agent = Agent(
            tools=INDICATOR_BUILDER_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider,
            model=model,
            print_mode=print_mode,
        )

        # Reason: Memory tools are bound with partial to bake in the file path.
        # The LLM never sees the _memory_file parameter.
        memory_file = Path(__file__).parent / "memory.md"

        self.agent.add_tool(**{**append_memory.tool, "function": partial(append_memory, memory_file)})
        self.agent.add_tool(**{**retrieve_memory.tool, "function": partial(retrieve_memory, memory_file)})

        # Reason: deploy_scoped_worker needs notebook, callback, user_id, and registry
        # pre-bound. The LLM only sees worker_type, task, plan_task_id, context.
        self.agent.add_tool(
            **DEPLOY_SCOPED_WORKER_TOOL,
            function=partial(
                deploy_scoped_worker,
                self.agent.notebook,
                chat_callback or NoOpChatCallback(),
                None,
                WORKERS,
            ),
        )

    def run(self, manifest: StrategyManifest) -> AgentResponse:
        """Build indicator code files from a Strategy Manifest.

        Args:
            manifest: The complete StrategyManifest from the Strategy Architect.

        Returns:
            AgentResponse with parsed_output containing an IndicatorBuildResult.
        """
        manifest_json = manifest.model_dump_json(indent=2)
        task = self.DEFAULT_TASK_TEMPLATE.format(manifest_json=manifest_json)

        return self.agent.run(
            task,
            plan_first=True,
            format_output=IndicatorBuildResult,
        )
