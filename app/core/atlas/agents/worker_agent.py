"""WorkerAgent - Lightweight agent for executing focused tasks with scoped tool sets."""

from typing import Optional, List, Dict, Any

from langfuse import propagate_attributes

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback, AgentResponse
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.prompts.worker import WORKER_SYSTEM_PROMPT
from app.core.atlas.tools.deep.write_notes import WRITE_NOTE_TOOL
from app.core.atlas.tools.base import LLM_WEB_SEARCH_TOOL


class WorkerAgent(AgentBase):
    """Lightweight agent for executing a focused task with a scoped tool set.

    Used by the OrchestratorAgent to run isolated execution loops per task.
    Reuses ExecutionLoop (same as ChatAgent) — no planning, terminates on
    text-only response. Internal messages never leave the worker.
    """

    def __init__(
        self,
        task: str,
        tools: List[Dict[str, Any]],
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 30,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None
    ):
        provider = provider or "gemini"
        model = model or "gemini-3-pro-preview"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.task = task

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = NoOpChatCallback()
        self.session_id = "worker"
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components (NOTE: Add these to the AgentBase class.)
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(
            self, self.printer, chat_callback=self.chat_callback
        )
        self.execution_loop = ExecutionLoop(self)

        self.add_tool(**WRITE_NOTE_TOOL) # We need to rebuild the write note tool to use this new version.
        self.add_tool(**LLM_WEB_SEARCH_TOOL)

        # Register the dynamically assigned tools
        for tool_def in tools:
            self.add_tool(**tool_def)

    def run(self) -> AgentResponse:
        """Execute the worker's task and return the result."""

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="worker_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:

            self.messages = [
                {"role": "system", "content": WORKER_SYSTEM_PROMPT},
                {"role": "user", "content": self.task},
            ]

            with propagate_attributes(
                session_id=self.session_id,
                tags=["WorkerAgent", self.provider],
                metadata={"model": self.model}
            ):
                result = self.execution_loop.execute()

            run_span.update(output=result["answer"])

            return AgentResponse(
                answer=result["answer"],
                tool_calls_made=result["tool_calls"],
                tokens_used=result["total_tokens"],
                iterations=result["iterations"],
                stop_reason=result["stop_reason"]
            )


