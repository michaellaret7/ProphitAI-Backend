from backend.src.prophit_alts.core.base_agent_class import BaseAgent
# from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from backend.src.calculations.risk_calculations.ticker_risk_calculations import TickerRiskCalculations

cro_system_prompt = """
You are a Chief Risk Officer for a hedge fund. You are responsible for the risk management of the fund.
"""
cro_user_prompt = """
You are a Chief Risk Officer for a hedge fund. You are responsible for the risk management of the fund.
"""

class CROAgent(BaseAgent):
    def __init__(self, system_prompt: str = cro_system_prompt, user_prompt: str = cro_user_prompt):
        super().__init__(system_prompt, user_prompt)

    def run(self):
        return super().run()

    def get_cio_choices(self): #Add this in the prompt no need to use a tool for this 
        """
        Get the choices from the CIO agent.
        """
        return "pass"

    def get_original_pool_of_tickers(self):
        """
        Get the original pool of tickers minus the ones chosen by the CIO agent.
        """
        return "pass"
    
    def stress_test(self):
        """
        Stress test the portfolio.
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
        return "pass"
    


