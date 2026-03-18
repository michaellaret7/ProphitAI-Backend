"""WorkerAgent - Lightweight agent for executing focused tasks with scoped tool sets."""

from functools import partial
from typing import Optional, List, Dict, Any

from langfuse import propagate_attributes

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback, AgentResponse
from app.core.atlas.models.notebook import Notebook
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.prompts.worker import build_worker_system_prompt
from app.core.atlas.tools.base import llm_web_search
from app.core.atlas.tools.worker_agent.write_note import write_note, WRITE_NOTE_TOOL


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
        notebook: Notebook,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 30,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        chat_callback: Optional[Any] = None,
    ):

        if provider is None:
            provider = "gemini"
        if model is None:
            model = "gemini-3.1-pro-preview"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.task = task
        self.notebook = notebook

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = chat_callback if chat_callback is not None else NoOpChatCallback()
        
        self.session_id = "worker"
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(
            self, self.printer, chat_callback=self.chat_callback
        )
        self.execution_loop = ExecutionLoop(self)

        # Reason: partial pre-binds notebook and worker_task so the LLM only sees title + content.
        self.add_tool(
            **WRITE_NOTE_TOOL,
            function=partial(write_note, self.notebook, worker_task=self.task),
        )
        self.add_tool(**llm_web_search.tool)

        # Register the dynamically assigned tools
        for tool_def in tools:
            self.add_tool(**tool_def)

    def run(self) -> AgentResponse:
        """Execute the worker's task and return the result."""

        with self.langfuse.start_as_current_observation(
            as_type="agent",
            name="worker_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:

            self.messages = [
                {"role": "system", "content": build_worker_system_prompt()},
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

if __name__ == "__main__":
    worker = WorkerAgent(
        task="What is the latest news in the stock market?",
        tools=[llm_web_search.tool],
        notebook=Notebook(),
        provider="groq",
        model="openai-gpt-oss-120b",
        chat_callback=NoOpChatCallback(),
        max_iterations=30,
    )
    result = worker.run()
    print(result)