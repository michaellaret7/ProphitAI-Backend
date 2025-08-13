from datetime import timedelta
from backend.src.agentic_framework.base_agent.agent import BaseAgent
from backend.src.calculations.risk_calculations.ticker_risk_calculations import TickerRiskCalculations
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.stress_test.runner import run_stress_test_workflow
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers
from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.prompts.cro_agent_prompts import cro_system_prompt, cro_user_prompt
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import get_upside_downside_ratios
from pydantic import BaseModel
from typing import List, Literal
import json

class CROPortfolioItem(BaseModel):
	ticker: str
	position: Literal["long", "short"]
	weight: float
	reason: str

class FinalPortfolio(BaseModel):
	portfolio: List[CROPortfolioItem]
# model="gpt-5-2025-08-07"
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
        
        #This tool gives the model the original pool of tickers from the CIO agent, use this to get the ticker choices
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



