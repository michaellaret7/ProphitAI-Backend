import openai
import pandas as pd
import numpy as np
from openai import OpenAI
from ib_insync import IB, Stock, Future, ContFuture, Option
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


OpenAI_API_KEY = "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"
ANTHROPIC_API_KEY = "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"
hf_token = "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"
grok_api_key = "xai-SRllgqCDKpTEPnjCdeoJABoKjO9vsyD3OXKvyiaPnuZNyjpx7CrntWrlw7vf3kFVo04NafIwWRnyqpeA"

# Initialize clients
client = OpenAI(
    api_key=OpenAI_API_KEY
)

def connect_to_ib():
    ib = IB()
    if ib.isConnected():
        ib.disconnect()

    connected = False

    for port in [7497]:
        for clientId in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=clientId)
                connected = True
                print(f"🌐 Connected successfully on port {port} with clientId {clientId}")
                break  # Break out of the clientId loop
            except Exception as e:
                print(f"🚨 Failed to connect on port {port} with clientId {clientId}: {e}")
                pass
        
        if connected:
            break  # Break out of the port loop if we're connected
    
    if not connected:
        print("⛔ Could not connect to IB on any port with any clientId")
        return None

    return ib

def get_portfolio_data():
    """
    Retrieves current portfolio positions and data from Interactive Brokers using IB Insync.
    
    Returns:
        pd.DataFrame: DataFrame containing portfolio positions and data
    """

    ib = connect_to_ib()
    
    # Get portfolio data
    portfolio = ib.portfolio()
    
    # Convert portfolio data to DataFrame
    portfolio_data = []
    for position in portfolio:
        data = {
            'symbol': position.contract.symbol,
            'secType': position.contract.secType,
            'exchange': position.contract.exchange,
            'currency': position.contract.currency,
            'position': position.position,
            'marketPrice': position.marketPrice,
            'marketValue': position.marketValue,
            'averageCost': position.averageCost,
            'unrealizedPNL': position.unrealizedPNL
        }
        portfolio_data.append(data)
    
    df = pd.DataFrame(portfolio_data)
    
    ib.disconnect()
    return df

def place_bracket_order_long(symbol, quantity, entry_price, take_profit_price, stop_loss_price):
    """
    Places a bracket order with a primary order, a take-profit order, and a stop-loss order.
    """
    ib = connect_to_ib()
    
    contract = Stock(symbol, 'SMART', 'USD')
    ib.qualifyContracts(contract)
    
    # Create the bracket order components
    parent = ib.bracketOrder(
        action='BUY',
        quantity=quantity,
        limitPrice=entry_price,
        takeProfitPrice=take_profit_price,
        stopLossPrice=stop_loss_price
    )
    
    # Submit all orders together

    for order in parent:
        order.tif = 'GTC'
        order.transmit = True

    for order in parent:
        trade = ib.placeOrder(contract, order)
        
        ib.sleep(0.1)  # Add small delay between orders
        
        # Wait for order to be acknowledged
        while trade.orderStatus.status == 'PendingSubmit':
            ib.sleep(0.1)
            
        print(f"Order {order.orderId} status: {trade.orderStatus.status}")
    
    ib.disconnect()
    return parent[0]  # Return the parent order

tools = [{
    "type": "function",
    "function": {
        "name": "get_portfolio_data",
        "description": """
        Retrieve current portfolio positions from Interactive Brokers.

        Examples:
        - Show my current portfolio holdings
        - What positions do I currently own?
        - Display my investment holdings
        - List active positions
        - Show portfolio breakdown
        - Current market positions
        - Portfolio status
        - Investment allocation
        - Open positions summary
        - Active trades overview
        """,
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "place_bracket_order_long",
        "description": """
        The user will give you a stock symbol, quantity, entry price, take profit price, and stop loss price.
        If the user does not give you a quantity, then the quantity is 100.
        If the user uses the name of the stock instead of the ticker symbol, then you must convert the name of the stock into its ticker symbol.
        If the user says 'buy', 'go long', 'long', 'buy long', 'buy the long', 'buy the long position', 'buy the long position of', 'buy the long position of 'stock_name'', purchase, etc. then enact this function.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The stock symbol of the data to push to excel"},
                "quantity": {"type": "number", "description": "The quantity of the stock to trade, this is in number of shares not dollar amount"},
                "entry_price": {"type": "number", "description": "The price at which to enter the position"},
                "take_profit_price": {"type": "number", "description": "The price at which to take profit"},
                "stop_loss_price": {"type": "number", "description": "The price at which to stop loss"}
            },
            "required": ["symbol", "quantity", "entry_price", "take_profit_price", "stop_loss_price"],
            "additionalProperties": False
        }
    }
}]

# Initialize conversation history with system prompt
messages = [
    {
        "role": "system",
        "content": "You are an expert portfolio manager specializing in stocks and overseeing my portfolio. You can retrieve portfolio data or place trades when requested, but you can also answer general questions without taking any action."
    }
]

# Main interaction loop
while True:
    user_input = input("🤖 Enter your prompt here: ")
    messages.append({"role": "user", "content": user_input})
    
    # Inner loop to handle tool calls and responses
    while True:
        completion = client.chat.completions.create(
            model="gpt-4o",
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
                    result_str = result.to_string()  # Convert DataFrame to string
                    messages.append({
                        "role": "tool",
                        "content": result_str,
                        "tool_call_id": tool_call.id
                    })
                elif tool_call.function.name == "place_bracket_order_long":
                    args = json.loads(tool_call.function.arguments)
                    result = place_bracket_order_long(**args)
                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call.id
                    })
            # After tool calls are processed, loop back to let the model respond
        else:
            # No tool calls: print the response and exit the inner loop
            print(response.content)
            break

