"""Agent - Unified conversational and orchestration agent."""

from __future__ import annotations

from functools import partial
from typing import Callable, List, Dict, Any, Optional, Union

from pydantic import BaseModel

from prophitai_atlas.models import (
    PrintMode,
    AgentResponse,
    ChatCallback,
    NoOpChatCallback,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
)
from prophitai_atlas.models.notebook import Notebook
from prophitai_atlas.models.new_plan import Plan
from prophitai_atlas.prompts.base import build_base_system_blocks, build_base_system_prompt
from prophitai_atlas.prompts.plan_injection import inject_plan_tasks, inject_plan_tasks_blocks
from prophitai_atlas.tools.catalogue import build_deferred_tools_data
from prophitai_atlas.tools.base.register_tools import (
    REGISTER_TOOLS_TOOL,
    register_tools_fn,
)

from .base import AgentBase
from prophitai_atlas.tools.base import (
    llm_web_search,
    RETRIEVE_NOTES_TOOL,
    retrieve_notes,
    UPDATE_PLAN_TOOL,
    update_plan,
)
from prophitai_atlas.agents.planner_agent import PlannerAgent
from prophitai_atlas.utils.gpt_parser import parse_with_gpt


class Agent(AgentBase):
    """Unified agent for interactive chat and complex task orchestration.

    Supports two modes per turn:
    - Chat (default): Direct tool calling with 3-tier decision framework.
    - Plan-first: PlannerAgent generates a structured plan, then the agent
      executes each task via worker delegation and marks them complete.

    Args:
        tools: List of @agent_tool-decorated callables registered immediately at init.
            These tools are in the LLM context window from the first turn.
        deferred_tools: List of @agent_tool-decorated callables available via register_tools.
            Their names and short descriptions are appended to the system prompt.

    Use `run()` for multi-turn chat with optional per-turn planning.
    Pass `plan_first=True` for one-shot orchestrator-style jobs.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 200,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        user_id: Optional[str] = None,
        session_id: str = "default",
        tools: Optional[List[Callable]] = None,
        deferred_tools: Optional[List[Callable]] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(
            provider=provider or DEFAULT_PROVIDER,
            model=model or DEFAULT_MODEL,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
            chat_callback=chat_callback,
            session_id=session_id,
        )

        self.plan: Optional[Plan] = None
        self.notebook = Notebook()
        self.user_id: Optional[str] = user_id

        # --- Deferred tools wiring --- #
        if deferred_tools:
            data = build_deferred_tools_data(deferred_tools)
            deferred_description = data.description
            tool_registry = data.tool_registry
            all_tools = data.all_tools
        else:
            deferred_description = ""
            tool_registry = {}
            all_tools = {}

        # --- Register Tools Upfront --- #
        if tools:
            for func in tools:
                self.add_tool(**func.tool)

        # --- System prompt --- #
        # Reason: if there is a system prompt passed to the agent, that is the system prompt used for the agent. Else, use the generic base prompt.
        if system_prompt is not None:
            self.system_prompt: str = system_prompt
            self.system_prompt_blocks: Optional[List[Dict[str, Any]]] = [
                {"type": "text", "text": system_prompt, "cacheable": True},
            ]
            
        else:
            self.system_prompt = build_base_system_prompt()
            self.system_prompt_blocks = build_base_system_blocks()

        # Reason: Append deferred tools description to whatever prompt is used (system-prompt agnostic)
        if deferred_description:
            self.system_prompt = f"{self.system_prompt}\n\n{deferred_description}"

            if self.system_prompt_blocks is not None:

                self.system_prompt_blocks.append(
                    {"type": "text", "text": deferred_description, "cacheable": True}
                )

        # --- Add the built-in tools ---
        self.add_tool(**llm_web_search.tool)

        self.add_tool(
            **RETRIEVE_NOTES_TOOL,
            function=partial(retrieve_notes, self.notebook),
        )

        # --- Add the register_tools tool only if deferred_tools is not None ---
        if deferred_tools:
            self.add_tool(
                **REGISTER_TOOLS_TOOL,
                function=partial(register_tools_fn, tool_registry, all_tools, self),
            )


        print(f"Initialized Agent with model: {self.model} (provider: {self.provider})")

    def build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Build the message list for the LLM call.

        Trusts the caller to provide properly filtered conversation_history.
        Use ChatSession.get_history() to pre-filter at the boundary.
        """
        if system_prompt is not None:
            prompt = system_prompt

        elif self.provider == "anthropic" and self.system_prompt_blocks is not None:
            prompt = self.system_prompt_blocks

        else:
            prompt = self.system_prompt

        messages = [{"role": "system", "content": prompt}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_message})

        return messages

    def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        *,
        plan_first: bool = False,
        format_output: Optional[type[BaseModel]] = None,
    ) -> AgentResponse:
        """Run the agent for a user query.

        Args:
            user_message: The user's message or task description.
            conversation_history: Prior conversation turns (ignored when plan_first=True).
            plan_first: If True, run PlannerAgent first and execute the plan.
            format_output: Optional Pydantic model to parse the final answer into.
        """
        span_name = "agent.run_planned" if plan_first else "agent.run"

        with self.observer.agent_run(
            name=span_name,
            input=user_message,
            provider=self.provider,
            model=self.model,
        ) as run_span:

            try:
                self.total_tokens = 0 # reset total tokens
                self.cache_creation_input_tokens = 0
                self.cache_read_input_tokens = 0

                # --- Planning phase ---
                if plan_first:
                    if self.printer.is_verbose:
                        print("Plan-first mode enabled. Generating plan...")

                    planner = PlannerAgent(
                        task=user_message,
                        system_context=self.system_prompt,
                        print_mode=PrintMode.PRODUCTION,
                    )

                    self.plan = planner.run()

                    # Reason: remove first to avoid stale binding if a prior run() left it registered
                    self.remove_tool(UPDATE_PLAN_TOOL["name"])
                    
                    self.add_tool(
                        **UPDATE_PLAN_TOOL,
                        function=partial(update_plan, self.plan, self.chat_callback),
                    )

                    self.chat_callback.on_plan_created(self.plan)

                    if self.printer.is_verbose:
                        print(f"Plan generated: {self.plan}")

                # --- Select system prompt ---
                if plan_first and self.plan:
                    if self.provider == "anthropic" and self.system_prompt_blocks is not None:
                        system_prompt = inject_plan_tasks_blocks(self.system_prompt_blocks, self.plan)
                    else:
                        system_prompt = inject_plan_tasks(self.system_prompt, self.plan)
                else:
                    system_prompt = None  # uses self.system_prompt via build_messages

                # --- Build messages ---
                self.messages = self.build_messages(
                    user_message, 
                    conversation_history, 
                    system_prompt=system_prompt
                )

                # --- Execute ---
                trace_name = self.get_trace_name(planned=plan_first)
                
                with self.observer.trace_context(
                    trace_name=trace_name,
                    session_id=self.session_id,
                    tags=[trace_name, self.provider],
                    metadata={
                        "model": self.model,
                        "provider": self.provider,
                        "max_iterations": str(self.max_iterations),
                    },
                ):
                    result = self.execution_loop.execute()

                run_span.update(output={
                    "answer": result["answer"],
                    "tool_calls": result["tool_calls"],
                    "total_tokens": result["total_tokens"],
                    "cache_creation_input_tokens": result["cache_creation_input_tokens"],
                    "cache_read_input_tokens": result["cache_read_input_tokens"],
                    "iterations": result["iterations"],
                    "stop_reason": result["stop_reason"],
                })

                # --- Structured output parsing ---
                parsed_output = None
                if result["stop_reason"] == "answer_ready" and format_output:
                    try:
                        parsed_output = parse_with_gpt(
                            query=result["answer"],
                            target_model=format_output,
                        )
                    except (RuntimeError, ValueError, TypeError) as e:
                        self.printer.error(f"Error parsing output: {e}")
                        parsed_output = None

                return AgentResponse(
                    answer=result["answer"],
                    tool_calls_made=result["tool_calls"],
                    tokens_used=result["total_tokens"],
                    cache_creation_input_tokens=result["cache_creation_input_tokens"],
                    cache_read_input_tokens=result["cache_read_input_tokens"],
                    iterations=result["iterations"],
                    stop_reason=result["stop_reason"],
                    plan=self.plan if plan_first else None,
                    parsed_output=parsed_output,
                )

            finally:
                # Clean up per-turn state
                if plan_first:
                    self.remove_tool("update_plan")



