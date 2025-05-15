import openai
import pandas as pd
import numpy as np
from openai import OpenAI
from ib_insync import Stock, Future, ContFuture, Option, MarketOrder, StopOrder, LimitOrder
import yfinance as yf
from datetime import datetime, timedelta, date
import json
from typing import List, Dict
import os
from PIL import Image
import pandas as pd
from pathlib import Path
from ib_insync import Stock, Option, Future, ContFuture, IB
import os
from dotenv import load_dotenv
from src.prophitai_gpt.dataRetrievalTools.portfolioData import get_portfolio_data, format_portfolio_grid
from src.utils.ticker_utils import name_to_ticker
from src.prophitai_gpt.placeOrders.exitPosition import prompt_exit_position, exit_position
from src.utils.ib_utils import connect_to_ib, disconnect_from_ib
from src.prophitai_gpt.placeOrders.longOrder import prompt_long_buy_order, place_bracket_order_long
from src.prophitai_gpt.functionSchemas.tools import tools
from src.prophitai_gpt.dataRetrievalTools.retrieve_financial_metrics import retrieve_financial_metric
from src.utils.formatting import strip_formatting

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

# Connect to IB at startup
connect_to_ib()

# Main interaction loop
try:
    while True:
        user_input = input("🤖 Enter your prompt here: ")
        messages.append({"role": "user", "content": user_input})
        
        # Check for direct buy triggers
        buy_triggers = ["buy", "purchase", "invest in", "want to buy", "get some", "go long", "long", "buy long", "execute long position", "enter position", "initiate position", "set up a trade", "create an order", "place an order", "execute trade", "make a purchase", "buy shares of", "purchase some", "acquire stock in"]
        force_buy_tool = False
        stock_symbol = None
        
        # Simple buy intent detection
        user_input_lower = user_input.lower()
        if any(trigger in user_input_lower for trigger in buy_triggers):
            force_buy_tool = True
            # Try to extract stock symbol - simple approach
            words = user_input.replace(',', '').replace('.', '').split()
            for i, word in enumerate(words):
                if any(trigger in word.lower() for trigger in buy_triggers) and i < len(words) - 1:
                    # Assume the word after a buy trigger might be a stock name
                    stock_symbol = words[i+1]
                    break
        
        # Inner loop to handle tool calls and responses
        while True:
            if force_buy_tool and stock_symbol:
                # Skip the model and directly call prompt_long_buy_order
                print("I'll help you buy some shares. Let me get some details from you.")
                result = prompt_long_buy_order(stock_symbol)
                # Add a simulated response to keep conversation history consistent
                messages.append({
                    "role": "assistant",
                    "content": str(result) if result else "Order was cancelled."
                })
                break
            else:
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
                        if tool_call.function.name == "get_portfolio_data":
                            result = get_portfolio_data()
                            # Format as grid instead of basic string conversion
                            result_str = format_portfolio_grid(result)
                            result_str = strip_formatting(result_str)
                            
                            # Add a message to the AI to preserve the formatting
                            messages.append({
                                "role": "tool",
                                "content": "Here is your portfolio data in a tabular format. Please display it exactly as formatted below with its table structure intact:\n\n" + result_str,
                                "tool_call_id": tool_call.id
                            })
                        elif tool_call.function.name == "place_bracket_order_long":
                            args = json.loads(tool_call.function.arguments)
                            # Use the interactive prompt flow instead of direct function call
                            symbol = args.get('symbol')
                            result = prompt_long_buy_order(symbol)
                            messages.append({
                                "role": "tool",
                                "content": str(result) if result else "Order was cancelled.",
                                "tool_call_id": tool_call.id
                            })
                        elif tool_call.function.name == "prompt_exit_position":
                            args = json.loads(tool_call.function.arguments)
                            symbol = args.get('symbol')
                            result = prompt_exit_position(symbol)
                            messages.append({
                                "role": "tool",
                                "content": str(result) if result else "Order was cancelled.",
                                "tool_call_id": tool_call.id
                            })
                        elif tool_call.function.name == "retrieve_financial_metric":
                            args = json.loads(tool_call.function.arguments)
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
                                "tool_call_id": tool_call.id
                            })
                    # After tool calls are processed, loop back to let the model respond
                else:
                    # No tool calls: print the response and strip formatting before displaying
                    print(strip_formatting(response.content))
                    break
finally:
    # Make sure to disconnect when the program exits
    disconnect_from_ib()

