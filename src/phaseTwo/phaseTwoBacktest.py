from ib_insync import IB
from ib_insync import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

json = {
    "final_portfolio": [
         {
            "ticker": "VTI",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "15%",
            "market_value": "$15,000"
        },
        {
            "ticker": "QQQ",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "10%",
            "market_value": "$25,000"
        },
        {
            "ticker": "XLV",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "8%",
            "market_value": "$8,000"
        },
        {
            "ticker": "IEMG",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "7%",
            "market_value": "$18,000"
        },
        {
            "ticker": "LQD",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "10%",
            "market_value": "$10,000"
        },
        {
            "ticker": "IEI",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "10%",
            "market_value": "$20,000"
        },
        {
            "ticker": "TIP",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "5%",
            "market_value": "$10,000"
        },
        {
            "ticker": "EMB",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "10%",
            "market_value": "$10,000"
        },
        {
            "ticker": "GLD",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "4%",
            "market_value": "$10,000"
        },
        {
            "ticker": "GSG",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "3%",
            "market_value": "$7,000"
        },
        {
            "ticker": "VNQ",
            "position_type": "LONG",
            "shares": "N/A",
            "allocation": "3%",
            "market_value": "$3,000"
        },
        {
            "ticker": "Cash",
            "position_type": "CASH",
            "shares": "N/A",
            "allocation": "10%",
            "market_value": "$10,000"
        }
    ]
}

json2 = {
    "final_portfolio": [
        {
            "ticker": "AAL",
            "position_type": "LONG",
            "shares": "1000",
            "allocation": "10%",
            "market_value": "Varies"
        },
        {
            "ticker": "CEG",
            "position_type": "LONG",
            "shares": "300",
            "allocation": "8%",
            "market_value": "Varies"
        },
        {
            "ticker": "CTSH",
            "position_type": "LONG",
            "shares": "50",
            "allocation": "5%",
            "market_value": "Varies"
        },
        {
            "ticker": "GM",
            "position_type": "LONG",
            "shares": "100",
            "allocation": "7%",
            "market_value": "Varies"
        },
        {
            "ticker": "HYG",
            "position_type": "LONG",
            "shares": "50",
            "allocation": "4%",
            "market_value": "Varies"
        },
        {
            "ticker": "IBKR",
            "position_type": "LONG",
            "shares": "50",
            "allocation": "5%",
            "market_value": "Varies"
        },
        {
            "ticker": "SBUX",
            "position_type": "LONG",
            "shares": "100",
            "allocation": "7%",
            "market_value": "Varies"
        },
        {
            "ticker": "V",
            "position_type": "LONG",
            "shares": "150",
            "allocation": "10%",
            "market_value": "Varies"
        },
        {
            "ticker": "MRVL",
            "position_type": "LONG",
            "shares": "120",
            "allocation": "5%",
            "market_value": "New Position"
        },
        {
            "ticker": "ON",
            "position_type": "LONG",
            "shares": "150",
            "allocation": "5%",
            "market_value": "New Position"
        },
        {
            "ticker": "WELL",
            "position_type": "LONG",
            "shares": "100",
            "allocation": "7%",
            "market_value": "New Position"
        },
        {
            "ticker": "TAN",
            "position_type": "LONG",
            "shares": "200",
            "allocation": "8%",
            "market_value": "New Position"
        },
        {
            "ticker": "VGT",
            "position_type": "LONG",
            "shares": "75",
            "allocation": "6%",
            "market_value": "New Position"
        },
        {
            "ticker": "SPG",
            "position_type": "SHORT",
            "shares": "amount TBD",
            "allocation": "5%",
            "market_value": "New Position"
        }
    ]
}

json3 = {
    "final_portfolio": [
        {
            "ticker": "SBUX",
            "position_type": "LONG",
            "shares": 50,
            "allocation": "5%",
            "market_value": 4935.65
        },
        {
            "ticker": "WBA",
            "position_type": "LONG",
            "shares": 3000,
            "allocation": "10%",
            "market_value": 33540.00
        },
        {
            "ticker": "XLP",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "XLU",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "XLK",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "10%",
            "market_value": 96000.00
        },
        {
            "ticker": "VGT",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "FBT",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "IBB",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "ICLN",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "5%",
            "market_value": 48000.00
        },
        {
            "ticker": "XLF",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "10%",
            "market_value": 96000.00
        },
        {
            "ticker": "EEM",
            "position_type": "LONG",
            "shares": "-",
            "allocation": "15%",
            "market_value": 144000.00
        },
        {
            "ticker": "CASH",
            "position_type": "CASH",
            "shares": "-",
            "allocation": "10%",
            "market_value": 96977.81
        }
    ]
}

json4 = {
    "final_portfolio": [
        {
            "ticker": "SBUX",
            "position_type": "LONG",
            "shares": "100",
            "allocation": "7%"
    },
    {
        "ticker": "V",
        "position_type": "LONG", 
        "shares": "150",
        "allocation": "12%"
    },
    {
        "ticker": "AMD",
        "position_type": "LONG",
        "shares": "200", 
        "allocation": "9%"
    },
    {
        "ticker": "GOOGL",
        "position_type": "LONG",
        "shares": "150",
        "allocation": "11%"
    },
    {
        "ticker": "AMZN", 
        "position_type": "LONG",
        "shares": "100",
        "allocation": "10%"
    },
    {
        "ticker": "PLD",
        "position_type": "LONG",
        "shares": "200",
        "allocation": "12%"
    },
    {
        "ticker": "NEE",
        "position_type": "LONG",
        "shares": "150",
        "allocation": "9%"
    },
    {
        "ticker": "CEG",
        "position_type": "LONG",
        "shares": "237",
        "allocation": "8%"
    },
    {
        "ticker": "WBA",
        "position_type": "LONG",
        "shares": "4389",
        "allocation": "15%"
    },
    {
        "ticker": "CASH",
        "position_type": "CASH",
        "shares": "NA",
        "allocation": "7%"
        }
    ]
}

json5 = {
    "final_portfolio": [
        {
            "ticker": "AMD",
            "position_type": "LONG", 
            "shares": 100,
            "allocation": "10%"
        },
        {
            "ticker": "IYR",
            "position_type": "LONG",
            "shares": 200,
            "allocation": "12%"
        },
        {
            "ticker": "NIO",
            "position_type": "LONG",
            "shares": 150,
            "allocation": "8%"
        },
        {
            "ticker": "ENPH",
            "position_type": "LONG",
            "shares": 80,
            "allocation": "12%"
        },
        {
            "ticker": "F",
            "position_type": "LONG",
            "shares": 150,
            "allocation": "5%"
        },
        {
            "ticker": "CEG",
            "position_type": "LONG",
            "shares": 237,
            "allocation": "5%"
        },
        {
            "ticker": "GM",
            "position_type": "LONG",
            "shares": 100,
            "allocation": "3%"
        },
        {
            "ticker": "CTSH",
            "position_type": "LONG",
            "shares": 50,
            "allocation": "2%"
        },
        {
            "ticker": "HYG",
            "position_type": "LONG",
            "shares": 50,
            "allocation": "3%"
        },
        {
            "ticker": "IBKR",
            "position_type": "LONG",
            "shares": 50,
            "allocation": "5%"
        },
        {
            "ticker": "SONO",
            "position_type": "LONG",
            "shares": 100,
            "allocation": "1%"
        },
        {
            "ticker": "V",
            "position_type": "LONG",
            "shares": 70,
            "allocation": "10%"
        },
        {
            "ticker": "CASH",
            "position_type": "CASH",
            "shares": 0,
            "allocation": "10%"
        }
    ]
}

json6 = {
    "final_portfolio": [
        {
            "ticker": "AAPL",
            "position_type": "LONG", 
            "shares": "100",
            "allocation": "7%"
        },
        {
            "ticker": "MSFT",
            "position_type": "LONG",
            "shares": "80", 
            "allocation": "7%"
        },
        {
            "ticker": "JNJ",
            "position_type": "LONG",
            "shares": "50",
            "allocation": "6%"
        },
        {
            "ticker": "PG",
            "position_type": "LONG",
            "shares": "60",
            "allocation": "6%"
        },
        {
            "ticker": "XOM",
            "position_type": "LONG",
            "shares": "70",
            "allocation": "6%"
        },
        {
            "ticker": "JPM",
            "position_type": "LONG",
            "shares": "60",
            "allocation": "7%"
        },
        {
            "ticker": "NEE",
            "position_type": "LONG",
            "shares": "50",
            "allocation": "5%"
        },
        {
            "ticker": "AMZN",
            "position_type": "LONG",
            "shares": "40",
            "allocation": "6%"
        },
        {
            "ticker": "GOOG",
            "position_type": "LONG",
            "shares": "35",
            "allocation": "7%"
        },
        {
            "ticker": "CAT",
            "position_type": "LONG",
            "shares": "40",
            "allocation": "5%"
        },
        {
            "ticker": "LIN",
            "position_type": "LONG",
            "shares": "30",
            "allocation": "5%"
        },
        {
            "ticker": "PLD",
            "position_type": "LONG",
            "shares": "30",
            "allocation": "5%"
        },
        {
            "ticker": "T",
            "position_type": "LONG",
            "shares": "80",
            "allocation": "4%"
        },
        {
            "ticker": "MCD",
            "position_type": "LONG",
            "shares": "25",
            "allocation": "4%"
        },
        {
            "ticker": "ADBE",
            "position_type": "LONG",
            "shares": "25",
            "allocation": "5%"
        }
    ]
}

json7 = {
    "final_portfolio": [
        {"ticker": "CEG", "position_type": "LONG", "shares": "329", "allocation": "9%"},
        {"ticker": "CTSH", "position_type": "LONG", "shares": "785", "allocation": "8%"},
        {"ticker": "GM", "position_type": "LONG", "shares": "950", "allocation": "6%"},
        {"ticker": "HYG", "position_type": "LONG", "shares": "474", "allocation": "5%"},
        {"ticker": "IBKR", "position_type": "LONG", "shares": "524", "allocation": "12%"},
        {"ticker": "V", "position_type": "LONG", "shares": "217", "allocation": "10%"},
        {"ticker": "JPM", "position_type": "LONG", "shares": "373", "allocation": "7%"},
        {"ticker": "PG", "position_type": "LONG", "shares": "319", "allocation": "6%"},
        {"ticker": "CAT", "position_type": "LONG", "shares": "894", "allocation": "6%"},
        {"ticker": "AAPL", "position_type": "LONG", "shares": "263", "allocation": "6%"},
        {"ticker": "JNJ", "position_type": "LONG", "shares": "271", "allocation": "6%"},
        {"ticker": "NEE", "position_type": "LONG", "shares": "497", "allocation": "5%"},
        {"ticker": "DIS", "position_type": "LONG", "shares": "381", "allocation": "5%"},
        {"ticker": "EEM", "position_type": "LONG", "shares": "596", "allocation": "4%"},
        {"ticker": "VNQ", "position_type": "LONG", "shares": "373", "allocation": "4%"},
        {"ticker": "CASH", "position_type": "CASH", "shares": "0", "allocation": "1%"}
    ]
}

json8 = {
    "final_portfolio": [
        {"ticker": "IAU", "position_type": "LONG", "shares": "125", "allocation": "5%"},
        {"ticker": "GLD", "position_type": "LONG", "shares": "28", "allocation": "5%"},
        {"ticker": "SCHE", "position_type": "LONG", "shares": "160", "allocation": "4%"},
        {"ticker": "VWO", "position_type": "LONG", "shares": "100", "allocation": "4%"},
        {"ticker": "IGSB", "position_type": "LONG", "shares": "60", "allocation": "3%"},
        {"ticker": "VCIT", "position_type": "LONG", "shares": "38", "allocation": "3%"},
        {"ticker": "EQIX", "position_type": "LONG", "shares": "10", "allocation": "8%"},
        {"ticker": "DLR", "position_type": "LONG", "shares": "53", "allocation": "8%"},
        {"ticker": "MNTK", "position_type": "LONG", "shares": "200", "allocation": "2%"},
        {"ticker": "ORA", "position_type": "LONG", "shares": "29", "allocation": "2%"},
        {"ticker": "JXN", "position_type": "LONG", "shares": "200", "allocation": "10%"},
        {"ticker": "APO", "position_type": "LONG", "shares": "100", "allocation": "10%"},
        {"ticker": "CRBG", "position_type": "LONG", "shares": "233", "allocation": "7%"},
        {"ticker": "NVDA", "position_type": "LONG", "shares": "52", "allocation": "13%"},
        {"ticker": "CRDO", "position_type": "LONG", "shares": "200", "allocation": "4%"},
        {"ticker": "ARM", "position_type": "LONG", "shares": "40", "allocation": "4%"},
        {"ticker": "ADMA", "position_type": "LONG", "shares": "600", "allocation": "3%"},
        {"ticker": "BNTC", "position_type": "LONG", "shares": "1500", "allocation": "3%"},
        {"ticker": "TPST", "position_type": "LONG", "shares": "2000", "allocation": "2%"}
    ]
}

json9 = {
    "final_portfolio": [
        {"ticker": "PSP", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "MNA", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "CPER", "position_type": "LONG", "shares": "240", "allocation": "6%"},
        {"ticker": "DBB", "position_type": "LONG", "shares": "80", "allocation": "2%"},
        {"ticker": "VGIT", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "SCHP", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "SHY", "position_type": "LONG", "shares": "80", "allocation": "2%"},
        {"ticker": "IAU", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "GLD", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "IGSB", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "VCIT", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "HYG", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "FALN", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "AMPS", "position_type": "LONG", "shares": "80", "allocation": "2%"},
        {"ticker": "MNTK", "position_type": "LONG", "shares": "80", "allocation": "2%"},
        {"ticker": "JXN", "position_type": "LONG", "shares": "240", "allocation": "6%"},
        {"ticker": "APO", "position_type": "LONG", "shares": "160", "allocation": "4%"},
        {"ticker": "EQH", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "EGP", "position_type": "LONG", "shares": "160", "allocation": "4%"},
        {"ticker": "TRNO", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "FR", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "NVDA", "position_type": "LONG", "shares": "280", "allocation": "7%"},
        {"ticker": "CRDO", "position_type": "LONG", "shares": "120", "allocation": "3%"},
        {"ticker": "ARM", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "ZJYL", "position_type": "LONG", "shares": "80", "allocation": "2%"},
        {"ticker": "BSX", "position_type": "LONG", "shares": "200", "allocation": "5%"},
        {"ticker": "KEQU", "position_type": "LONG", "shares": "120", "allocation": "3%"}
    ]
}

def connect_to_ib():
    """
    Establish a connection to Interactive Brokers TWS or Gateway
    
    Attempts to connect on standard ports (4002, 7497) with different client IDs.
    
    Returns:
        IB connection object if successful, None if connection fails
    """
    ib = IB()
    
    # Disconnect if already connected
    if ib.isConnected():
        ib.disconnect()

    connected = False
    
    # Try standard TWS/Gateway ports
    ports = [4002, 7497]  # 4002 for Gateway, 7497 for TWS
    
    for port in ports:
        for client_id in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=client_id)
                connected = True
                print(f"🌐 Connected to IB on port {port} with client ID {client_id}")
                return ib
            except Exception as e:
                print(f"🚨 Connection failed on port {port} with client ID {client_id}: {e}")
    
    print("⛔ Could not connect to IB on any port or client ID")
    return None

def get_ib_historical_data(ib, ticker):
    from ib_insync import Stock
    
    try:
        # Create contract for the ticker (assuming US stock)
        contract = Stock(ticker, 'SMART', 'USD')
        
        # Request historical data - increased to 30 days for better analysis
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='4 Y',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        bars = util.df(bars)
        
        # Extract the most recent close price
        if not bars.empty:
            print(bars)
            return bars
        else:
            print(f"⚠️ No historical data retrieved for {ticker}")
            return None
            
    except Exception as e:
        print(f"❌ Error retrieving historical data: {e}")
        return None

def get_portfolio_value(ib):
    """
    Get the total liquid value of the portfolio from Interactive Brokers
    
    Args:
        ib: IB connection object
        
    Returns:
        float: Total portfolio value (NetLiquidation)
    """
    try:
        # Request account summary
        account_summary = ib.accountSummary()
        
        # Find NetLiquidation tag
        for summary in account_summary:
            if summary.tag == 'NetLiquidation' and summary.currency == 'USD':
                portfolio_value = float(summary.value)
                print(f"📊 Current portfolio value: ${portfolio_value:,.2f}")
                return portfolio_value
        
        # If NetLiquidation not found, try TotalCashValue
        for summary in account_summary:
            if summary.tag == 'TotalCashValue' and summary.currency == 'USD':
                portfolio_value = float(summary.value)
                print(f"📊 Current portfolio cash value: ${portfolio_value:,.2f}")
                return portfolio_value
        
        print("⚠️ Could not find portfolio value, using default")
        return 1000000  # Default fallback
    
    except Exception as e:
        print(f"❌ Error retrieving portfolio value: {e}")
        print("⚠️ Using default portfolio value")
        return 1000000  # Default fallback

def get_historical_data_for_all_tickers(portfolio):
    """
    Get historical data for all tickers in the portfolio
    
    Args:
        portfolio: Dictionary containing portfolio data
        
    Returns:
        Dictionary with tickers as keys and historical data as values, and the portfolio value
    """
    results = {}
    portfolio_value = None
    
    # Connect to IB once
    ib = connect_to_ib()
    if not ib:
        print("❌ Could not connect to Interactive Brokers")
        return results, 1000000  # Default fallback value
    
    try:
        # Get portfolio value first
        portfolio_value = get_portfolio_value(ib)
        
        # Get SPY data first for comparison
        print(f"\n📊 Getting historical data for SPY...")
        spy_data = get_ib_historical_data(ib, "SPY")
        results["SPY"] = spy_data
        
        # Get data for portfolio tickers
        for position in portfolio["final_portfolio"]:
            ticker = position["ticker"]
            print(f"\n📊 Getting historical data for {ticker}...")
            data = get_ib_historical_data(ib, ticker)
            results[ticker] = data
            
        return results, portfolio_value
    finally:
        # Disconnect from IB only once at the end
        if ib and ib.isConnected():
            print("🔌 Disconnecting from Interactive Brokers")
            ib.disconnect()

def get_current_portfolio_holdings(ib):
    """
    Get current portfolio holdings from Interactive Brokers using proper IB Insync methods
    """
    try:
        # Get portfolio data directly using portfolio() method
        portfolio = ib.portfolio()
        holdings = {}
        
        if portfolio:
            for item in portfolio:
                symbol = item.contract.symbol
                if symbol not in holdings:
                    holdings[symbol] = {
                        'shares': float(item.position),
                        'market_value': float(item.marketValue),
                        'average_cost': float(item.averageCost)
                    }
                    print(f"Found position: {symbol} - {holdings[symbol]}")
        else:
            print("No positions found in the account")
            
        return holdings
    except Exception as e:
        print(f"❌ Error getting current holdings: {e}")
        return None

def calculate_portfolio_returns(portfolio, historical_data, initial_investment):
    """
    Calculate portfolio returns over time based on historical data and allocation percentages

    Args:
        portfolio: Dictionary containing portfolio data
        historical_data: Dictionary with tickers as keys and historical data as values
        initial_investment: Actual portfolio value from IBKR

    Returns:
        Tuple containing (portfolio_values DataFrame, allocation_dict) or (None, None) if error
    """
    # Create dictionaries to store shares and allocations for each ticker
    # shares_dict = {} # This variable was unused
    allocation_dict = {}

    # Handle duplicate tickers by combining their allocations and shares
    combined_allocations = {}

    # Filter out CASH positions from allocation calculation if present
    portfolio_items = [pos for pos in portfolio.get("final_portfolio", []) if pos.get("position_type", "").upper() != "CASH"]

    if not portfolio_items:
        print("⚠️ Portfolio contains no non-cash positions to calculate returns.")
        return None, None


    for position in portfolio_items:
        ticker = position.get("ticker")
        allocation_str = position.get("allocation", "0%")
        position_type = position.get("position_type", "LONG").upper()

        if not ticker:
            print(f"⚠️ Skipping position with missing ticker: {position}")
            continue

        try:
            allocation = float(allocation_str.strip("%")) / 100
        except ValueError:
            print(f"⚠️ Skipping position with invalid allocation format for {ticker}: {allocation_str}")
            continue


        # Adjust allocation sign based on position type
        if position_type == "SHORT":
            allocation *= -1

        if ticker in combined_allocations:
            combined_allocations[ticker] += allocation
        else:
            combined_allocations[ticker] = allocation

    # Use the combined values
    allocation_dict = combined_allocations

    if not allocation_dict:
         print("⚠️ No valid allocations found after processing portfolio.")
         return None, None

    # Normalize allocations based on absolute values to handle long/short mix
    total_exposure = sum(abs(v) for v in allocation_dict.values())
    if total_exposure > 1e-9: # Use tolerance for floating point comparison
        for ticker in allocation_dict:
            allocation_dict[ticker] /= total_exposure
    else:
        print("⚠️ Total absolute allocation is zero or near-zero, cannot normalize.")
        # Proceeding with potentially zero allocations, which might lead to zero returns.

    # Create a combined DataFrame for all ticker prices
    all_data = pd.DataFrame()

    # First, check if we have data for all tickers in allocation_dict
    missing_data = []
    valid_tickers = list(allocation_dict.keys()) # Tickers we actually need data for

    for ticker in valid_tickers:
        if ticker not in historical_data or historical_data[ticker] is None or historical_data[ticker].empty:
            missing_data.append(ticker)

    if missing_data:
        print(f"⚠️ Missing historical data for required tickers: {', '.join(missing_data)}")
        # Decide if partial calculation is allowed or return error
        # For now, let's try to proceed with available data, but warn user
        print("⚠️ Proceeding with backtest using only available ticker data.")
        # Remove missing tickers from allocation_dict to avoid errors later
        for ticker in missing_data:
            del allocation_dict[ticker]
        valid_tickers = list(allocation_dict.keys()) # Update valid tickers
        if not valid_tickers:
             print("❌ No historical data available for any allocated ticker. Cannot calculate returns.")
             return None, None


    # Combine all close prices into one DataFrame for valid tickers
    print(" assembling historical data frame...")
    for ticker in valid_tickers:
        data = historical_data[ticker]
        if 'date' in data.columns and 'close' in data.columns:
            try:
                # Ensure date is datetime and set as index
                date_index = pd.to_datetime(data['date'])
                temp_series = pd.Series(data['close'].values, index=date_index, name=ticker)
                if all_data.empty:
                     all_data = temp_series.to_frame()
                else:
                     all_data = pd.merge(all_data, temp_series.to_frame(), left_index=True, right_index=True, how='outer')
            except Exception as e:
                 print(f" Error processing data for {ticker}: {e}")
        else:
             print(f"⚠️ Data for {ticker} is missing 'date' or 'close' column.")


    if all_data.empty:
        print("❌ No valid historical data could be assembled into DataFrame.")
        return None, None

    # Ensure all_data has a proper datetime index and sort
    all_data = all_data.sort_index()

    # Fill missing values (e.g., holidays, different start dates)
    # Forward fill first, then backfill for any remaining NaNs at the beginning
    all_data = all_data.ffill().bfill()

    # Double-check if any NaNs remain after filling (shouldn't happen ideally)
    if all_data.isnull().values.any():
        print("⚠️ Warning: NaNs remain in price data after ffill/bfill. Check data sources.")
        # Option: Drop rows with any NaNs, but might lose data points
        # all_data = all_data.dropna()
        # If dropping leads to empty dataframe, return error
        # if all_data.empty:
        #    print("❌ Dataframe became empty after dropping NaNs.")
        #    return None, None


    print(f"📊 Assembled data spans from {all_data.index.min()} to {all_data.index.max()} for {len(valid_tickers)} tickers.")

    # Calculate portfolio values over time
    portfolio_values = pd.DataFrame(index=all_data.index)
    portfolio_values['value'] = 0.0  # Initialize with float

    print(f"💵 Using initial investment value: ${initial_investment:,.2f}")
    initial_ticker_values = {} # Stores {'ticker': {'shares': float, 'initial_day': datetime}}

    # Calculate initial shares based on first available price for each ticker
    print(" calculating initial shares based on first price...")
    for ticker in valid_tickers:
        if ticker not in all_data.columns: # Should not happen if logic above is correct, but check
            print(f" Ticker {ticker} unexpectedly not in all_data columns.")
            continue

        first_valid_idx = all_data[ticker].first_valid_index()
        if first_valid_idx is not None:
            initial_price = all_data.loc[first_valid_idx, ticker]
            if initial_price > 1e-9: # Avoid division by zero or tiny numbers
                allocation = allocation_dict.get(ticker, 0) # Get allocation safely
                # Use absolute allocation for share calculation magnitude
                adjusted_shares = (initial_investment * abs(allocation)) / initial_price
                # Apply sign based on original allocation (long/short)
                if allocation < 0:
                    adjusted_shares *= -1

                initial_ticker_values[ticker] = {
                    'shares': adjusted_shares,
                    'initial_day': first_valid_idx
                }
                # print(f"  {ticker}: Calculated {adjusted_shares:.4f} shares at ${initial_price:.2f} on {first_valid_idx.date()}")
            else:
                print(f"⚠️ Initial price for {ticker} on {first_valid_idx.date()} is zero or near-zero. Cannot calculate shares.")
                # Remove ticker from allocation_dict and valid_tickers if shares cannot be calculated?
                # Or assign 0 shares? Let's assign 0 shares for now.
                initial_ticker_values[ticker] = {'shares': 0.0, 'initial_day': first_valid_idx}
        else:
             print(f"⚠️ No valid price data found for {ticker} in the assembled data.")
             # Ticker effectively has 0 shares if no price data exists


    # Calculate daily portfolio value based on fixed shares and daily prices
    print(" calculating daily portfolio value...")
    for day in all_data.index:
        day_value = 0.0
        for ticker, initial_info in initial_ticker_values.items():
             shares = initial_info['shares']
             if abs(shares) > 1e-9 and ticker in all_data.columns: # Check if shares != 0 and ticker exists
                 current_price = all_data.loc[day, ticker]
                 # Check if current_price is NaN (can happen if bfill didn't cover start)
                 if pd.notna(current_price):
                     day_value += shares * current_price
                 # else: price is NaN, contribution is 0 for this day

        portfolio_values.loc[day, 'value'] = day_value


    # Ensure the first value is based on the actual initial investment if possible
    # The calculated value on the first day might differ slightly due to using first available prices
    # Option 1: Use calculated first day value (current implementation)
    # Option 2: Force first day value to be initial_investment
    # portfolio_values.iloc[0, portfolio_values.columns.get_loc('value')] = initial_investment

    # Handle cases where calculated value might be zero or negative if logic allows
    if (portfolio_values['value'] <= 1e-9).all():
         print("⚠️ Portfolio value remained zero or near-zero throughout the backtest period.")
         # Return empty results or handle as appropriate
         # return None, None # Let's allow it to proceed and show flat return for now

    # Calculate daily returns (use .loc to avoid potential SettingWithCopyWarning)
    # Remove deprecated fill_method
    portfolio_values['daily_return'] = portfolio_values['value'].pct_change()

    # Handle the first day's return (which is NaN after pct_change)
    portfolio_values.loc[portfolio_values.index[0], 'daily_return'] = 0.0

    # Fill any other NaNs that might arise (e.g., if value was 0 then became non-zero)
    portfolio_values['daily_return'] = portfolio_values['daily_return'].fillna(0)

    # Calculate cumulative returns with proper geometric compounding
    portfolio_values['cumulative_return'] = (1 + portfolio_values['daily_return']).cumprod() - 1

    # Verify consistency between value and returns (optional check)
    # calculated_values = initial_investment * (1 + portfolio_values['cumulative_return'])
    # value_discrepancy = np.abs(portfolio_values['value'] - calculated_values)
    # if (value_discrepancy > 1).any():  # Allow $1 tolerance
    #     print("⚠️ Warning: Value/return mismatch detected - check calculation logic")
    #     print("   Max discrepancy: ${:.2f}".format(value_discrepancy.max()))


    # --- Calculate Metrics ---
    print(" calculating performance metrics...")
    # Improved drawdown calculation
    portfolio_values['peak'] = portfolio_values['value'].cummax()
    # Avoid division by zero if peak is zero
    portfolio_values['drawdown'] = np.where(portfolio_values['peak'] > 1e-9,
                                           (portfolio_values['value'] - portfolio_values['peak']) / portfolio_values['peak'],
                                           0.0) # Set drawdown to 0 if peak is 0

    # Fill any potential NaNs/Infs arising from edge cases in drawdown calculation
    portfolio_values['drawdown'] = portfolio_values['drawdown'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Annualized return
    num_days = len(portfolio_values)
    trading_days_per_year = 252
    if num_days > 1:
         # Use the last cumulative return for CAGR calculation
         total_return_cumulative = portfolio_values['cumulative_return'].iloc[-1]
         # CAGR formula: (Ending Value / Beginning Value)^(1 / Num Years) - 1
         # (1 + total_return_cumulative)^(trading_days_per_year / num_days) - 1
         ann_return = (1 + total_return_cumulative) ** (trading_days_per_year / num_days) - 1
    elif num_days == 1:
         ann_return = portfolio_values['cumulative_return'].iloc[-1] # Total return if only 1 day
    else: # num_days == 0
         ann_return = 0.0

    # Calculate annualized volatility
    if num_days > 1:
        ann_volatility = portfolio_values['daily_return'].std() * np.sqrt(trading_days_per_year)
    else:
        ann_volatility = 0.0 # No volatility if <= 1 day

    # Calculate Sharpe ratio (assuming risk-free rate = 0)
    if ann_volatility > 1e-9:
        sharpe_ratio = ann_return / ann_volatility
    else:
        sharpe_ratio = 0.0 # Or np.nan, depending on desired output for zero volatility

    # Ensure no NaN values in the final 'value' (use last valid if needed)
    if pd.isna(portfolio_values['value'].iloc[-1]):
        last_valid_value = portfolio_values['value'].ffill().iloc[-1]
        portfolio_values.loc[portfolio_values.index[-1], 'value'] = last_valid_value


    print(f"📊 Portfolio calculated for {num_days} days")
    # Return calculated values and the allocation dict used (might have changed if data was missing)
    return portfolio_values, allocation_dict

# Wrap execution logic in a function
def backtest(portfolio_json):
    """
    Runs a backtest for a given portfolio JSON configuration.

    Args:
        portfolio_json: Dictionary containing the portfolio definition (e.g., json, json2, etc.)
    """
    # Get historical data for all tickers for the given portfolio
    print(f"\n📊 Fetching historical data for portfolio...")
    # Make sure get_historical_data_for_all_tickers returns dataframes or None
    historical_data, portfolio_value = get_historical_data_for_all_tickers(portfolio_json)

    # --- Initial Data Check ---
    if not historical_data:
        print("❌ Failed to fetch any historical data. Cannot proceed.")
        return
    if portfolio_value is None:
        print("⚠️ Failed to fetch portfolio value, using default $1,000,000.")
        portfolio_value = 1000000

    # Check if SPY data is present, needed for comparison plot
    if "SPY" not in historical_data or historical_data["SPY"] is None or historical_data["SPY"].empty:
         print("⚠️ SPY historical data not found or empty. Comparison plot will exclude SPY.")


    # Get current holdings (optional, for comparison - uses default account)
    print("\n💼 Fetching current holdings for comparison...")
    current_holdings = None # Initialize
    ib_conn_current = connect_to_ib() # Connect once for current holdings
    if ib_conn_current:
        try:
            current_holdings = get_current_portfolio_holdings(ib_conn_current)
        except Exception as e:
            print(f"❌ Error fetching current holdings: {e}")
        finally:
            if ib_conn_current.isConnected():
                print("🔌 Disconnecting from IB (after getting current holdings)")
                ib_conn_current.disconnect()
    else:
        print("⚠️ Could not connect to IB to fetch current holdings.")


    print("\n🔍 Summary of historical data fetched:")
    valid_data_count = 0
    for ticker, data in historical_data.items():
        # Check if data is a DataFrame and not empty
        if isinstance(data, pd.DataFrame) and not data.empty:
            print(f"  {ticker}: {len(data)} bars retrieved")
            valid_data_count +=1
        # Allow None or empty for SPY if fetch failed, but note it
        elif ticker == "SPY" and (data is None or data.empty):
             print(f"  {ticker}: Data missing or empty.")
        elif data is not None: # If not None and not DataFrame/empty
             print(f"  {ticker}: Data retrieved but not in expected format or empty.")
        # else: data is None (already handled for SPY)


    if valid_data_count == 0:
        print("❌ No valid historical data retrieved for any ticker. Cannot proceed with backtest.")
        return

    # Calculate portfolio returns using the provided portfolio json
    print("\n📈 Calculating portfolio returns...")
    # Pass the potentially modified portfolio_value
    portfolio_values, allocation_dict = calculate_portfolio_returns(portfolio_json, historical_data, portfolio_value)

    if portfolio_values is None or portfolio_values.empty:
         print("❌ Failed to calculate portfolio returns. Cannot generate plot.")
         return # Exit if calculation failed

    # --- Plotting and Metrics ---
    print("\n📊 Portfolio Performance Summary:")
    print(f"Initial Portfolio Value: ${portfolio_values['value'].iloc[0]:,.2f}")
    final_val = portfolio_values['value'].iloc[-1]
    print(f"Final Portfolio Value: ${final_val:,.2f}")

    # Ensure final value is not NaN before calculating total return
    if pd.isna(portfolio_values['cumulative_return'].iloc[-1]):
         print("⚠️ Final cumulative return is NaN. Cannot calculate Total Return.")
         total_return_pct = np.nan
    else:
         total_return_pct = portfolio_values['cumulative_return'].iloc[-1] * 100
         print(f"Total Return: {total_return_pct:.2f}%")


    # Print daily returns information
    print("\n📅 Daily Returns Summary:")
    print(f"Mean Daily Return: {portfolio_values['daily_return'].mean() * 100:.4f}%")
    print(f"Std Dev of Daily Returns: {portfolio_values['daily_return'].std() * 100:.4f}%")
    print(f"Min Daily Return: {portfolio_values['daily_return'].min() * 100:.4f}%")
    print(f"Max Daily Return: {portfolio_values['daily_return'].max() * 100:.4f}%")

    # Print portfolio allocation information (using the final dict from calculation)
    print("\n💰 Portfolio Allocation Used (Normalized, After Data Checks):")
    if allocation_dict:
        for ticker, allocation in allocation_dict.items():
            print(f"{ticker}: {allocation*100:.2f}%")
    else:
        print("  No allocations were used in the calculation (likely due to missing data).")


    # Recalculate metrics based on returned portfolio_values DataFrame
    # (Metrics calculation is now inside calculate_portfolio_returns, just print them here)
    num_days = len(portfolio_values)
    trading_days_per_year = 252

    if num_days > 1:
        total_return_cumulative = portfolio_values['cumulative_return'].iloc[-1]
        if pd.notna(total_return_cumulative):
             ann_return = (1 + total_return_cumulative) ** (trading_days_per_year / num_days) - 1
        else:
             ann_return = np.nan # If total return is NaN, annualized is NaN
    elif num_days == 1:
        ann_return = portfolio_values['cumulative_return'].iloc[-1]
    else:
        ann_return = 0.0

    if num_days > 1:
        ann_volatility = portfolio_values['daily_return'].std() * np.sqrt(trading_days_per_year)
    else:
        ann_volatility = 0.0

    if pd.notna(ann_return) and pd.notna(ann_volatility) and ann_volatility > 1e-9:
        sharpe_ratio = ann_return / ann_volatility
    else:
        sharpe_ratio = np.nan # Sharpe is NaN if ann_return or ann_volatility is NaN or volatility is zero

    max_drawdown = portfolio_values['drawdown'].min() * 100

    # Get max drawdown date - convert to readable format
    try:
        # Ensure drawdown series is not all zeros before finding idxmin
        if not (portfolio_values['drawdown'] == 0).all():
            min_idx = portfolio_values['drawdown'].idxmin()
            max_drawdown_date = min_idx.strftime('%Y-%m-%d') if isinstance(min_idx, pd.Timestamp) else "Date not found"
        else:
            max_drawdown_date = "N/A (No drawdown)"
    except Exception as e:
        print(f"Error getting drawdown date: {e}")
        max_drawdown_date = "Date calculation error"

    print("\n📈 Calculated Metrics:")
    print(f"Annualized Return: {ann_return*100:.2f}%" if pd.notna(ann_return) else "Annualized Return: N/A")
    print(f"Annualized Volatility: {ann_volatility*100:.2f}%" if pd.notna(ann_volatility) else "Annualized Volatility: N/A")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}" if pd.notna(sharpe_ratio) else "Sharpe Ratio: N/A")
    print(f"Maximum Drawdown: {max_drawdown:.2f}%")
    print(f"Maximum Drawdown Date: {max_drawdown_date}")

    # --- Plotting ---
    print("\n🖼️ Generating performance plot...")
    fig = go.Figure()

    # Add optimized portfolio cumulative returns trace
    fig.add_trace(
        go.Scatter(
            x=portfolio_values.index,
            y=portfolio_values['cumulative_return'] * 100,
            mode='lines',
            name='Optimized Portfolio',
            line=dict(color='#2ecc71', width=2)
        )
    )

    # Add SPY cumulative returns trace
    if 'SPY' in historical_data and isinstance(historical_data['SPY'], pd.DataFrame) and not historical_data['SPY'].empty:
        spy_data = historical_data['SPY']
        if 'date' in spy_data.columns and 'close' in spy_data.columns:
            spy_df = pd.DataFrame({'close': spy_data['close'].values}, index=pd.to_datetime(spy_data['date']))
            spy_df = spy_df.reindex(portfolio_values.index).ffill().bfill() # Align dates

            if not spy_df.empty and not spy_df['close'].isnull().all():
                 # Remove deprecated fill_method
                 spy_returns = spy_df['close'].pct_change().fillna(0)
                 spy_cumulative = (1 + spy_returns).cumprod() - 1

                 fig.add_trace(
                     go.Scatter(
                         x=spy_df.index,
                         y=spy_cumulative * 100,
                         mode='lines',
                         name='SPY Returns',
                         line=dict(color='#3498db', width=2)
                     )
                 )
        else:
            print("  SPY data missing expected 'date' or 'close' columns.")
    # else: Already printed warning about missing SPY earlier


    # --- Calculate and add current portfolio returns if available ---
    if current_holdings:
        print("\n🔄 Calculating returns for current portfolio holdings (for comparison plot)...")
        # Filter out holdings with zero shares or market value
        valid_holdings = {
            symbol: data for symbol, data in current_holdings.items()
            if data.get('shares', 0) != 0 and data.get('market_value', 0) != 0
        }

        if not valid_holdings:
             print("  No valid current holdings (with non-zero shares and market value) found.")
        else:
            symbols_to_fetch = list(valid_holdings.keys())
            print(f"  Fetching historical data for {len(symbols_to_fetch)} current holding symbols: {', '.join(symbols_to_fetch)}")

            # --- Fetch data for current holdings ONCE ---
            current_holdings_data = {}
            ib_conn_plot = connect_to_ib() # Connect once for this plotting task
            if ib_conn_plot:
                try:
                    for symbol in symbols_to_fetch:
                        print(f"    Fetching for {symbol}...")
                        data = get_ib_historical_data(ib_conn_plot, symbol)
                        if isinstance(data, pd.DataFrame) and not data.empty:
                            current_holdings_data[symbol] = data
                        else:
                            print(f"    ⚠️ Failed to get valid data for {symbol}")
                except Exception as e:
                     print(f"    ❌ Error fetching data for current holdings: {e}")
                finally:
                    if ib_conn_plot.isConnected():
                         print("    🔌 Disconnecting from IB (after fetching current holdings data)")
                         ib_conn_plot.disconnect()
            else:
                 print("  ⚠️ Could not connect to IB to fetch data for current holdings plot.")
            # --- End data fetching ---


            if not current_holdings_data:
                 print("  ⚠️ Failed to fetch historical data for any current holdings. Cannot plot comparison.")
            else:
                # --- Calculate returns using fetched data ---
                current_portfolio_df = pd.DataFrame(index=portfolio_values.index) # Initialize DataFrame for current returns
                all_current_returns = pd.DataFrame(index=portfolio_values.index) # Store weighted returns per symbol
                total_current_value = sum(abs(holding.get('market_value', 0)) for holding in valid_holdings.values()) # Recalculate total value using only valid holdings

                calculation_successful = False
                if total_current_value > 1e-9: # Check again in case valid_holdings changed
                    print("  Calculating weighted returns for current holdings...")
                    for symbol, holding_data in current_holdings_data.items():
                         # Holding info (shares, market value) is from valid_holdings
                         holding_info = valid_holdings[symbol]
                         market_value = holding_info.get('market_value', 0)
                         weight = market_value / total_current_value # Use signed value

                         if 'date' in holding_data.columns and 'close' in holding_data.columns:
                             symbol_df = pd.DataFrame({'close': holding_data['close'].values}, index=pd.to_datetime(holding_data['date']))
                             symbol_df = symbol_df.reindex(portfolio_values.index).ffill().bfill() # Align dates

                             if not symbol_df.empty and not symbol_df['close'].isnull().all():
                                 # Remove deprecated fill_method
                                 symbol_returns = symbol_df['close'].pct_change().fillna(0)
                                 weighted_returns = symbol_returns * weight
                                 all_current_returns[symbol] = weighted_returns # Store weighted returns per symbol
                                 calculation_successful = True # Mark success if at least one symbol processed
                         else:
                              print(f"    ⚠️ Data for current holding {symbol} missing 'date' or 'close'.")

                    if calculation_successful:
                        # Sum weighted returns across all symbols for each day
                        current_portfolio_df['returns'] = all_current_returns.sum(axis=1, skipna=True) # Sum returns, skip NaNs
                        current_portfolio_df['returns'] = current_portfolio_df['returns'].fillna(0) # Fill any remaining NaNs from sum
                        current_portfolio_df['cumulative'] = (1 + current_portfolio_df['returns']).cumprod() - 1

                        # Add the trace for current portfolio
                        fig.add_trace(
                            go.Scatter(
                                x=current_portfolio_df.index,
                                y=current_portfolio_df['cumulative'] * 100,
                                mode='lines',
                                name='Current Portfolio (Estimate)',
                                line=dict(color='#e74c3c', width=2)
                            )
                        )
                        print("  Current portfolio comparison returns calculated and added to plot.")
                    else:
                         print("  ⚠️ No valid returns could be calculated for any current holdings symbols.")

                else: # total_current_value is 0 or near-zero
                    print("  ⚠️ Total market value of valid current holdings is zero, cannot calculate comparison returns.")
                # --- End return calculation ---

    # else: current_holdings was None or empty initially


    # Update layout for a clean, professional look
    fig.update_layout(
        title='Portfolio Performance Comparison',
        height=600,
        showlegend=True,
        xaxis_title='Date',
        yaxis_title='Cumulative Returns (%)',
        hovermode='x unified',
        template='plotly_white',
        legend_title_text='Portfolio',
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(
            tickformat='.1f', # Format y-axis ticks
            gridcolor='lightgrey',
            gridwidth=1,
            zeroline=True, zerolinecolor='grey', zerolinewidth=1
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            gridwidth=1,
            showgrid=True # Ensure x-axis grid is shown
        )
    )

    # Display the plot
    print("\n🖼️ Displaying performance plot...")
    fig.show()

# Example of how to run the backtest when the script is executed directly
if __name__ == "__main__":
    # Choose which portfolio JSON to test (e.g., json, json2, ..., json9)
    selected_portfolio_json = json9 # Or change to json, json2, etc.
    print(f"🚀 Running backtest for selected portfolio...")
    backtest(selected_portfolio_json)

