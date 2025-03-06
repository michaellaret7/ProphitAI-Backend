import openai
import pandas as pd
import numpy as np
from openai import OpenAI
from ib_insync import IB, Stock, Future, ContFuture, Option, MarketOrder, StopOrder, LimitOrder
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

    for port in [7497, 4002]:
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

# ---------------------------------------------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------------------------------------------

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

def format_portfolio_grid(df):
    """
    Format portfolio data as a horizontal grid with key metrics.
    
    Args:
        df: Portfolio DataFrame
        
    Returns:
        str: Formatted grid as string
    """
    if df.empty:
        return "No positions in portfolio."
        
    # Select and rename the most important columns
    if 'symbol' in df.columns and 'position' in df.columns:
        display_df = df[['symbol', 'position', 'marketPrice', 'marketValue', 'averageCost', 'unrealizedPNL']]
        
        # Format numeric columns and create a new clean dataframe
        formatted_data = []
        for _, row in display_df.iterrows():
            # Format numeric values with commas for thousands
            shares = int(row['position'])
            price = row['marketPrice']
            value = row['marketValue']
            cost = row['averageCost']
            pnl = row['unrealizedPNL']
            
            formatted_row = {
                'Symbol': row['symbol'],
                'Shares': f"{shares:,}",
                'Price': f"${price:,.2f}",
                'Value': f"${value:,.2f}",
                'Cost': f"${cost:,.2f}",
                # Format P/L with sign before the dollar sign
                'P/L': f"-${abs(pnl):,.2f}" if pnl < 0 else f"+${pnl:,.2f}"
            }
            formatted_data.append(formatted_row)
            
        # Create a new DataFrame with the formatted data
        clean_df = pd.DataFrame(formatted_data)
        
        # Sort by value (descending)
        # Extract numeric value from the Value column for sorting
        clean_df['SortValue'] = display_df['marketValue']
        clean_df = clean_df.sort_values(by='SortValue', ascending=False)
        clean_df = clean_df.drop('SortValue', axis=1)
        
        # Force the output to be printed as a fixed-width grid without code block markers
        result = "PORTFOLIO HOLDINGS\n\n"
        
        # Calculate column widths based on the longest value in each column
        col_widths = {}
        for col in clean_df.columns:
            # Use exact width of the longest item in the column
            col_widths[col] = max(len(col), clean_df[col].astype(str).map(len).max())
            
        # Add header row with pipes
        result += "| "
        for col in clean_df.columns:
            result += col.ljust(col_widths[col]) + " | "
        result += "\n"
        
        # Add separator row
        result += "|"
        for col in clean_df.columns:
            result += "-" * (col_widths[col] + 2) + "|"
        result += "\n"
        
        # Add data rows
        for _, row in clean_df.iterrows():
            result += "| "
            for col in clean_df.columns:
                value = str(row[col])
                # Right-align numeric columns, left-align text
                if col == 'Symbol':
                    result += value.ljust(col_widths[col]) + " | "
                else:
                    result += value.rjust(col_widths[col]) + " | "
            result += "\n"
            
        return result
    else:
        return df.to_string()

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
    
    # Set GTC for all orders
    for order in parent:
        order.tif = 'GTC'
    
    # Set transmission flags properly for a bracket
    parent[0].transmit = False  # Parent order doesn't transmit yet
    parent[1].transmit = False  # Take profit doesn't transmit yet
    parent[2].transmit = True   # Stop loss transmits all orders
    
    # Place all orders
    trades = []
    for order in parent:
        trade = ib.placeOrder(contract, order)
        trades.append(trade)
        ib.sleep(0.1)  # Small delay between order submissions
    
    # Wait for order acknowledgement
    for trade in trades:
        print(f"Order {trade.order.orderId} status: {trade.orderStatus.status}")
    
    print("✅ Order submitted successfully!")
    ib.disconnect()
    return parent[0]  # Return the parent order

def name_to_ticker(company_name):
    """
    Convert company name to ticker symbol using OpenAI.
    
    Args:
        company_name (str): Company name or approximate ticker
        
    Returns:
        str: Ticker symbol
    """
    # If input already looks like a ticker (all caps, 1-5 chars), return it
    if company_name.isupper() and 1 <= len(company_name) <= 5:
        return company_name
    
    # Use OpenAI to identify the ticker
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial assistant that converts company names to their stock ticker symbols. Respond ONLY with the ticker symbol in uppercase, nothing else."
                },
                {
                    "role": "user",
                    "content": f"What is the stock ticker symbol for {company_name}?"
                }
            ],
            temperature=0,
            max_tokens=10
        )
        
        ticker = response.choices[0].message.content.strip().upper()
        
        # Verify it looks like a ticker (1-5 characters, all caps)
        if ticker and len(ticker) <= 5 and ticker.isalpha():
            print(f"Converted '{company_name}' to ticker symbol: {ticker}")
            return ticker
    except Exception as e:
        print(f"Error getting ticker from OpenAI: {e}")
    
    # Fallback to yfinance if OpenAI fails
    try:
        ticker = yf.Ticker(company_name)
        info = ticker.info
        if 'symbol' in info:
            return info['symbol'].upper()
    except:
        pass
    
    # Last resort: return uppercase input
    print(f"Could not find ticker for '{company_name}', using as-is")
    return company_name.upper()

def prompt_long_buy_order(symbol):
    """
    Interactive user flow for long buy orders. Prompts user for required parameters,
    confirms the order details, and places the order if confirmed.
    
    Args:
        symbol (str): The stock symbol to buy
        
    Returns:
        dict: Result of the order or None if canceled
    """
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    print(f"\n--- Long Buy Order for {ticker} ---")
    
    # Prompt for each parameter one at a time with clear instructions
    print("\nPlease enter the following details one by one:")
    
    # Get quantity
    while True:
        quantity = input("📦 How many shares: ")
        try:
            quantity = int(quantity)
            if quantity > 0:
                break
            else:
                print("Quantity must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get entry price
    while True:
        entry_price = input("💲 Entry price: ")
        try:
            entry_price = float(entry_price)
            if entry_price > 0:
                break
            else:
                print("Price must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Get stop loss
    while True:
        stop_loss = input("🛑 Stop loss: ")
        try:
            stop_loss = float(stop_loss)
            if stop_loss > 0:
                break
            else:
                print("Stop loss must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Get take profit
    while True:
        take_profit = input("🎯 Take profit: ")
        try:
            take_profit = float(take_profit)
            if take_profit > 0:
                break
            else:
                print("Take profit must be positive. Please try again.")
        except ValueError:
            print("Please enter a valid price.")
    
    # Confirm order details
    print(f"\nJust to confirm, you want to buy {quantity} shares of {ticker} at ${entry_price:.2f} with a stop loss of ${stop_loss:.2f} and a take profit of ${take_profit:.2f}")
    confirmation = input("Confirm order (y/n): ").lower()
    
    if confirmation == 'y' or confirmation == 'yes':
        # Place the order
        result = place_bracket_order_long(ticker, quantity, entry_price, take_profit, stop_loss)
        print(f"✅ Order submitted successfully!")
        return result
    else:
        print("Order cancelled.")
        return None

def exit_position(symbol):
    """
    Exits a position by selling all shares of the specified stock at market price.
    
    Args:
        symbol (str): The stock symbol to sell
        
    Returns:
        dict: Result of the order or None if no position found/order failed
    """
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    # Connect to IB
    ib = connect_to_ib()
    
    # Get portfolio data
    portfolio = ib.portfolio()
    
    # Find position for the specified symbol
    position_found = False
    for position in portfolio:
        if position.contract.symbol == ticker:
            position_found = True
            quantity = abs(position.position)
            
            if quantity <= 0:
                print(f"No position found for {ticker}.")
                ib.disconnect()
                return None
                
            print(f"Found position: {quantity} shares of {ticker}")
            
            # Create contract
            contract = Stock(ticker, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            
            # Create market sell order
            sell_order = MarketOrder('SELL', quantity)
            sell_order.tif = 'GTC'
            
            # Place the order
            trade = ib.placeOrder(contract, sell_order)
            print(f"Market sell order placed for {quantity} shares of {ticker}")
            
            # Wait for order to be acknowledged
            while trade.orderStatus.status == 'PendingSubmit':
                ib.sleep(0.1)
                
            print(f"Order status: {trade.orderStatus.status}")
            
            ib.disconnect()
            return trade
    
    if not position_found:
        print(f"No position found for {ticker}.")
        ib.disconnect()
        return None

def prompt_exit_position(symbol):
    """
    Interactive user flow for exiting positions. Prompts user to confirm
    selling all shares of the specified stock at market price.
    
    Args:
        symbol (str): The stock symbol to sell
        
    Returns:
        dict: Result of the order or None if canceled/no position
    """
    # Convert company name to ticker if needed
    ticker = name_to_ticker(symbol)
    
    print(f"\n--- Exit Position for {ticker} ---")
    
    # Connect to IB to get position info
    ib = connect_to_ib()
    portfolio = ib.portfolio()
    ib.disconnect()
    
    # Find position for the specified symbol
    position_found = False
    for position in portfolio:
        if position.contract.symbol == ticker:
            position_found = True
            quantity = abs(position.position)
            market_value = position.marketValue
            market_price = position.marketPrice
            
            if quantity <= 0:
                print(f"No position found for {ticker}.")
                return None
            
            # Display position details
            print(f"\nCurrent position:")
            print(f"Symbol: {ticker}")
            print(f"Quantity: {quantity} shares")
            print(f"Current price: ${market_price:.2f}")
            print(f"Market value: ${market_value:.2f}")
            
            # Confirm exit
            confirmation = input(f"\nAre you sure you want to sell all {quantity} shares of {ticker} at market price? (y/n): ").lower()
            
            if confirmation == 'y' or confirmation == 'yes':
                print(f"\nPlacing market sell order for {quantity} shares of {ticker}...")
                result = exit_position(ticker)
                if result:
                    print(f"✅ Exit order submitted successfully!")
                return result
            else:
                print("Order cancelled.")
                return None
    
    if not position_found:
        print(f"No position found for {ticker}.")
        return None

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
        
        Activate for ANY stock purchase expressions:
        - General: "buy a stock", "purchase stock", "invest in", "want to buy", "add to portfolio"
        - Specific: "buy", "go long", "long", "purchase", "enter position", "initiate position"
        - Action: "place an order", "execute trade", "make a purchase"
        - With stock: "buy shares of", "invest in", "purchase some"
        
        Trigger this for both general buying statements AND specific purchase requests.
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
},
{
    "type": "function",
    "function": {
        "name": "prompt_exit_position",
        "description": """
        Exit/sell an existing position in a specified stock at market price.
        
        Activate for ANY selling/exit expressions:
        - General: "exit position", "sell my shares", "close position", "liquidate position", "get out of", "exit my position", "close my position", "sell my position", "sell my shares of", "exit my position in", "close out of", "get out of my position in", "exit {stock name}", "close {stock name}", "sell {stock name}", "sell my shares of {stock name}", "exit my position in {stock name}", "close out of {stock name}", "get out of my position in {stock name}"
        - Specific: "sell", "exit", "close", "dump", "get rid of", "unload"
        - Action: "sell all shares", "exit my position", "close my position"
        - With stock: "sell my shares of", "exit my position in", "close out of", "get out of my position in"
        
        Trigger this whenever the user wants to sell or exit a position in a stock.
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The stock symbol to exit/sell"}
            },
            "required": ["symbol"],
            "additionalProperties": False
        }
    }
}]

# Initialize conversation history with system prompt
messages = [
    {
        "role": "system",
        "content": "You are an expert portfolio manager specializing in stocks and overseeing my portfolio. You can retrieve portfolio data, place trades, or exit positions when requested, but you can also answer general questions without taking any action. IMPORTANT: When a user expresses intent to buy a stock (e.g., 'I want to buy Apple'), IMMEDIATELY use the place_bracket_order_long tool with just the stock symbol - do NOT ask for additional details first. Similarly, when a user expresses intent to sell a stock (e.g., 'I want to exit my Amazon position'), IMMEDIATELY use the prompt_exit_position tool with just the stock symbol."
    }
]

# Main interaction loop
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

