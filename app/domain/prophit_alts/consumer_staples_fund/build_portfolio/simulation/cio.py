"""CIO Simulation Agent.

This module implements the CIOSimulationAgent, which is a specialized version of the
CIOAgent that operates with a historical cutoff date (September 30, 2024) for backtesting
and portfolio validation purposes.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel

from app.core.agentic_framework.base_agent import BaseAgent
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.prompts import (
    cio_system_prompt,
    cio_user_prompt,
)
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.tool_registry import (
    register_cio_tools,
)
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.simulation.config import (
    SIMULATION_CUTOFF_DATE,
)
from app.core.agentic_framework.base_agent.memory.domain_memory import DomainMemory
from typing import Literal


class CIOPortfolioItem(BaseModel):
    """Schema for a single portfolio position."""
    ticker: str
    position: Literal["long", "short"]
    thesis: str
    key_drivers: str
    allocation: float

class FinalPortfolio(BaseModel):
    """Schema for the final portfolio output."""
    portfolio: List[CIOPortfolioItem]

class CIOSimulationAgent(BaseAgent):
    """CIO Agent for simulation/backtesting with historical data cutoff.

    This agent operates as if the current date is September 30, 2024, using only
    data available up to that date. This enables immediate validation of portfolio
    construction decisions without waiting for real-time performance.

    Attributes:
        cutoff_date: The historical date to use as "today" (default: Sept 30, 2024)
    """

    def __init__(
        self,
        cutoff_date: datetime = SIMULATION_CUTOFF_DATE,
        max_iterations: int = 250,
        plan_first: bool = True,
        save_messages: bool = True,
        model: str = "gpt-4.1",
        verbose: bool = True,
        memory_refresh_interval: int = 20,
    ):
        """Initialize the CIO Simulation Agent.

        Args:
            cutoff_date: The date to use as "today" in simulation (default: Sept 30, 2024)
            max_iterations: Maximum number of agent iterations
            plan_first: Whether to create a plan before executing
            save_messages: Whether to save conversation messages
            model: LLM model to use
            verbose: Whether to print verbose output
            memory_refresh_interval: How often to refresh episodic memory
        """
        self.cutoff_date = cutoff_date

        # Inject the simulation date naturally into the system prompt
        date_injection = f"\nToday's date is {cutoff_date.strftime('%B %d, %Y')}.\n"
        modified_system_prompt = date_injection + cio_system_prompt

        # Initialize base agent with date-injected prompts and simulation_date parameter
        super().__init__(
            system_prompt=modified_system_prompt,
            user_prompt=cio_user_prompt,
            max_iterations=max_iterations,
            plan_first=plan_first,
            save_messages=save_messages,
            model=model,
            verbose=verbose,
            memory_refresh_interval=memory_refresh_interval,
            simulation_date=cutoff_date,  # Enable simulation mode - auto-injects _simulation_date into all tool calls
        )

        # Register CIO tools (simulation_date is auto-injected by BaseAgent)
        register_cio_tools(self)

        if self.verbose:
            print(f"🕰️  CIO Simulation Agent initialized with cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}")
            print(f"📊 Agent will operate as if today is {self.cutoff_date.strftime('%B %d, %Y')}")

    def _initialize_domain_memory(self):
        """Initialize CIO-specific domain memories for portfolio construction.

        Uses the same domain memory as the production CIO agent, as the portfolio
        construction principles and patterns remain the same regardless of date.

        Note: We override the current_date in memory to match the simulation cutoff.
        """
        # Load domain memory but prevent it from saving changes (to avoid overwriting dates)
        self.domain_memory = DomainMemory(
            agent_type='cio',
            save_memory=True,  # Load from disk
            verbose=self.verbose
        )

        # Override the date retrieval method to return simulation date
        def get_simulation_date():
            return self.cutoff_date.strftime('%Y-%m-%d')
        self.domain_memory.get_current_date = get_simulation_date

        # Prevent saving to avoid overwriting the memory file with simulation dates
        self.domain_memory.save_memory = False

        if self.verbose:
            total_memories = sum(len(m) for m in self.domain_memory.memories.values())
            if total_memories == 0:
                print("⚠️  No CIO memories found - agent will have no portfolio construction knowledge!")
            else:
                print(f"🧠 CIO Simulation Agent loaded with {total_memories} portfolio construction memories")
                print(f"📅 Memory date overridden to simulation cutoff: {self.cutoff_date.strftime('%Y-%m-%d')}")

    def run(self):
        """Run the simulation agent and parse the final portfolio output.

        Returns:
            FinalPortfolio: The constructed portfolio with allocations and theses
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🎬 Starting CIO Simulation Agent (Cutoff: {self.cutoff_date.strftime('%Y-%m-%d')})")
            print(f"{'='*80}\n")

        result = super().run()  # Run main BaseAgent workflow

        final_text = (result.get("final_text") or "").strip()

        if not final_text:
            if self.verbose:
                print("⚠️  No final text returned from agent")
            return result

        # Parse the final output into structured format
        if self.verbose:
            print(f"\n{'='*80}")
            print("📝 Parsing final portfolio output...")
            print(f"{'='*80}\n")

        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.model,
            response_format=FinalPortfolio,
            output_key="portfolio",
            verbose=self.verbose
        )

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"✅ CIO Simulation Agent completed successfully")
            print(f"{'='*80}\n")

        return result["final_text"]


if __name__ == "__main__":
    # Example usage
    agent = CIOSimulationAgent(verbose=True)
    result = agent.run()

    print("="*100)
    print("CIO SIMULATION AGENT RESULT:")
    print("="*100)
    print(result)
    print("\n")
    print("="*100)
    print("NEXT STEPS:")
    print("="*100)
    print("1. Track the performance of this portfolio from October 2024 to present")
    print("2. Compare against SPY benchmark and consumer staples sector index")
    print("3. Analyze which theses were correct and which were incorrect")
    print("4. Use insights to refine domain memory and portfolio construction process")
    print("="*100)