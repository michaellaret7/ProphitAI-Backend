"""WorkerAgent - Lightweight agent for executing focused tasks with scoped tools."""

from functools import partial
from typing import Any, Callable, List, Optional

from prophitai_atlas.agents.base import AgentBase
from prophitai_atlas.models import PrintMode, AgentResponse, WORKER_PROVIDER, WORKER_MODEL
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.prompts.worker import build_worker_system_prompt
from prophitai_atlas.tools.base import web_search
from prophitai_atlas.tools.base.worker_agent.write_note import write_note, WRITE_NOTE_TOOL

from prophitai_shared.time_utils import get_current_utc_time


class WorkerAgent(AgentBase):
    """Lightweight agent for executing a focused task with scoped tools.

    Used by the orchestrator Agent to run isolated execution loops per task.
    Reuses ExecutionLoop (same as Agent) — no planning, terminates on
    text-only response. Internal messages never leave the worker.

    Workers receive only the tools they need, registered directly at init.
    No deferred tools, no register_tools overhead.
    """

    def __init__(
        self,
        task: str,
        notebook: Notebook,
        *,
        tools: Optional[List[Callable]] = None,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 100,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        chat_callback: Optional[Any] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(
            provider=provider or WORKER_PROVIDER,
            model=model or WORKER_MODEL,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
            chat_callback=chat_callback,
            session_id="worker",
        )

        self.task = task
        self.user_id = user_id
        self.notebook = notebook
        self.custom_system_prompt = system_prompt

        # --- Built-in tools (always present) --- #

        # Reason: partial pre-binds notebook and worker_task so the LLM only sees title + content.
        self.add_tool(
            **WRITE_NOTE_TOOL,
            function=partial(write_note, self.notebook, worker_task=self.task),
        )

        self.add_tool(**web_search.tool)

        # --- Register scoped tools directly --- #
        if tools:
            for func in tools:
                self.add_tool(**func.tool)

    def run(self) -> AgentResponse:
        """Execute the worker's task and return the result."""

        with self.observer.agent_run(
            name="worker_agent.run",
            input=self.task,
            provider=self.provider,
            model=self.model,
        ) as run_span:

            worker_prompt = self._build_system_prompt()

            self.messages = [
                {"role": "system", "content": self._wrap_system_for_provider(worker_prompt)},
                {"role": "user", "content": self.task},
            ]

            trace_name = self.get_trace_name()
            
            with self.observer.trace_context(
                trace_name=trace_name,
                session_id=self.session_id,
                tags=[trace_name, self.provider],
                metadata={"model": self.model}
            ):
                result = self.execution_loop.execute() # main agent execution loop 

            run_span.update(output=result["answer"])

            return AgentResponse(
                answer=result["answer"],
                tool_calls_made=result["tool_calls"],
                tokens_used=result["total_tokens"],
                cache_creation_input_tokens=result["cache_creation_input_tokens"],
                cache_read_input_tokens=result["cache_read_input_tokens"],
                iterations=result["iterations"],
                stop_reason=result["stop_reason"]
            )

    # ================================
    # --> Helper funcs
    # ================================

    def _build_system_prompt(self) -> str:
        """Build the system prompt as plain text. Provider wrapping happens at the boundary."""
        if self.custom_system_prompt:
            date = get_current_utc_time().strftime("%m/%d/%Y")
            return f"{self.custom_system_prompt}\n\nToday's date is {date}."

        return build_worker_system_prompt()
