import openai
import pandas as pd
import numpy as np
from openai import OpenAI
from ib_insync import Stock, Future, ContFuture, Option, MarketOrder, StopOrder, LimitOrder
import yfinance as yf
from datetime import datetime, timedelta, date
import json
import time
from typing import List, Dict
import calendar
import random
import os
import base64
from PIL import Image
import pandas as pd
import io
import sys
from pathlib import Path
from huggingface_hub import InferenceApi
from huggingface_hub import InferenceClient
from sklearn.linear_model import LinearRegression
from ib_insync import Stock, Option, Future, ContFuture, IB
import os
from dotenv import load_dotenv
from src.prophitaiGPT.dataRetrievalTools.portfolioData import get_portfolio_data, format_portfolio_grid
from src.utils.ticker_utils import name_to_ticker
from src.prophitaiGPT.placeOrders.exitPosition import prompt_exit_position, exit_position
from src.utils.ib_utils import connect_to_ib, disconnect_from_ib, get_ib
from src.prophitaiGPT.placeOrders.longOrder import prompt_long_buy_order, place_bracket_order_long
from src.prophitaiGPT.functionSchemas.tools import tools    

load_dotenv()

OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL")

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
        "content": """You are an expert portfolio manager specializing in stocks and overseeing my portfolio. 
        You can retrieve portfolio data, place trades, or exit positions when requested, but you can also answer general questions without taking any action. 
        IMPORTANT: When a user expresses intent to buy a stock (e.g., 'I want to buy Apple'), IMMEDIATELY use the place_bracket_order_long tool with just the stock symbol - do NOT ask for additional details first. 
        Similarly, when a user expresses intent to sell a stock (e.g., 'I want to exit my Amazon position'), IMMEDIATELY use the prompt_exit_position tool with just the stock symbol."""
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
                    # After tool calls are processed, loop back to let the model respond
                else:
                    # No tool calls: print the response and exit the inner loop
                    print(response.content)
                    break
finally:
    # Make sure to disconnect when the program exits
    disconnect_from_ib()

