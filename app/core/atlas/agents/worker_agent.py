"""WorkerAgent - Lightweight agent for executing focused tasks with scoped tool sets."""

from typing import Optional, List, Dict, Any

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.prompts.worker import WORKER_SYSTEM_PROMPT
from app.core.atlas.tools.deep.write_notes import WRITE_NOTE_TOOL


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
        max_iterations: int = 20,
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

        self.add_tool(**WRITE_NOTE_TOOL)

        # Register the dynamically assigned tools
        for tool_def in tools:
            self.add_tool(**tool_def)

    def run(self) -> Dict[str, Any]:
        """Execute the worker's task and return the result."""
        self.messages = [
            {"role": "system", "content": WORKER_SYSTEM_PROMPT},
            {"role": "user", "content": self.task},
        ]

        result = self.execution_loop.execute()

        return {
            "answer": result["answer"],
            "tool_calls_made": result["tool_calls"],
            "tokens_used": result["total_tokens"],
            "iterations": result["iterations"],
            "stop_reason": result["stop_reason"],
        }

if __name__ == "__main__":
    agent = WorkerAgent(
        task="Find me any trends from the CUBE earnings call transcripts.",
        provider="gemini",
        model="gemini-3-pro-preview",
        tools=[EARNINGS_CALL_SEARCH_TOOL],
    )
    result = agent.run()
    print(result)
