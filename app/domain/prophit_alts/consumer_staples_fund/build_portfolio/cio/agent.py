from typing_extensions import List
from pydantic import BaseModel
from app.core.agentic_framework.base_agent import BaseAgent
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cio_agent_prompts import cio_system_prompt, cio_user_prompt
from .tool_registry import register_cio_tools
from app.core.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from typing import Literal

class CIOPortfolioItem(BaseModel):
	ticker: str
	position: Literal["long", "short"]
	thesis: str
	key_drivers: str
	allocation: float

class FinalPortfolio(BaseModel):
	portfolio: List[CIOPortfolioItem]

class CIOAgent(BaseAgent):
    def __init__(self):
        super().__init__(cio_system_prompt, cio_user_prompt, max_iterations=250, plan_first=True, save_messages=True, model="gpt-5", verbose=True, memory_refresh_interval=10)
        
        register_cio_tools(self)

    def _initialize_semantic_memory(self):
        """Initialize CIO-specific semantic memories for portfolio construction."""
        # Initialize semantic memory for CIO agent
        self.semantic_memory = SemanticMemory(agent_type='cio', save_memory=True, verbose=self.verbose)
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No CIO memories found - agent will have no portfolio construction knowledge!")
            else:
                print(f"🧠 CIO Agent loaded with {total_memories} portfolio construction memories")

    def run(self):
        result = super().run()  # Run main BaseAgent workflow

        final_text = (result.get("final_text") or "").strip()
        
        if not final_text:
            return result
        
        # Use utility function for consistent parsing
        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.llm,
            response_format=FinalPortfolio,
            output_key="portfolio",
            verbose=self.verbose
        )
        
        return result["final_text"]


if __name__ == "__main__":
    agent = CIOAgent()
    result = agent.run()
    print("="*100)
    print("CIO Agent Result:")
    print("="*100)
    print(result)





   






    

