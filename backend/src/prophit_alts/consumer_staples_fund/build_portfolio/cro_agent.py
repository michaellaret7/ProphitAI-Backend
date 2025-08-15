from backend.src.agentic_framework.base_agent.agent import BaseAgent
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cro_temp_tools import *
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
        super().__init__(system_prompt, user_prompt, max_iterations=75, save_messages=True, model="gpt-5", verbose=True)
        
        self._register_cro_tools()

    def run(self):
        result = super().run()

        print(type(result))
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

    def _register_cro_tools(self):
        """
        Register the tools for the CRO agent.
        """

        self.add_tool(
            name="stress_test",
            description="Run an extensive stress test on the provided portfolio.",
            parameters={
                "type": "object",
                "properties": {
                    "portfolio_dict": {
                        "type": "object",
                        "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values"
                    }
                },
                "required": ["portfolio_dict"]
            },
            function=lambda portfolio_dict: run_stress_test_workflow(portfolio_dict)
        )
        
        self.add_tool(
            name="get_larger_ticker_pool",
            description="Get the larger pool of tickers from the CIO agent's original selection. Use this when you need alternative tickers to substitute or add to the portfolio. Returns a dictionary of ticker_name: {position, industry, risk_allocation, reasoning}. THIS TAKES NO PARAMETERS.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: self._get_larger_ticker_pool()
        )

        self.add_tool(
            name="get_upside_downside_ratios",
            description="Get the upside capture and downside capture ratios for the portfolio.",
            parameters={
                "type": "object",
                "properties": {
                    "portfolio_dict": {
                        "type": "object",
                        "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values"
                    }
                },
                "required": ["portfolio_dict"]
            },
            function=lambda portfolio_dict: get_upside_downside_ratios(portfolio_dict)
        )

        self.add_tool(
            name="get_all_factor_calculations",
            description="Get all factor calculations for a ticker. This is good for fundamental analysis on a single ticker.",
            parameters={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string", 
                        "description": "The ticker symbol you want to get factor calculations for"
                    }
                },
                "required": ["ticker"]
            },
            function=lambda ticker: get_all_factor_calculations(ticker)
        )

        self.add_tool(
            name="get_ticker_performance_metrics",
            description="Get performance metrics for a ticker. This is good for technical analysis on a single ticker.",
            parameters={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string", 
                        "description": "The ticker symbol you want to get performance metrics for"
                    }
                },
                "required": ["ticker"]
            },
            function=lambda ticker: get_ticker_performance_metrics(ticker)
        )

        self.add_tool(
            name="get_most_recent_fundamentals",
            description="Get the most recent fundamentals for a ticker. This is good for fundamental analysis on a single ticker.",
            parameters={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string", 
                        "description": "The ticker symbol you want to get the most recent fundamentals for"
                    },
                    "fundamentals_type": {
                        "type": "string", 
                        "description": "The type of fundamentals you want to get. Options are: ['balance_sheet', 'income_statement', 'cash_flow_statement', 'financial_ratios', 'analyst_estimates', 'all']"
                    }
                },
                "required": ["ticker", "fundamentals_type"]
            },
            function=lambda ticker, fundamentals_type: get_most_recent_fundamentals(ticker, fundamentals_type)
        )

        self.add_tool(
            name="analyze_portfolio_performance",
            description="Analyze the performance of the portfolio. This is good for portfolio level analysis.",
            parameters={
                "type": "object",
                "properties": {
                    "portfolio_dict": {
                        "type": "object",
                        "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values. Follow the <Dictionary Format Rules> from the prompt for this format."
                    }
                },
                "required": ["portfolio_dict"]
            },
            function=lambda portfolio_dict: analyze_portfolio_performance(portfolio_dict)
        )

        self.add_tool(
            name="get_initial_portfolio",
            description="Get the initial portfolio from the CIO agent.",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            function=lambda: self._get_initial_portfolio()
        )
    
    def _get_initial_portfolio(self):
        """
        Get the initial portfolio from the CIO agent.
        """
        initial_portfolio = {
            # Long positions
            "CASY": {"conviction": 0.10, "position": "long"},
            "CELH": {"conviction": 0.10, "position": "long"},
            "ODC": {"conviction": 0.05, "position": "long"},
            "ODD": {"conviction": 0.05, "position": "long"},
            "PM": {"conviction": 0.05, "position": "long"},
            "VITL": {"conviction": 0.05, "position": "long"},
            "WMT": {"conviction": 0.05, "position": "long"},
            "BJ": {"conviction": 0.05, "position": "long"},
            "SFM": {"conviction": 0.05, "position": "long"},
            "COCO": {"conviction": 0.05, "position": "long"},
            "MNST": {"conviction": 0.05, "position": "long"},
            "CL": {"conviction": 0.05, "position": "long"},
            "IPAR": {"conviction": 0.05, "position": "long"},
            "TPB": {"conviction": 0.05, "position": "long"},
            "DOLE": {"conviction": 0.05, "position": "long"},
            "PPC": {"conviction": 0.05, "position": "long"},
            "INGR": {"conviction": 0.05, "position": "long"},
            # Short positions
            "WBA": {"conviction": 0.05, "position": "short"},
            "ANDE": {"conviction": 0.05, "position": "short"},
            "TGT": {"conviction": 0.02, "position": "short"},
            "STZ": {"conviction": 0.05, "position": "short"},
            "PEP": {"conviction": 0.05, "position": "short"},
            "SAM": {"conviction": 0.05, "position": "short"},
            "MGPI": {"conviction": 0.05, "position": "short"},
            "ENR": {"conviction": 0.05, "position": "short"},
            "SPB": {"conviction": 0.05, "position": "short"},
            "COTY": {"conviction": 0.05, "position": "short"},
            "KVUE": {"conviction": 0.05, "position": "short"},
            "KLG": {"conviction": 0.05, "position": "short"},
            "JJSF": {"conviction": 0.05, "position": "short"},
            "SEB": {"conviction": 0.05, "position": "short"}
        }

        return initial_portfolio

    def _get_larger_ticker_pool(self):
        """
        Get the larger pool of tickers from the CIO agent's original selection.
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

if __name__ == "__main__":
    agent = CROAgent()
    result = agent.run()

    print("="*100)
    print("CRO Agent Result:")
    print("="*100)
    print(result)



