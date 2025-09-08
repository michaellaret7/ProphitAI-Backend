from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.industry_prompts import build_industry_prompt
from .tools import get_eligible_tickers
from .tool_registry import register_industry_tools
from pydantic import BaseModel
from typing import List, Literal
import json

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

if __name__ == "__main__":
    industries = [
        "beverages",
        "food_products",
        "household_products",
        "personal_care_products",
        "consumer_staples_distribution_and_retail",
        "tobacco",
    ]

    agent = IndustryAgent(industries[4])
    final_result = agent.run()
    print(final_result)
    print(type(final_result))

    # from backend.src.db.core.db_config import MarketSession
    # from backend.src.db.core.market_data_models import *
    # from backend.src.utils.serialize_output import serialize_sqlalchemy_obj

    # tickers = []
    # with MarketSession() as session:
    #     tickers = session.query(BalanceSheet).join(Ticker).filter(
    #         Ticker.ticker == "AAL", 
    #         BalanceSheet.fillingDate >= "2025-04-01"
    #     ).all()
    #     for balance_sheet in tickers:
    #         print(serialize_sqlalchemy_obj(balance_sheet))