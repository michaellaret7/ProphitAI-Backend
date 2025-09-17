from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cro.tool_registry import register_cro_tools
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from pydantic import BaseModel
from typing import List, Literal

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

class ActionableSuggestion(BaseModel):
	ticker: str
	action: Literal["increase allocation", "decrease allocation", "drop position"]
	amount: float = None  
	reason: str

class FinalPortfolio(BaseModel):
	portfolio: List[CROPortfolioItem]

class PortfolioWithSuggestions(BaseModel):
	portfolio: List[CROPortfolioItem]
	suggestions: List[ActionableSuggestion]

class CROAgent(BaseAgent):
    def __init__(self, system_prompt: str = cro_system_prompt, user_prompt: str = cro_user_prompt):
        super().__init__(system_prompt, user_prompt, max_iterations=250, save_messages=True, model="gpt-5", verbose=True, memory_refresh_interval=10)
        
        register_cro_tools(self)
    
    def _initialize_semantic_memory(self):
        """Initialize CRO-specific semantic memories for risk management."""
        # Initialize semantic memory for CRO agent
        self.semantic_memory = SemanticMemory(agent_type='cro', save_memory=True, verbose=self.verbose)
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No CRO memories found - agent will have no risk management knowledge!")
            else:
                print(f"🧠 CRO Agent loaded with {total_memories} risk management memories")

    def run(self):
        result = super().run() # Run main BaseAgent workflow

        final_text = (result.get("final_text") or "").strip()
        
        if not final_text:
            return result
        
        # Use utility function for consistent parsing with fallback support
        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.llm,
            response_format=PortfolioWithSuggestions,
            output_key="portfolio",
            fallback_formats=[(FinalPortfolio, "portfolio")],
            verbose=self.verbose
        )
        
        return result["final_text"]

if __name__ == "__main__":
    agent = CROAgent()
    result = agent.run()

    print("="*100)
    print("CRO Agent Result:")
    print("="*100)
    print(result)



