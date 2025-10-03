from typing import List, Dict, Optional
from pydantic import BaseModel
from typing_extensions import Literal
from app.core.agentic_framework.base_agent import BaseAgent
from app.domain.portfolio_operations.optimization.optimizer.prompts import system_prompt, user_prompt
from app.domain.portfolio_operations.optimization.optimizer.tool_registry import register_optimizer_tools
from app.core.agentic_framework.base_agent.memory.domain_memory import DomainMemory
from app.domain.portfolio_operations.optimization.optimizer.tool_registry import register_optimizer_tools
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.tool_registry import register_cio_tools

class OptimizedPosition(BaseModel):
    ticker: str
    allocation: float
    position: Literal["long", "short"]
    changes_from_original: str

class OptimizedPortfolio(BaseModel):
    portfolio: List[OptimizedPosition]
    optimization_summary: str

class OptimizerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt=system_prompt, 
            user_prompt=user_prompt, 
            max_iterations=200, 
            plan_first=True,
            save_messages=True, 
            # model="gpt-5", 
            verbose=True, 
            memory_refresh_interval=20
        )
        
        register_optimizer_tools(self)
        
    def _initialize_domain_memory(self):
        """Initialize Optimizer-specific domain memories for portfolio optimization."""
        # Initialize domain memory for Optimizer agent
        self.domain_memory = DomainMemory(agent_type='optimizer', save_memory=True, verbose=self.verbose)
        
        if self.verbose:
            total_memories = sum(len(m) for m in self.domain_memory.memories.values())
            if total_memories == 0:
                print("⚠️ No Optimizer memories found - agent will have no optimization knowledge!")
            else:
                print(f"🧠 Optimizer Agent loaded with {total_memories} optimization memories")

    def run(self):
        result = super().run()  # Run main BaseAgent workflow

        final_text = (result.get("final_text") or "").strip()
        
        if not final_text:
            return result
        
        # Use utility function for consistent parsing
        result["final_text"] = self.utilities.parse_agent_output(
            final_text=final_text,
            client=self.client,
            llm=self.model,
            response_format=OptimizedPortfolio,
            output_key="portfolio",
            verbose=self.verbose
        )
        
        return result["final_text"]

if __name__ == "__main__":
    agent = OptimizerAgent()
    result = agent.run()
    
    print("="*100)
    print("Optimizer Agent Result:")
    print("="*100)
    print(result)