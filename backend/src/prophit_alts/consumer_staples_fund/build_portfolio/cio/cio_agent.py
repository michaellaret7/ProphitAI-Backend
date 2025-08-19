from backend.src.agentic_framework.base_agent import BaseAgent
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cio_agent_prompts import cio_system_prompt, cio_user_prompt
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.macro_agent import MacroAnalyst
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *

class CIOAgent(BaseAgent):
    """
    Chief Investment Officer Agent with specialized portfolio management tools.
    Extends BaseAgent with CIO-specific functionality.
    """
    
    def __init__(self, system_prompt: str = cio_system_prompt, user_prompt: str = cio_user_prompt):
        # Initialize parent class first
        super().__init__(system_prompt, user_prompt)
        
        # Add CIO-specific tools
        self._register_cio_tools()
    
    def _retrieve_ticker_pool(self):
        """Retrieve all of the positions that were pushed to the database by your lower level industry analysts."""
        session = ProphitAltsSession()
        positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

        positions_dict = {}
        for position in positions:
            positions_dict[position.ticker_name] = {
                "position": position.position.value,  # Extract the string value from enum
                "industry": position.industry,
                "risk_allocation": position.risk_allocation,
                "reasoning": position.reasoning
            }

        return positions_dict
    
    def _register_cio_tools(self):
        """Register CIO-specific tools that are not in the base class."""

        # Tool 1: Macro Analysis
        self.macro_analyst = MacroAnalyst()

        self.add_tool(
            name="macro_agent",
            description="Analyze the macroeconomic environment and provide a recommendation for the net exposure of the long/short Consumer Staples Fund.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: self.macro_analyst.get_final_recommendation()
        )

        # Tool 2: Retrieve Positions Pool
        self.add_tool(
            name="retrieve_ticker_pool",
            description="Retrieve all of the positions that were pushed to the database by your lower level industry analysts. You will receieve a dictionary of ticker_name: {position, industry, risk_allocation, reasoning}.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: self._retrieve_ticker_pool()
        )
    
# Example usage
if __name__ == "__main__":
    # Create CIO agent with default prompts
    cio_agent = CIOAgent()
    
    # Run the agent
    result = cio_agent.run()