"""OrchestratorAgent - Decomposes complex tasks and delegates to worker agents."""

from functools import partial
from typing import Optional, List, Dict, Any

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback
from app.core.atlas.models.new_plan import Plan
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.worker_agent.setup import DEPLOY_WORKER_TOOL
from app.core.atlas.tools.base.search_engine import LLM_WEB_SEARCH_TOOL
from app.core.atlas.tools.orchestrator import UPDATE_PLAN_TOOL, update_plan
from app.core.atlas.prompts.chat_agent_prompts.orchestrator_agent import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    build_plan_prompt,
)
from app.core.atlas.planning.agent import PlannerAgent

class OrchestratorAgent(AgentBase):
    """Decomposes complex tasks and delegates sub-tasks to worker agents.

    Supports two modes:
    - Default: Ad-hoc decomposition using think + deploy_worker_agent.
    - Plan-first: PlannerAgent generates a structured plan, then the
      orchestrator executes each task and marks it complete via update_plan.
    """

    def __init__(
        self,
        task: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 50,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        plan_first: bool = False,
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

        self.plan_first = plan_first
        self.plan: Optional[Plan] = None

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = NoOpChatCallback()
        self.session_id = "orchestrator"
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(self, self.printer, chat_callback=self.chat_callback)
        self.execution_loop = ExecutionLoop(self)

        # Register orchestrator-specific tools (think + calculator come from AgentBase)
        self.add_tool(**DEPLOY_WORKER_TOOL)
        self.add_tool(**LLM_WEB_SEARCH_TOOL)

    def run(self) -> Dict[str, Any]:
        """Execute the orchestrator's task decomposition and delegation loop."""

        if self.plan_first:
            planner = PlannerAgent(task=self.task, print_mode=PrintMode.PRODUCTION)
            self.plan = planner.run()
            self.add_tool(**{**UPDATE_PLAN_TOOL, "function": partial(update_plan, self.plan)})

        system_prompt = build_plan_prompt(self.plan) if self.plan else ORCHESTRATOR_SYSTEM_PROMPT

        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self.task},
        ]

        result = self.execution_loop.execute()

        return {
            "answer": result["answer"],
            "tool_calls_made": result["tool_calls"],
            "tokens_used": result["total_tokens"],
            "iterations": result["iterations"],
            "stop_reason": result["stop_reason"],
            "plan": self.plan.model_dump() if self.plan else None,
        }


if __name__ == "__main__":
    orchestrator_agent = OrchestratorAgent(
        task="Build a defensive consumer staples portfolio.",
        provider="anthropic",
        model="claude-opus-4-6",
        max_iterations=50,
        print_mode=PrintMode.DEBUG,
        temperature=0.7,
        plan_first=True,
    )
    result = orchestrator_agent.run()
    print(result["answer"])
