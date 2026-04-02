"""WorkerAgent - Lightweight agent for executing focused tasks with deferred tool registration."""

from functools import partial
from typing import Optional, List, Callable, Any

from langfuse import propagate_attributes

from prophitai_atlas.agents.base import AgentBase
from prophitai_atlas.models import PrintMode, AgentResponse, WORKER_PROVIDER, WORKER_MODEL
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.prompts.worker import build_worker_system_blocks, build_worker_system_prompt
from prophitai_atlas.tools.base import llm_web_search, write_note, WRITE_NOTE_TOOL
from prophitai_atlas.tools.base.register_tools import REGISTER_TOOLS_TOOL, register_tools_fn
from prophitai_atlas.tools.catalogue import build_deferred_tools_data


class WorkerAgent(AgentBase):
    """Lightweight agent for executing a focused task with deferred tool registration.

    Used by the orchestrator Agent to run isolated execution loops per task.
    Reuses ExecutionLoop (same as Agent) — no planning, terminates on
    text-only response. Internal messages never leave the worker.

    Workers receive all available tools as deferred_tools and can register
    the ones they need via the register_tools meta-tool.
    """

    def __init__(
        self,
        task: str,
        deferred_tools: List[Callable],
        notebook: Notebook,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 30,
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

        # Reason: partial pre-binds notebook and worker_task so the LLM only sees title + content.
        self.add_tool(
            **WRITE_NOTE_TOOL,
            function=partial(write_note, self.notebook, worker_task=self.task),
        )
        self.add_tool(**llm_web_search.tool)

        # --- Deferred tools wiring --- #
        if deferred_tools:
            data = build_deferred_tools_data(deferred_tools)
            self._deferred_description = data.description

            self.add_tool(
                **REGISTER_TOOLS_TOOL,
                function=partial(register_tools_fn, data.tool_registry, data.all_tools, self),
            )
        else:
            self._deferred_description = ""

    def run(self) -> AgentResponse:
        """Execute the worker's task and return the result."""

        with self.langfuse.start_as_current_observation(
            as_type="agent",
            name="worker_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:

            # Reason: Append deferred tools description to the worker prompt
            if self.provider == "anthropic":
                worker_prompt: Any = build_worker_system_blocks()
                
                if self._deferred_description:
                    worker_prompt.append(
                        {"type": "text", "text": self._deferred_description, "cacheable": True}
                    )
            else:
                worker_prompt = build_worker_system_prompt()
                if self._deferred_description:
                    worker_prompt = f"{worker_prompt}\n\n{self._deferred_description}"

            self.messages = [
                {"role": "system", "content": worker_prompt},
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
                cache_creation_input_tokens=result["cache_creation_input_tokens"],
                cache_read_input_tokens=result["cache_read_input_tokens"],
                iterations=result["iterations"],
                stop_reason=result["stop_reason"]
            )
