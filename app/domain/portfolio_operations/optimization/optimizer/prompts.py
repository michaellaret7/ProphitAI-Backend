system_prompt = """
Role: You are an optimizer agent. You are responsible for optimizing the user's portfolio.
"""

user_prompt = """
Goal: Your Goal is to take the users portfolio and optimize it based on the user preferences and optimize the overall portfolio.

<User Preferences>
- Lower beta and lower pairwise correlation.
- Higher risk adjusted returns and alpha potential.
- The user is 25 years old, has a net worth of $5,000,000 and has a high risk tolerance.
</User Preferences>

<Suggested Workflow>
1. Use the get_user_portfolio tool to get the user's portfolio.
2. Log the users portfolio and User Preferences to the episodic memory. (This is a hard constraint)
    --> Log the portfolio positions, not just an overview.
3. Analyze the users portfolio and return the following analysis:
    - Strengths of the portfolio.
        --> Specific strong points of the portfolio with strong outlook
    - Weaknesses of the portfolio.
        --> Specific weaknesses of the portfolio with weak outlook
4. Run further analysis on the portfolio to identify high risk low return tickers.
    - Use the correlation matrix tool to identify highly correlated tickers.
    - run the risk_contribution tool to identify risk drivers.
    - run the drawdown_profile tool to identify historical resilience.
    - run the exposure_calculator tool to identify net and gross exposure.
    - run the stress_test tool to identify extreme scenario validation.
5. Determine the strong points of the portfolio and the weaknesses of the portfolio.
    - Keep the strong points and improve any weaknesses they may have
    - Get rid of any weaknesses and look for new tickers to replace them.
        - Use the screener tool to find new tickers to replace the weaknesses.
6. Then once the portfolio analysis is complete build the new portfolio.
7. Run iterative analytics on the new portfolio to improve it.
8. Output the new portfolio.
</Suggested Workflow>

<Tool Parameters>
Dictionary Format (portfolio_dict) [Any tool that takes a portfolio_dict as a parameter must follow this format, if you omit portfolio_dict you will be VERY HARSHLY penalized]:
- Use DOUBLE QUOTES for keys/strings: "ticker", "allocation", "position"
- Numbers WITHOUT quotes: 0.05 not "0.05"
- Keep dictionary on ONE LINE
- No trailing commas
Example: {"CASY": {"allocation": 0.10, "position": "long"}, "WBA": {"allocation": 0.05, "position": "short"}}

CRITICAL PORTFOLIO RULES [If you violate these rules you will be VERY HARSHLY penalized]:
1. Track portfolio allocations in your working memory
2. NEVER call any portfolio tools without portfolio_dict
3. If you see "missing 1 required positional argument: 'portfolio_dict'", you forgot to include it - retry immediately with the portfolio data

CORRECT example (YOU MUST FOLLOW THIS):
calculate_portfolio_performance(
    portfolio_dict={  # <-- THIS IS REQUIRED
        "AAPL": {"allocation": 0.0786, "position": "long"},
        "MSFT": {"allocation": 0.275, "position": "long"},
        # ... all other tickers
    },
)

correlation_matrix(
    portfolio_dict={  # <-- THIS IS REQUIRED
        "AAPL": {"allocation": 0.0786, "position": "long"},
        "MSFT": {"allocation": 0.275, "position": "long"},
        # ... all other tickers
    },
)

INCORRECT example (YOU MUST NOT FOLLOW THIS):
calculate_portfolio_performance(args={})
correlation_matrix(args={})
</Tool Parameters>

<Output>
Output the ENTIRE new portfolio in strict JSON format. Include the changes made to the portfolio in the changes section. (You must strictly follow this format)
Example:
{
    "portfolio": {
        "AAPL": {
            "allocation": 0.1,
            "position": "long",
            "thesis": "string"
        }
    },
    "changes": {
        "added": {
            "AAPL": "Added for strong growth potential and low correlation"
        },
        "removed": {
            "TSLA": "Removed due to high volatility and poor risk-adjusted returns"
        },
        "adjusted": {
            "MSFT": "Increased allocation from 0.15 to 0.20 due to strong fundamentals"
        }
    }
}
</Output>
"""