"""DeepAgent - Complex long-running task execution agent."""

from typing import Dict, Any, Optional, List
from datetime import datetime

from pydantic import BaseModel

from app.core.atlas.models import NoOpCallback, StateCallback, Plan
from app.core.atlas.execution import DeepExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter, ensure_notes_file
from app.core.atlas.tools.deep_registry import register_base_deep_tools
from app.core.atlas.prompts import UNIVERSAL_AGENT_MESSAGE
from app.core.atlas.models import PrintMode
from app.core.atlas.logging import create_agent_output_dir
from app.utils.gpt_parser import parse_with_gpt

from .base import AgentBase


class DeepAgent(AgentBase):
    """Autonomous agent for complex long-running tasks with planning capabilities."""

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 100,
        print_mode: PrintMode = PrintMode.VERBOSE,
        temperature: Optional[float] = None,
        reasoning_effort: Optional[str] = None,
        plan_first: bool = True,
        simulation_date: Optional[datetime] = None,
        state_callback: Optional[StateCallback] = None,
    ):

        if provider is None:
            provider = "anthropic"
        if model is None:
            model = "claude-haiku-4-5-20251001"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.reasoning_effort = reasoning_effort

        # Planning
        self.plan_first = plan_first
        self.plan: Optional[Plan] = None

        # Simulation mode for backtesting
        self.simulation_date = simulation_date

        # Frontend streaming callback
        self.state_callback = state_callback if state_callback is not None else NoOpCallback()

        # Notes tracking
        self.note_titles: List[str] = []

        # Agent identity and output location
        self.agent_name = self.__class__.__name__
        self.output_dir = create_agent_output_dir(self.agent_name)
        ensure_notes_file(self.output_dir, self.agent_name)

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(self, self.printer)
        self.execution_loop = DeepExecutionLoop(self)

        # Register base tools
        register_base_deep_tools(self)

        print(f"Initialized Agent with model: {self.model} (provider: {self.provider})")

    def run(self, response_format: Optional[type[BaseModel]] = None) -> Dict[str, Any]:
        """Execute the agent's main ReAct loop."""
        self.messages = [
            {"role": "system", "content": UNIVERSAL_AGENT_MESSAGE},
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]

        if self.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG, PrintMode.PRODUCTION]:
            print(f"\n{'='*60}")
            print(f"Starting agent run")
            print(f"Task: {self.user_prompt}")
            print(f"{'='*60}\n")

        start_time = datetime.now()
        result = self.execution_loop.execute()
        end_time = datetime.now()
        duration = end_time - start_time

        print(f"\n{'='*60}")
        print(f"Agent run complete")
        print(f"Iterations: {result['iterations']}")
        print(f"Total tokens: {result['total_tokens']}")
        print(f"Stop reason: {result['stop_reason']}")
        print(f"Time taken: {duration}")
        print(f"Model: {self.model} ({self.provider})")
        print(f"{'='*60}\n")

        if response_format:
            final_answer = (result.get("final_answer") or "").strip()
            if final_answer:
                result["parsed_output"] = parse_with_gpt(
                    query=final_answer,
                    target_model=response_format
                )

        return result


if __name__ == "__main__":
    from app.core.atlas.tools.data.screening import EQUITY_SCREENER_TOOL
    from app.core.atlas.tools.ticker.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
    agent = DeepAgent(
        system_prompt="You are a helpful assistant that can answer questions and help with tasks using tool calls.",
        user_prompt="Run through the equity screener and find me tickers with low debt that have high alpha.",
        provider="grok",
        model="grok-4-1-fast-reasoning",
        print_mode=PrintMode.DEBUG,
    )
    agent.add_tool(**EQUITY_SCREENER_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
    result = agent.run()
    print(result)