import openai
import pandas as pd
import numpy as np
from openai import OpenAI
import yfinance as yf
from datetime import datetime, timedelta, date
import json
from typing import List, Dict, Optional
import os
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
from backend.src.utils.ticker_utils import name_to_ticker
from backend.src.prophitai_gpt.functionSchemas.tools import tools
from backend.src.prophitai_gpt.dataRetrievalTools.retrieve_financial_metrics import retrieve_financial_metric
from backend.src.utils.formatting import strip_formatting
from backend.src.utils.retrieve_portfolio_from_db import retrieve_user_current_portfolio

load_dotenv()

grok_api_key = os.getenv("GROK_API_KEY")
grok_model = os.getenv("GROK_MODEL")

model = grok_model

client = OpenAI(
  api_key=grok_api_key,
  base_url="https://api.x.ai/v1",
)

messages = [
    {
        "role": "system",
        "content": """
        Role: You are an expert portfolio manager, specializing in all things trading and investing.
        
        Follow the Thought → Action → Observation loop internally:
        1. Thought: brief reasoning.
        2. Action: call ONE tool exactly like  
        Action: tool_name(param=value, …)
        3. PAUSE 
        4. Observation: reflect on the tool result.

        IMPORTANT: 
        - if the user proceeds with a question (e.g. what should I buy?) do not initiate any order placing tools
        """
    }
]

# Main interaction loop
try:
    while True:
        user_input = input("🤖 Enter your prompt here: ")
        messages.append({"role": "user", "content": user_input})
        
        # Inner loop to handle tool calls and responses
        while True:
            # Normal flow using the model
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"  # Let the model decide whether to use a tool
            )
            
            response = completion.choices[0].message
            messages.append(response)  # Add the model's response to history
            
            if response.tool_calls:
                # Handle each tool call
                for tool_call in response.tool_calls:
                    tool_function_name = tool_call.function.name
                    tool_call_id = tool_call.id
                    args = json.loads(tool_call.function.arguments)

                    if tool_function_name == "get_portfolio_data":
                        user_name_from_model = args.get('user_name')
                        user_name = "test_user_beta" # Hardcoded for testing purposes
                        # print(f"[Testing Override] 'get_portfolio_data' called. Model sent user_name: '{user_name_from_model}'. Using hardcoded user_name: '{user_name}'")

                        if not user_name: # Should not happen with hardcoding, but good for robustness if hardcoding is removed
                            result_str = "Error: 'user_name' was not provided or is empty."
                        else:
                            portfolio_df = retrieve_user_current_portfolio(identifier=user_name, identifier_type="name")
                            if portfolio_df is None:
                                result_str = "Error: Portfolio data could not be retrieved."
                            elif portfolio_df.empty:
                                result_str = f"No portfolio data found for user '{user_name}'."
                            else:
                                # Convert DataFrame directly to string for the LLM
                                result_str = portfolio_df.to_string()
                        
                        # No strip_formatting needed here for portfolio data if LLM handles it
                        
                        messages.append({
                            "role": "tool",
                            "content": "Here is the user's portfolio data. Please format and display it appropriately:\n\n" + result_str,
                            "tool_call_id": tool_call_id
                        })
                    elif tool_function_name == "retrieve_financial_metric":
                        ticker = args.get('ticker')
                        metric_name = args.get('metric_name')

                        # Convert company name to ticker if needed
                        potential_ticker = name_to_ticker(ticker)
                        if potential_ticker:
                            ticker = potential_ticker
                        # else: # No explicit print if ticker not found, rely on function to handle
                            # # print(f"Could not find ticker for {ticker}, attempting with original input.")
                            
                        if not metric_name:
                            result_str = "Error: Metric name was not provided."
                        else:
                            metric_data = retrieve_financial_metric(ticker, metric_name)
                            
                            if metric_data:
                                # Format the data for the model
                                result_str = f"Historical {metric_name} for {ticker}:\n"
                                for date_val, val in metric_data:
                                    date_str = str(date_val) if date_val else "N/A"
                                    result_str += f"  Date: {date_str}, {metric_name}: {val:.2f}\n"
                            elif metric_data == []: # Empty list means no data found
                                result_str = f"No historical data found for metric '{metric_name}' for ticker '{ticker}'."
                            else: # None means an error occurred
                                result_str = f"Could not retrieve data for metric '{metric_name}' for ticker '{ticker}'. This could be due to an invalid ticker, metric name, or a database issue. Check logs for details."

                            result_str = strip_formatting(result_str)
                        messages.append({
                            "role": "tool",
                            "content": result_str,
                            "tool_call_id": tool_call_id
                        })
                # After tool calls are processed, loop back to let the model respond
            else:
                # No tool calls: print the response and strip formatting before displaying
                print(strip_formatting(response.content))
                break
finally:
    pass

