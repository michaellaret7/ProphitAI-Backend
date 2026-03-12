"""PlannerAgent - Generates structured execution plans for the OrchestratorAgent."""

from typing import Optional, List, Dict, Any

from langfuse import propagate_attributes

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.utils.gpt_parser import parse_with_gpt
from app.core.atlas.models.new_plan import Plan
from app.core.atlas.prompts.planner import PLANNER_SYSTEM_PROMPT


class PlannerAgent(AgentBase):
    """Generates a structured Plan for the OrchestratorAgent.

    Runs a short execution loop (default 5 iterations) to produce a Plan
    that the orchestrator then executes. Child agent — does not own the trace.
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

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = NoOpChatCallback()
        self.session_id = "planner"
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(self, self.printer, chat_callback=self.chat_callback)
        self.execution_loop = ExecutionLoop(self)

    def run(self) -> Plan:
        """Generate a structured Plan for the given task."""

        with self.langfuse.start_as_current_observation(
            as_type="agent",
            name="planner_agent.run",
            input=self.task,
            metadata={"provider": self.provider, "model": self.model},
        ) as run_span:

            self.messages = [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": self.task},
            ]

            with propagate_attributes(
                session_id=self.session_id,
                tags=["PlannerAgent", self.provider],
                metadata={"model": self.model},
            ):
                response = self.execution_loop.execute()

            plan = parse_with_gpt(
                response["answer"],
                target_model=Plan,
            )

            run_span.update(output=plan.model_dump())

            return plan

if __name__ == "__main__":
    planner = PlannerAgent(
        task=(
            "Analyze AAPL and MSFT as potential long-term portfolio holdings and determine which is more attractive "
            "at current valuation. Use the last 5 years of financial performance and the latest filings/transcripts. "
            "Evaluate competitive moat strength, AI and cloud monetization quality, capital allocation discipline, "
            "balance-sheet resilience, and downside risk under a macro slowdown. Include comparable-multiple analysis "
            "and scenario-based intrinsic valuation (bear/base/bull), then identify key 2-4 quarter catalysts, "
            "define measurable decision thresholds, and produce a final invest/hold/avoid recommendation with "
            "confidence level and thesis invalidation triggers."
        ),
        print_mode=PrintMode.PRODUCTION,
        provider="anthropic",
        model="claude-opus-4-6",
    )
    plan = planner.run()
    print(plan)