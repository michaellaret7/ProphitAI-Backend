from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.industry_prompts import build_industry_prompt
from .tools import get_eligible_tickers, get_base_ticker_info
from .tool_registry import register_industry_tools
from pydantic import BaseModel
from typing import List, Literal
import json
import time

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
        super().__init__(*build_industry_prompt(industry), max_iterations=75, plan_first=True, save_messages=True, model="gpt-4.1", verbose=True, memory_refresh_interval=8)
        
        register_industry_tools(self)

    def _initialize_semantic_memory(self):
        """Initialize {industry}-specific semantic memories for risk management."""
 
        agent_type = self.industry

        self.semantic_memory = SemanticMemory(agent_type=agent_type, save_memory=True, verbose=self.verbose)
        
        try:
            eligible_tickers = get_eligible_tickers(agent_type) or []
        except Exception:
            eligible_tickers = []
        self.semantic_memory.tickers = eligible_tickers
        
        if self.verbose:
            print(f"🧾 Injected {len(eligible_tickers)} eligible tickers into semantic memory for {self.industry}")
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print(f"⚠️ No {self.industry} memories found - agent will have no {self.industry} knowledge!")
            else:
                print(f"🧠 {self.industry} Agent loaded with {total_memories} {self.industry} memories")

    def run(self):
        result = super().run()

        final_text = (result.get("final_text") or "").strip()
        if not final_text:
            return result

        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()

        try:
            final_comp = self.client.chat.completions.parse(
                model=self.llm,
                messages=[
                    {"role": "system", "content": "Convert the JSON array to match the schema format with a 'recommendations' key."},
                    {"role": "user", "content": final_text},
                ],
                response_format=IndustryRecommendations,
            )

            parsed: IndustryRecommendations = final_comp.choices[0].message.parsed
            output_data = {
                "recommendations": [item.model_dump() for item in parsed.recommendations]
            }
            result["final_text"] = json.dumps(output_data)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ IndustryRecommendations parse failed, keeping original: {e}")
            pass

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
        from backend.src.repositories.portfolio_data import add_initial_positions as repo_add_initial_positions

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
                    "allocation": float(conviction)*100,  # repository expects percent, it will divide by 100
                    "reasoning": thesis,
                })

            return repo_add_initial_positions(positions=positions, industry=self.industry, fund_name=fund_name)
        except Exception:
            return False





   






    

