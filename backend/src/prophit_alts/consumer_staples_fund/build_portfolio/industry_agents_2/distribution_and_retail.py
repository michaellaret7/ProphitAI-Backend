from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.agentic_framework.base_agent.memory.semantic_memory import SemanticMemory
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.industry_prompts.beverages import beverages_system_prompt, beverages_user_prompt
from .industry_tools import register_industry_tools, get_eligible_tickers

class DistributionAndRetailAgent(BaseAgent):
    def __init__(self):
        super().__init__(beverages_system_prompt, beverages_user_prompt, max_iterations=75, plan_first=True, save_messages=True, model="gpt-4.1", verbose=True, memory_refresh_interval=8)

        register_industry_tools(self)

    def _initialize_semantic_memory(self):
        """Initialize Beverages-specific semantic memories for risk management."""
        # Initialize semantic memory for CRO agent
        self.semantic_memory = SemanticMemory(agent_type='distribution_and_retail', save_memory=True, verbose=self.verbose)
        
        try:
            eligible_tickers = get_eligible_tickers("consumer_staples_distribution_and_retail") or []
        except Exception:
            eligible_tickers = []
        self.semantic_memory.tickers = eligible_tickers
        
        if self.verbose:
            print(f"🧾 Injected {len(eligible_tickers)} eligible tickers into semantic memory for Beverages")
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.semantic_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No Beverages memories found - agent will have no beverages knowledge!")
            else:
                print(f"🧠 Beverages Agent loaded with {total_memories} beverages memories")

    def run(self):
        return super().run()


if __name__ == "__main__":
    agent = DistributionAndRetailAgent()
    agent.run()
    
