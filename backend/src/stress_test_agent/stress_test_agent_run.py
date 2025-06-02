import json
import openai
from .stress_test_agent_class import StressTestAgent
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
import numpy as np
import math
from functools import lru_cache
from .tools.tool_registry import register_tools

# Load environment variables from .env file
load_dotenv()

# Create a ReactAgent
agent = StressTestAgent(llm="gpt-4.1-2025-04-14", api_key=os.environ.get("OPENAI_API_KEY"), max_iterations=100)

# Register all tools with the agent
register_tools(agent)

prompt = """
{
  "task": "Identify the weakest holding in my portfolio under stress",
  "tickers": the tickers returned by get_tickers() tool,
  "crisis_windows": [
    {"name":"SVB Shock","start":"2023-03-08","end":"2023-03-15"},
    {"name":"Downgrade Shock","start":"2023-07-29","end":"2023-08-02"},
    {"name":"Fed Raises Rates by 25bps May 2022","start":"2022-05-05","end":"2022-05-10"},
    {"name":"Fed Raises Rates by 75bps June 2022","start":"2022-06-14","end":"2022-06-20"},
    {"name":"Fed Raises Rates by 75bps September 2022","start":"2022-09-20","end":"2022-09-30"}
  ],
  "patterns_to_look_for": [
    "Large volume spikes accompanying price drops",
    "Stock prices dropping and not recovering quickly",
    "Massive sell offs indicated by volume during downturns"
  ],
  "schema": {
    "type":"object",
    "properties":{
      "weakest_ticker":{"type":"string"},
      "drivers":{"type":"array","items":{"type":"string"}}
    },
    "required":["weakest_ticker","drivers"]
  },
  "instructions":[
    "Call get_tickers() first to confirm the list of tickers.",
    "DO the following analysis FOR EACH crisis window defined in 'crisis_windows'.",
    "  - Call calculate_stock_metrics(start_date_str=window_start, end_date_str=window_end) to get metrics for all tickers in the window.",
    "  - Call get_portfolio_returns(start_date_str=window_start, end_date_str=window_end) to get the overall portfolio return in the window.",
    "  - Identify the top 2 tickers with the highest max_drawdown and the ticker with the highest annualized_volatility during the window. Note these as potential weak performers.",
    "  - Compare the max_drawdown of these potential weak performers to the portfolio's overall minimum cumulative return during the same period.",
    "  - FOR EACH potential weak performer identified above: Call get_stock_data(ticker, start_date_str=window_start, end_date_str=window_end) for a deeper analysis.",
    "  - In the deep dive, look specifically for the patterns defined in 'patterns_to_look_for'. Note if these patterns are present.",
    "Synthesize the findings across ALL crisis windows.",
    "Determine the overall weakest ticker based on consistent underperformance (high drawdown/volatility), poor comparison to portfolio returns, and presence of negative patterns ('patterns_to_look_for') across windows.",
    "Provide the 'drivers' for identifying the weakest ticker, linking them back to the specific metrics and patterns observed.",
    "ANSWER THIS QUESTION: Based on the OBSERVED behavior (drawdown, volatility, recovery patterns) during the analyzed crisis windows, what would you predict happen to my portfolio, focusing on the weakest ticker, if there was another SVB Crash?"
  ],
  "important_notes": [
    "You have unlimited iterations to get the best answer. You can call the tools as many times as you want."
  ]
}
"""

result = agent.run(prompt)

print("\n=== AGENT RESPONSE ===\n")
print(result) 
