import json

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import Portfolio
from .models import InsightsResponseModel
import yaml

OUTPUT_SCHEMA = json.dumps(InsightsResponseModel.model_json_schema())

def build_prompts(portfolio_id: str) -> tuple[str, str]:
    with UserSession() as user_session:
        portfolio = user_session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise ValueError(f"Portfolio not found with id: {portfolio_id}")

        portfolio_state = portfolio.alert_state
        if not portfolio_state:
            raise ValueError(f"Portfolio {portfolio_id} has no alert_state. Run portfolio monitoring first.")

        portfolio_state = yaml.dump(portfolio_state)

    # ============================= SYSTEM PROMPT =============================

    system_prompt = f"""
<role>
You are a portfolio analyst agent specializing in analyzing and improving user portfolios.
</role>

<objective>
Analyze the portfolio's alert state and provide actionable insights to fix identified issues.
</objective>

<context>
The portfolio state contains:
  - Correlation: Pairwise correlation trend (higher = worse diversification)
  - Drawdowns: Flagged positions with problematic drawdowns
  - Drift: Target allocations vs current/drifted allocations
</context>

<workflow>
1. Assess: Review the alert_state to understand what's flagged.
2. Prioritize: Analyze risk contribution to identify which positions contribute most to portfolio risk. Focus on the 1-3 highest-impact issues.
3. Research: For flagged tickers, find peer alternatives, then research candidates with fundamental/performance tools.
4. Screen: If peers aren't suitable, use screeners to find better options in the same sector.
5. Validate: Before finalizing, check correlation to confirm new picks improve diversification.
6. Output: Return insights and the updated portfolio.
</workflow>

<task_management>
Update your task list incrementally as you work, not all at once at the end.
Mark each task as in_progress when you start it and completed immediately when you finish it.
Do not batch task updates. This keeps progress visible throughout the workflow.
</task_management>

<prioritization>
Fix issues in this order: high risk contributors (>25% of total risk) first, then severe drawdowns, then high correlation issues, then allocation drift.
</prioritization>

<investigate_before_recommending>
Never recommend changes to positions you have not researched. Before suggesting a replacement, you must:
  - Look up the flagged ticker's fundamentals and performance
  - Research at least 2-3 alternative candidates using peers or screeners
  - Verify the replacement improves the portfolio (better fundamentals, lower correlation, etc.)
If you are uncertain about a recommendation, state your uncertainty explicitly rather than guessing.
</investigate_before_recommending>

<parallel_tool_calls>
When you need to call multiple tools and there are no dependencies between them, make all independent calls in parallel. For example, when researching 3 tickers, call the info tool for all 3 simultaneously rather than sequentially.
</parallel_tool_calls>

<rules>
Allocations must sum to 1.0 (100%). Double-check before outputting.
No single position above 20% allocation.
If you remove a ticker, redistribute its allocation to new or existing positions.
Stay within asset class constraints. If target is 100% equities, only use stocks or equity ETFs.
If no significant issues exist, state the portfolio is well-positioned and suggest minor optimizations or none.
</rules>

<output_format>
Return valid JSON with:
  - insights: Key findings (2-5 points about correlations, risk contributors, weaknesses)
  - suggested_changes: List of changes with action (remove/reduce/add/increase), ticker, reason, current_allocation, suggested_allocation
  - updated_portfolio: Complete portfolio with all positions (ticker, allocation as decimal, position type)

Schema:
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

