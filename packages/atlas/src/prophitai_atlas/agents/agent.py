"""Agent - Unified conversational and orchestration agent."""

from __future__ import annotations

from functools import partial
from typing import Callable, List, Dict, Any, Optional, Union

from pydantic import BaseModel
from langfuse import propagate_attributes

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
from prophitai_atlas.prompts.base import build_base_system_prompt
from prophitai_atlas.prompts.plan_injection import inject_plan_tasks
from prophitai_atlas.tools.catalogue import ToolCatalogue
from prophitai_atlas.tools.base.register_tools import (
    build_register_tools_schema,
    register_tools_fn,
)

from .base import AgentBase
from prophitai_atlas.tools.base import (
    llm_web_search,
    DEPLOY_WORKER_TOOL,
    _resolve_and_deploy,
    build_deploy_worker_schema,
    retrieve_notes,
    RETRIEVE_NOTES_TOOL,
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

        # --- Tool catalogue wiring --- #
        if tools:
            self.catalogue: Optional[ToolCatalogue] = ToolCatalogue(tools)

            catalogue_text = self.catalogue.build_catalogue_description()
            tool_registry = self.catalogue.tool_registry
            all_tools = self.catalogue.all_tools

            deploy_schema = build_deploy_worker_schema(all_tools) # Build the deploy_worker_agent tool schema with all avail tools
        else:
            self.catalogue = None
            catalogue_text = ""
            tool_registry = {}
            all_tools = {}
            deploy_schema = DEPLOY_WORKER_TOOL

        # Reason: caller-provided prompt takes precedence; fallback to generic base prompt
        if system_prompt is not None:
            self.system_prompt: str = system_prompt
        else:
            self.system_prompt = build_base_system_prompt(tool_catalogue=catalogue_text)

        reg_schema = build_register_tools_schema(tool_registry, all_tools)

        # --- Add the built-in tools ---
        self.add_tool(**llm_web_search.tool)
        
        self.add_tool(
            **RETRIEVE_NOTES_TOOL,
            function=partial(retrieve_notes, self.notebook),
        )

        # --- Add the register_tools tool ---
        self.add_tool(
            **reg_schema,
            function=partial(register_tools_fn, tool_registry, all_tools, self),
        )

        # --- Add the deploy_worker_agent tool ---
        self.add_tool(
            **deploy_schema,
            function=partial(
                _resolve_and_deploy, all_tools, self.notebook, self.chat_callback
            ),
        )

        print(f"Initialized Agent with model: {self.model} (provider: {self.provider})")
        print(f"Registered tools ({len(self.tool_functions)}): {sorted(self.tool_functions.keys())}")

    def build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build the message list for the LLM call.

        Trusts the caller to provide properly filtered conversation_history.
        Use ChatSession.get_history() to pre-filter at the boundary.
        """
        prompt = system_prompt or self.system_prompt
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
        max_iterations: Optional[int] = None,
    ) -> AgentResponse:
        """Run the agent for a user query.

        Args:
            user_message: The user's message or task description.
            conversation_history: Prior conversation turns (ignored when plan_first=True).
            plan_first: If True, run PlannerAgent first and execute the plan.
            format_output: Optional Pydantic model to parse the final answer into.
            max_iterations: Override max iterations for this turn (defaults to 50 when plan_first=True).
        """
        original_max_iterations = self.max_iterations

        if max_iterations is not None:
            self.max_iterations = max_iterations
        elif plan_first:
            self.max_iterations = 50

        span_name = "agent.run_planned" if plan_first else "agent.run"

        with self.langfuse.start_as_current_observation(
            as_type="agent",
            name=span_name,
            input=user_message,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:

            try:
                self.total_tokens = 0 # reset total tokens

                # --- Planning phase ---
                if plan_first:
                    if self.printer.is_verbose:
                        print("Plan-first mode enabled. Generating plan...")

                    planner = PlannerAgent(
                        task=user_message,
                        print_mode=PrintMode.PRODUCTION,
                    )
                    self.plan = planner.run()
                    print(f"Plan generated: {self.plan}")

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
                trace_name = "Agent (planned)" if plan_first else "Agent"
                with propagate_attributes(
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

                run_span.update(output=result["answer"])

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
                    iterations=result["iterations"],
                    stop_reason=result["stop_reason"],
                    plan=self.plan if plan_first else None,
                    parsed_output=parsed_output,
                )

            finally:
                # Clean up per-turn state
                if plan_first:
                    self.remove_tool("update_plan")

                self.max_iterations = original_max_iterations



