from app.core.agentic_framework.base_agent import BaseAgent
from app.core.agentic_framework.base_agent.memory.domain_memory import DomainMemory
from app.db.core.db_config import ProphitAltsSession, MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.prophit_alts_models import Fund
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.industry_agents.prompts import build_industry_prompt
from .tool_registry import register_industry_tools
from pydantic import BaseModel
from typing import List, Literal
import json
import time
import yaml
from app.core.agentic_framework.tool_lib.agent_specific_tools.industry import get_eligible_tickers
from app.utils.decorators.database import with_session
from app.db.core.models.prophit_alts_models import FundInitialPosition

class IndustryRecommendation(BaseModel):
    ticker: str
    position: Literal["long", "short"]
    thesis: str
    key_drivers: str
    key_risks: str
    valuation_snapshot: str
    conviction: float

class IndustryRecommendations(BaseModel):
    recommendations: List[IndustryRecommendation]

class IndustryAgent(BaseAgent):
    def __init__(self, industry: str):
        self.industry = industry
        super().__init__(*build_industry_prompt(industry), max_iterations=250, plan_first=True, save_messages=True, verbose=True, memory_refresh_interval=8, use_episodic_memory=True, model="gpt-5-mini", reasoning_effort="high")
        
        register_industry_tools(self)

    def _initialize_domain_memory(self):
        """Initialize {industry}-specific domain memories for risk management."""
 
        agent_type = self.industry

        self.domain_memory = DomainMemory(agent_type=agent_type, save_memory=True, verbose=self.verbose)

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
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.domain_memory.memories.values())
            if total_memories == 0:
                print(f"⚠️ No {self.industry} memories found - agent will have no {self.industry} knowledge!")
            else:
                print(f"🧠 {self.industry} Agent loaded with {total_memories} {self.industry} memories")

    def run(self):
        result = super().run()

        final_text = (result.get("final_text") or "").strip()
        if not final_text:
            return result

        # Use utility function for consistent parsing
        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.model,
            response_format=IndustryRecommendations,
            output_key="recommendations",
            verbose=self.verbose
        )

        return result["final_text"]

    def save_initial_positions(self, fund_name: str, recommendations_json: str) -> bool:
        """
        Persist agent recommendations into prophit_alts_funds.initial_positions.

        Args:
            fund_name: Target fund name (e.g., "consumer_staples_fund").
            recommendations_json: JSON string from self.run() with key 'recommendations'.

        Returns:
            bool indicating success.
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

