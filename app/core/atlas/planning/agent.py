"""WorkerAgent - Lightweight agent for executing focused tasks with scoped tool sets."""

from typing import Optional, List, Dict, Any

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.prompts.worker import WORKER_SYSTEM_PROMPT
from app.core.atlas.tools.deep.write_notes import WRITE_NOTE_TOOL
from app.utils.gpt_parser import parse_with_gpt
from app.core.atlas.models.new_plan import Plan
from app.core.atlas.prompts.planner import PLANNER_SYSTEM_PROMPT

class PlannerAgent(AgentBase):
    """Lightweight agent for executing a focused task with a scoped tool set.

    Used by the OrchestratorAgent to run isolated execution loops per task.
    Reuses ExecutionLoop (same as ChatAgent) — no planning, terminates on
    text-only response. Internal messages never leave the worker.
    """

    def __init__(
        self,
        task: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 5,
        print_mode: PrintMode = PrintMode.VERBOSE,
        temperature: Optional[float] = None
    ):
        provider = provider or "grok"
        model = model or "grok-4-1-fast-non-reasoning"

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

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(self, self.printer, chat_callback=self.chat_callback)
        self.execution_loop = ExecutionLoop(self)

    def run(self) -> Dict[str, Any]:
        """Execute the worker's task and return the result."""
        self.messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": self.task},
        ]

        response = self.execution_loop.execute()

        answer = parse_with_gpt(
            response["answer"],
            target_model=Plan
        )

        return answer


