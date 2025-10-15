from typing import Dict, Optional
import uuid
from pydantic import BaseModel, Field
from typing_extensions import Literal
from app.core.agentic_framework.base_agent import BaseAgent
from .prompts import system_prompt, user_prompt
from .tool_registry import register_optimizer_tools
from app.core.agentic_framework.base_agent.memory.domain_memory import DomainMemory
from app.utils.decorators.timer import timer

#TODO: Add a portfolio compare tool to compare the new proposed portfolio to the old one that needed optimizaiton

class PortfolioPosition(BaseModel):
    allocation: float
    position: Literal["long", "short"]
    thesis: str

class PortfolioChanges(BaseModel):
    added: Optional[Dict[str, str]] = Field(default_factory=dict, description="Tickers added and reasons")
    removed: Optional[Dict[str, str]] = Field(default_factory=dict, description="Tickers removed and reasons")
    adjusted: Optional[Dict[str, str]] = Field(default_factory=dict, description="Adjustments made and descriptions")

class OptimizedPortfolio(BaseModel):
    portfolio: Dict[str, PortfolioPosition] = Field(description="Optimized portfolio with ticker -> position details")
    changes: PortfolioChanges = Field(description="Portfolio changes made during optimization")

class OptimizerAgent(BaseAgent):
    def __init__(self, portfolio_id: str):
        """
        Initialize OptimizerAgent with a specific portfolio to optimize.

        Args:
            portfolio_id: UUID of the portfolio to optimize (must be a valid UUID format)

        Raises:
            ValueError: If portfolio_id is not provided or is invalid format
        """
        if not portfolio_id:
            raise ValueError("portfolio_id is required")

        # Basic UUID format validation
        try:
            uuid.UUID(portfolio_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid portfolio_id format: '{portfolio_id}'. "
                f"Must be a valid UUID (e.g., 'b07e9c3b-01a1-4431-9b5f-2048c1bc7e11'). "
                f"Error: {str(e)}"
            )

        self.portfolio_id = portfolio_id

        # Inject portfolio_id into user prompt with clear instruction
        dynamic_user_prompt = user_prompt.replace(
            "1. Use the get_user_portfolio tool to get the user's portfolio.",
            f"1. CRITICAL: Use the get_user_portfolio tool with EXACTLY this portfolio_id parameter: '{portfolio_id}' (this is the target portfolio UUID for optimization)."
        )

        # Also inject into system prompt for extra clarity
        dynamic_system_prompt = f"""{system_prompt}

CRITICAL CONTEXT:
- Target portfolio_id for this optimization: '{portfolio_id}'
- You MUST use this exact UUID when calling get_user_portfolio
- Do NOT modify or change this UUID in any way
"""

        super().__init__(
            system_prompt=dynamic_system_prompt,
            user_prompt=dynamic_user_prompt,
            max_iterations=200,
            plan_first=True,
            save_messages=True,
            model="gpt-4.1",
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

        # Use dict-specific parser (avoids OpenAI structured output issues with Dict fields)
        result["final_text"] = self.utilities.parse_agent_dict_output(
            final_text=final_text,
            response_format=OptimizedPortfolio,
            verbose=self.verbose
        )

        return result["final_text"]

@timer
def main():
    portfolio_id = "01be5cf2-a1fe-45b0-b9a4-cf9cc1a94b36"
    agent = OptimizerAgent(portfolio_id=portfolio_id)
    result = agent.run()

    print("="*100)
    print("Optimizer Agent Result:")
    print("="*100)
    print(result)

if __name__ == "__main__":
    main()