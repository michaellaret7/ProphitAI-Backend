from app.utils.choose_model_and_client import openai_model_and_client
from app.core.agentic_framework.tool_lib.agent_specific_tools.optimizer import get_user_portfolio

def build_portfolio_summary() -> str:
    model, client = openai_model_and_client('gpt-5')
    
    system_prompt = """
Role: Act as a portfolio analyst who specializes in writing in depth reports on portfolios and providing guidance on how to improve the portfolio.

Context: You will be given a portfolio from the given user.

Task: 
- Analyze the users portfolio and return the following analysis:
    - Strengths of the portfolio.
        --> Specific strong points of the portfolio with strong outlook
    - Weaknesses of the portfolio.
        --> Specific weaknesses of the portfolio with weak outlook
    - High risk low return tickers
    - Important note: When suggesting a ticker to remove, make sure to give a reason for the removal and a suggestion of the criteria that the new ticker should meet.
    - Return the analysis in a detailed report format.
"""

    user_prompt = f"""
Analyze the following portfolio:
{get_user_portfolio()}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    completions = client.chat.completions.create(
        model=model,
        messages=messages
    )

    return completions.choices[0].message.content


if __name__ == "__main__":
    print(build_portfolio_summary())