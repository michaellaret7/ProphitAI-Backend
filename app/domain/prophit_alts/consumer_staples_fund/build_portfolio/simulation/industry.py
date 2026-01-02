"""Industry Simulation Agent.

This module implements the IndustrySimulationAgent, which is a specialized version
of the IndustryAgent that operates with a historical cutoff date (September 30, 2024)
for backtesting and validation purposes.
"""

from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel

from app.core.agentic_framework.base_agent import BaseAgent
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.industry_agents.prompts import build_industry_prompt
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.industry_agents.tool_registry import register_industry_tools
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.simulation.config import SIMULATION_CUTOFF_DATE
from app.core.agentic_framework.base_agent.memory.domain_memory import DomainMemory
from app.core.agentic_framework.tool_lib.agent_specific_tools.industry import get_eligible_tickers
import json
import yaml


class IndustryRecommendation(BaseModel):
    """Schema for a single industry recommendation."""
    ticker: str
    position: Literal["long", "short"]
    thesis: str
    key_drivers: str
    key_risks: str
    valuation_snapshot: str
    conviction: float


class IndustryRecommendations(BaseModel):
    """Schema for the final recommendations output."""
    recommendations: List[IndustryRecommendation]


class IndustrySimulationAgent(BaseAgent):
    """Industry Agent for simulation/backtesting with historical data cutoff.

    This agent operates as if the current date is September 30, 2024, using only
    data available up to that date. This enables immediate validation of industry-level
    stock recommendations without waiting for real-time performance.

    Attributes:
        industry: Industry name (e.g., "Food Products", "Beverages")
        cutoff_date: The historical date to use as "today" (default: Sept 30, 2024)
    """

    def __init__(
        self,
        industry: str,
        cutoff_date: datetime = SIMULATION_CUTOFF_DATE,
        max_iterations: int = 250,
        plan_first: bool = True,
        save_messages: bool = True,
        model: str = "gpt-5-mini",
        reasoning_effort: str = "high",
        verbose: bool = True,
        memory_refresh_interval: int = 8,
        use_episodic_memory: bool = True
    ):
        """Initialize the Industry Simulation Agent.

        Args:
            industry: Industry name (e.g., "Food Products", "Beverages")
            cutoff_date: The date to use as "today" in simulation (default: Sept 30, 2024)
            max_iterations: Maximum number of agent iterations
            plan_first: Whether to create a plan before executing
            save_messages: Whether to save conversation messages
            model: LLM model to use
            reasoning_effort: Reasoning effort to use
            verbose: Whether to print verbose output
            memory_refresh_interval: How often to refresh episodic memory
            use_episodic_memory: Whether to use episodic memory
        """
        self.industry = industry
        self.cutoff_date = cutoff_date

        # Get prompts and inject simulation date
        system_prompt, user_prompt = build_industry_prompt(industry)
        date_injection = f"\nToday's date is {cutoff_date.strftime('%B %d, %Y')}.\n"
        modified_system_prompt = date_injection + system_prompt

        # Initialize base agent with date-injected prompts and simulation_date parameter
        super().__init__(
            system_prompt=modified_system_prompt,
            user_prompt=user_prompt,
            max_iterations=max_iterations,
            plan_first=plan_first,
            save_messages=save_messages,
            model=model,
            reasoning_effort=reasoning_effort,
            verbose=verbose,
            memory_refresh_interval=memory_refresh_interval,
            use_episodic_memory=use_episodic_memory,
            simulation_date=cutoff_date,  # Enable simulation mode - auto-injects _simulation_date into all tool calls
        )

        # Register industry tools (simulation_date is auto-injected by BaseAgent)
        register_industry_tools(self)

        if self.verbose:
            print(f"🕰️  {industry} Simulation Agent initialized with cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}")
            print(f"📊 Agent will operate as if today is {self.cutoff_date.strftime('%B %d, %Y')}")

    def _initialize_domain_memory(self):
        """Initialize industry-specific domain memories.

        Uses the same domain memory as the production Industry agent, as the stock
        analysis principles and patterns remain the same regardless of date.

        Note: We override the current_date in memory to match the simulation cutoff.
        """
        agent_type = self.industry

        # Load domain memory but prevent it from saving changes
        self.domain_memory = DomainMemory(
            agent_type=agent_type,
            save_memory=True,  # Load from disk
            verbose=self.verbose
        )

        # Override the date retrieval method to return simulation date
        def get_simulation_date():
            return self.cutoff_date.strftime('%Y-%m-%d')
        self.domain_memory.get_current_date = get_simulation_date

        # Prevent saving to avoid overwriting the memory file with simulation dates
        self.domain_memory.save_memory = False

        # Inject eligible tickers
        try:
            eligible_tickers_response = get_eligible_tickers(agent_type)
            # Reason: get_eligible_tickers returns YAML string, need to parse it
            parsed_response = yaml.safe_load(eligible_tickers_response)
            if parsed_response and parsed_response.get("success"):
                eligible_tickers = parsed_response.get("data", [])
            else:
                eligible_tickers = []
        except Exception:
            eligible_tickers = []
        self.domain_memory.tickers = eligible_tickers

        if self.verbose:
            print(f"🧾 Injected {len(eligible_tickers)} eligible tickers into domain memory for {self.industry}")
            total_memories = sum(len(m) for m in self.domain_memory.memories.values())
            if total_memories == 0:
                print(f"⚠️  No {self.industry} memories found - agent will have no {self.industry} knowledge!")
            else:
                print(f"🧠 {self.industry} Simulation Agent loaded with {total_memories} {self.industry} memories")
                print(f"📅 Memory date overridden to simulation cutoff: {self.cutoff_date.strftime('%Y-%m-%d')}")

    def run(self):
        """Run the simulation agent and parse the final recommendations output.

        Returns:
            IndustryRecommendations: The industry stock recommendations with theses and conviction
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🎬 Starting {self.industry} Simulation Agent (Cutoff: {self.cutoff_date.strftime('%Y-%m-%d')})")
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
            print("📝 Parsing final recommendations output...")
            print(f"{'='*80}\n")

        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.model,
            response_format=IndustryRecommendations,
            output_key="recommendations",
            verbose=self.verbose
        )

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"✅ {self.industry} Simulation Agent completed successfully")
            print(f"{'='*80}\n")

        return result["final_text"]

    def save_initial_positions(self, fund_name: str, recommendations_json: str) -> bool:
        """Persist agent recommendations into prophit_alts_funds.initial_positions.

        Args:
            fund_name: Target fund name (e.g., "consumer_staples_fund")
            recommendations_json: JSON string from self.run() with key 'recommendations'

        Returns:
            bool indicating success
        """
        from app.repositories.portfolio_data import add_initial_positions as repo_add_initial_positions

        try:
            data = json.loads(recommendations_json)
            items = data.get("recommendations", []) if isinstance(data, dict) else []

            positions = {"long": [], "short": []}
            for item in items:
                ticker = item.get("ticker")
                position_side = (item.get("position") or "").lower()
                conviction = item.get("conviction") or 0.0  # expected as decimal (e.g., 0.1 for 10%)
                thesis = item.get("thesis") or ""

                if not ticker or position_side not in ("long", "short"):
                    continue

                positions[position_side].append({
                    "ticker": ticker,
                    "allocation": float(conviction),  # Decimal format (0.25 = 25%)
                    "reasoning": thesis,
                })

            return repo_add_initial_positions(positions=positions, industry=self.industry, fund_name=fund_name)
        except Exception:
            return False


if __name__ == "__main__":
    # Example usage
    # agent = IndustrySimulationAgent(industry="food_products", verbose=True)
    agent = IndustrySimulationAgent(industry="personal_care_products", verbose=True)

    result = agent.run()

    # agent.save_initial_positions(fund_name="simulation", recommendations_json=result)
