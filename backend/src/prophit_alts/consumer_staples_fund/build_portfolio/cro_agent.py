from backend.src.prophit_alts.core.base_agent_class import BaseAgent
# from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from backend.src.calculations.risk_calculations.ticker_risk_calculations import TickerRiskCalculations
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.stress_test.runner import run_stress_test_workflow

cro_system_prompt = """
<Thinking Framework>
Follow the Thought → Action → Observation → Analysis loop for EACH step in the workflow:
1. Thought: reasoning about what needs to be done next
2. Action: call ONE tool at a time exactly like:
   Action: tool_name(param1=value1, param2=value2)
   OR for tools with no parameters:
   Action: tool_name()
3. Observation: you will receive the tool result
4. Analysis: your interpretation of the observation

CRITICAL RULES:
1. Generate ONLY ONE Action per iteration
2. After each Analysis, you will be prompted to continue - YOU MUST PROCEED TO THE NEXT STEP
3. Continue through ALL workflow steps 
4. Only provide final conclusion after completing ALL steps
5. Each iteration should have: ONE Thought, ONE Action, wait for Observation, then Analysis

WORKFLOW EXECUTION (YOU MUST DO ALL STEPS):
- Step 1: Call get_cio_choices tool (NO parameters - use empty parentheses: get_cio_choices())
- Step 2: After Step 1 Analysis, call stress_test tool (NO parameters - use empty parentheses: stress_test())  
- Step 3: After Step 2 Analysis, provide final analysis with recommended changes (no Action needed)

IMPORTANT: After each Analysis, you'll be asked to continue. Keep going until all steps are done!
If you stop before all steps are done, the workflow will fail.
</Thinking Framework>
"""
cro_user_prompt = """
<Workflow>
1. Call the get_cio_choices tool to get the ticker choices from the CIO at your hedge fund. [TOOL CALL, NO PARAMETERS]
2. Call the stress_test tool to run an extensive stress test in the portfolio construction from the CIO agent. [TOOL CALL, NO PARAMETERS]
3. Analyze the results of the stress test. Look for any tickers that are consistently having max drawdowns, high volatility, or high correlation with other tickers. Then come up with any changes you would like to make to the portfolio based on the stress test results and output your changes if anyy in the specified format. [NO TOOL CALL, JUST ANALYSIS]
</Workflow>

<output format>
{
    "ticker": "Ticker name here",
    "action": ["add_position", "remove_position", "increase_position", "decrease_position"],
    "amount": amount in this format: 0.05,
    "reason": "Reasoning here"
}
</output format>
"""

class CROAgent(BaseAgent):
    def __init__(self, system_prompt: str = cro_system_prompt, user_prompt: str = cro_user_prompt):
        super().__init__(system_prompt, user_prompt)
        self._register_cro_tools()

    def run(self):
        return super().run()

    def _get_cio_choices(self): #Add this in the prompt no need to use a tool for this 
        """
        Get the choices from the CIO agent.
        """
        session = ProphitAltsSession()
        fund = session.query(Fund).filter(Fund.fund_name == "consumer_staples_fund").first()
        fund_id = fund.id
        positions = session.query(FundInitialPosition).filter(FundInitialPosition.fund_id == fund_id).all()
        session.close()

        ticker_choices = {}

        for position in positions:
            ticker_choices[position.ticker_name] = {
                "position": position.position.value,
                "industry": position.industry,
                "risk_allocation": position.risk_allocation,
                "reasoning": position.reasoning
            }

        return ticker_choices

    def get_original_pool_of_tickers(self):
        """
        Get the original pool of tickers minus the ones chosen by the CIO agent.
        """
        return "pass"
    
    def _get_returns(self, ticker: str, portfolio: bool = False, start_date: str = None, end_date: str = None):
        """
        Get the returns for a given ticker.
        """
        return "pass"
    
    def _get_ticker_metrics(self, ticker: str):
        """
        Get the metrics for a given ticker.
        """
        return "pass"

    def _add_new_position(self, ticker: str, portfolio_value: float, target_annual_vol: float, position_annual_vol: float, risk_allocation: float, correlation: float = 0.0):
        """
        Add a position to the portfolio using the TickerRiskCalculations class.
        """
        return "pass"
    
    def _register_cro_tools(self):
        """
        Register the tools for the CRO agent.
        """

        self.add_tool(
            name="get_cio_choices",
            description="Get the choices from the ticker choices from the CIO agent. You will receive a dictionary of ticker_name: {position, industry, risk_allocation, reasoning}. THIS TAKES NO PARAMETERS.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: self._get_cio_choices()
        )

        self.add_tool(
            name="stress_test",
            description="Run an extensive stress test in the portfolio construction from the CIO agent. THIS TAKES NO PARAMETERS.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: run_stress_test_workflow()
        )

    
if __name__ == "__main__":
    agent = CROAgent()
    agent.run()

