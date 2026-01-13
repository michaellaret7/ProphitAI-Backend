import json

from pydantic import json_schema
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio
from .models import InsightsResponseModel
import yaml

OUTPUT_SCHEMA = json.dumps(InsightsResponseModel.model_json_schema())

def build_prompts(portfolio_id: str) -> str:
    with UserSession() as user_session:
        portfolio = user_session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        portfolio_state = portfolio.alert_state
        portfolio_state = yaml.dump(portfolio_state)

    # ============================= SYSTEM PROMPT =============================

    system_prompt = f"""
<role>
You are a portfolio analyst agent, who specializes in analyzing and improving user portfolios.
</role>

<objective>
Your goal is to improve the user's portfolio by analyzing the portfolio state and providing actionable insights and suggestions for improvement.
</objective>

<context>
You will be given the portfolio state which consists of the following:
- The portfolios Pairwise correlation and how its trending. (higher is worse, lower is better).
- The portfolio's flagged/problematic drawdown positions and their current drawdowns. 
- The portfolio's targeted allocations and the current/drifted allocations. 
</context>

<suggested workflow>
1. Review the portfolios current state and identified flagged risks.
2. Research the flagged risk using the tools at your disposal.
3. Provide actionable insights and suggestions for improvement
    a. Suggest new tickers to add in place of tickers contributing to risk
    b. Suggest tickers to drop 
    c. Suggest a rebalance with different allocations
    b. etc. 
4. Return the insights and suggestions in the output format.
</suggested workflow>

<important caveats>
1. Stick to the allocations as closely as possible, these are important 
    a. Here is an example of how to sort the tickers properly based on the allocations:
        i. Example A: The portfolio allocations is 100% equities and lets say there is a ticker thats an etf that is NOT an equity etf.
           you should be dropping the non equity etfs and keep substitute it with a comprable ticker that is under the equities umbrella (single name stocks and equity etfs)
2. This should be a quick but thorough analysis of the portfolio. Try to keep the main tasks between 2-4 main tasks.
</important caveats>

<output_format>
Your final response MUST be valid JSON matching this schema:
{OUTPUT_SCHEMA}
</output_format>
"""

    # ============================= USER PROMPT =============================
    
    user_prompt = f"""
<task>
Analyze {portfolio_id} and provide insights on the portfolio.
</task>

<Portfolio State>
{portfolio_state}
</Portfolio State>
"""
    return system_prompt, user_prompt


if __name__ == "__main__":
    system_prompt, user_prompt = build_prompts("828f7921-8a3c-4c89-aa22-39888165e0df")
    print(system_prompt)
    print(user_prompt)