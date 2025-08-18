from backend.src.agentic_framework.base_agent.agent import BaseAgent
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cro.cro_tool_registry import register_cro_tools
from backend.src.stress_test.runner import run_stress_test_workflow
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import get_upside_downside_ratios
from pydantic import BaseModel
from typing import List, Literal
import json

print(f"""
╔═══════════════════════════════════════════════╗                                             
║  ╔═╗╦═╗╔═╗╔═╗╦ ╦╦╔╦╗╔═╗╦                      ║
║  ╠═╝╠╦╝║ ║╠═╝╠═╣║ ║ ╠═╣║                      ║
║  ╩  ╩╚═╚═╝╩  ╩ ╩╩ ╩ ╩ ╩╩                      ║
║  Agent: CRO Agent                             ║
║  Fund: Consumer Staples Fund                  ║
╚═══════════════════════════════════════════════╝
""")

class CROPortfolioItem(BaseModel):
	ticker: str
	position: Literal["long", "short"]
	weight: float
	reason: str

class FinalPortfolio(BaseModel):
	portfolio: List[CROPortfolioItem]

class CROAgent(BaseAgent):
    def __init__(self, system_prompt: str = cro_system_prompt, user_prompt: str = cro_user_prompt):
        super().__init__(system_prompt, user_prompt, max_iterations=75, save_messages=True, model="gpt-4.1", verbose=True)
        
        register_cro_tools(self)

    def run(self):
        result = super().run()

        final_text = (result.get("final_text") or "").strip()
        
        if not final_text:
            return result
        
        # Strip "Final Answer:" prefix if present
        if final_text.startswith("Final Answer:"):
            final_text = final_text[len("Final Answer:"):].strip()
        
        try:
            final_comp = self.client.chat.completions.parse(
                model=self.llm,
                messages=[
                    {"role": "system", "content": "Convert the JSON array to match the schema format with a 'portfolio' key."},
                    {"role": "user", "content": final_text},
                ],
                response_format=FinalPortfolio,
            )
            parsed: FinalPortfolio = final_comp.choices[0].message.parsed
            result["final_text"] = json.dumps([item.model_dump() for item in parsed.portfolio])
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Parse failed, keeping original: {e}")
            pass
        
        return result["final_text"]

if __name__ == "__main__":
    agent = CROAgent()
    result = agent.run()

    print("="*100)
    print("CRO Agent Result:")
    print("="*100)
    print(result)



