"""OrchestratorAgent - Decomposes complex tasks and delegates to worker agents."""

from functools import partial
from turtle import position
from typing import Optional, List

from pydantic import BaseModel
from langfuse import propagate_attributes
from app.core.atlas.models.notebook import Notebook

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback, AgentResponse
from app.core.atlas.models.new_plan import Plan
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.base.search_engine import LLM_WEB_SEARCH_TOOL
from app.core.atlas.tools.orchestrator import (
    UPDATE_PLAN_TOOL,
    update_plan,
)
from app.core.atlas.tools.orchestrator.retrieve_note import retrieve_notes, RETRIEVE_NOTES_TOOL
from app.core.atlas.tools.worker_agent.setup import DEPLOY_WORKER_TOOL, _resolve_and_deploy
from app.core.atlas.prompts.orchestrator_agent import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    build_plan_prompt,
)
from app.core.atlas.planning.agent import PlannerAgent
from app.utils.gpt_parser import parse_with_gpt

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
        plan_first: bool = True,
        format_output: Optional[type[BaseModel]] = None,
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
        self.format_output = format_output
        self.notebook = Notebook()
        
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
        self.tool_handler = ToolHandler(
            self, self.printer, chat_callback=self.chat_callback
        )
        self.execution_loop = ExecutionLoop(self)

        #----- Register the Tools specific to the orchestrator agent -----#
        # Reason: partial pre-binds notebook so the LLM only sees task + tools.
        self.add_tool(
            **DEPLOY_WORKER_TOOL,
            function=partial(_resolve_and_deploy, self.notebook),
        )
        self.add_tool(
            **RETRIEVE_NOTES_TOOL,
            function=partial(retrieve_notes, self.notebook),
        )
        self.add_tool(**LLM_WEB_SEARCH_TOOL)

    def run(self) -> AgentResponse:
        """Execute the orchestrator's task decomposition and delegation loop."""
        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="orchestrator_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:
        
            self.langfuse.update_current_trace(
                name="OrchestratorAgent",
                input=self.task,
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "max_iterations": str(self.max_iterations),
                },
            )

            # ----- Keep the planner agent inside the orchestrator span ----- #
            if self.plan_first:
                print("Plan-first mode enabled. Generating plan...")
                planner = PlannerAgent(task=self.task, print_mode=PrintMode.PRODUCTION)
                self.plan = planner.run()
                self.add_tool(**{**UPDATE_PLAN_TOOL, "function": partial(update_plan, self.plan)})
                print(f"Plan generated: {self.plan}")
                print("="*100)

            system_prompt = build_plan_prompt(self.plan) if self.plan else ORCHESTRATOR_SYSTEM_PROMPT

            self.messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.task},
            ]

            with propagate_attributes(
                session_id=self.session_id,
                tags=["OrchestratorAgent", self.provider],
                metadata={"model": self.model}
            ):
                result = self.execution_loop.execute()

            self.langfuse.update_current_trace(output=result["answer"])
            run_span.update(output=result["answer"])

            parsed_output = None
            if result["stop_reason"] == "answer_ready" and self.format_output:
                try:
                    parsed_output = parse_with_gpt(
                        query=result["answer"],
                        target_model=self.format_output,
                    )
                except Exception as e:
                    print(f"Error parsing output: {e}")
                    parsed_output = None

            return AgentResponse(
                answer=result["answer"],
                tool_calls_made=result["tool_calls"],
                tokens_used=result["total_tokens"],
                iterations=result["iterations"],
                stop_reason=result["stop_reason"],
                plan=self.plan if self.plan else None,
                parsed_output=parsed_output if parsed_output else None,
            )

if __name__ == "__main__":
    task = """
    Context: I am a 24 year old and I want to invest $3,000 to $4,000 thousand dollars and I want to build a portfolio of 7-10 stocks or etfs.
    My time horizon for this investment is 6-8 months. My goal is to maximize my risk adjusted returns and make around 20-30% return in those 6-8 months.

    Your Goal: Build me a well hedged+diversified portfolio that is well constructed to maximize risk adjusted returns and mitigate any macro volatility.

    your ouput format is:
    {
        "positions": [
            {
                "ticker": "TICKER_SYMBOL_HERE",
                "allocation": "ALLOCATION_AS_DECIMAL_BETWEEN_0_AND_1_HERE",
                "investment_thesis": "DETAILED_INVESTMENT_THESES_HERE",
                "investment_strategy": "DETAILED_INVESTMENT_STRATEGY_HERE"
            }
        ]
    }
    """
    class Position(BaseModel):
        ticker: str
        allocation: str
        investment_thesis: str
        investment_strategy: str

    class Portfolio(BaseModel):
        positions: List[Position]

    orchestrator_agent = OrchestratorAgent(
        task=task,
        provider="anthropic",
        model="claude-opus-4-6",
        max_iterations=50,
        print_mode=PrintMode.PRODUCTION,
        temperature=0.7,
        plan_first=True,
        format_output=Portfolio,
    )
    result = orchestrator_agent.run()
    print(result.parsed_output.model_dump_json(indent=4))
