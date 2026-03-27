"""PlannerAgent - Generates structured execution plans for the OrchestratorAgent."""

from typing import Optional

from langfuse import propagate_attributes

from prophitai_atlas.agents.base import AgentBase
from prophitai_atlas.models import PrintMode, PLANNER_PROVIDER, PLANNER_MODEL
from prophitai_atlas.utils.gpt_parser import parse_with_gpt
from prophitai_atlas.models.new_plan import Plan
from prophitai_atlas.prompts.planner import PLANNER_SYSTEM_PROMPT


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
        super().__init__(
            provider=provider or PLANNER_PROVIDER,
            model=model or PLANNER_MODEL,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
            session_id="planner",
        )

        self.task = task

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
