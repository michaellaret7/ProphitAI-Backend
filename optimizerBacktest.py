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

# Get historical data for all tickers
historical_data, portfolio_value = get_historical_data_for_all_tickers(json7)

# Get current holdings
ib = connect_to_ib()
if ib:
    current_holdings = get_current_portfolio_holdings(ib)
    ib.disconnect()
else:
    current_holdings = None

print("\n🔍 Summary of historical data:")
for ticker, data in historical_data.items():
    if data is not None:
        print(f"{ticker}: {len(data)} bars retrieved")
    else:
        print(f"{ticker}: No data retrieved")

def calculate_portfolio_returns(portfolio, historical_data, initial_investment):
    """
    Calculate portfolio returns over time based on historical data and allocation percentages
    
    Args:
        portfolio: Dictionary containing portfolio data
        historical_data: Dictionary with tickers as keys and historical data as values
        initial_investment: Actual portfolio value from IBKR
    
    Returns:
        Tuple containing (portfolio_values DataFrame, allocation_dict)
    """
    # Create dictionaries to store shares and allocations for each ticker
    shares_dict = {}
    allocation_dict = {}
    
    # Handle duplicate tickers by combining their allocations and shares
    combined_allocations = {}
    
    for position in portfolio["final_portfolio"]:
        ticker = position["ticker"]
        allocation = float(position["allocation"].strip("%")) / 100
        position_type = position["position_type"].upper()
        
        # Adjust allocation sign based on position type
        if position_type == "SHORT":
            allocation *= -1
        
        if ticker in combined_allocations:
            combined_allocations[ticker] += allocation
        else:
            combined_allocations[ticker] = allocation
    
    # Use the combined values
    allocation_dict = combined_allocations
    
    # Normalize allocations based on absolute values to handle long/short mix
    total_exposure = sum(abs(v) for v in allocation_dict.values())
    if total_exposure != 0:
        for ticker in allocation_dict:
            allocation_dict[ticker] /= total_exposure
    
    # Create a combined DataFrame for all ticker prices
    all_data = pd.DataFrame()
    
    # First, check if we have data for all tickers
    missing_data = []
    for ticker in allocation_dict.keys():
        if ticker not in historical_data or historical_data[ticker] is None or historical_data[ticker].empty:
            missing_data.append(ticker)
    
    if missing_data:
        print(f"⚠️ Missing historical data for: {', '.join(missing_data)}")
        print("Cannot calculate complete portfolio returns")
        return None, None
    
    # Combine all close prices into one DataFrame
    for ticker, data in historical_data.items():
        if ticker in allocation_dict and data is not None and not data.empty:
            # Create a Series with proper datetime index
            temp_series = pd.Series(data['close'].values, index=pd.to_datetime(data['date']))
            all_data[ticker] = temp_series
    
    # Ensure all_data has a proper datetime index
    all_data = all_data.sort_index()
    
    if all_data.empty:
        print("❌ No valid data to calculate portfolio returns")
        return None, None
    
    # MODIFIED APPROACH: Instead of dropping all rows with NaNs, fill with 0s for allocation calculation
    # Keep track of which tickers have data at each point
    print(f"📊 Available data spans from {all_data.index.min()} to {all_data.index.max()}")
    
    # Create a DataFrame to track available tickers for each day
    availability = pd.DataFrame(~all_data.isna(), dtype=int)
    
    # Calculate portfolio values over time, adjusting allocations based on available tickers
    portfolio_values = pd.DataFrame(index=all_data.index)
    portfolio_values['value'] = 0.0  # Explicitly use float instead of 0
    
    # First pass to initialize portfolio
    # Use actual portfolio value from IBKR instead of fixed amount
    print(f"💵 Using actual portfolio value: ${initial_investment:,.2f}")
    initial_ticker_values = {}
    
    # For each day, calculate portfolio value based on tickers that have data
    for day in all_data.index:
        # Get tickers available on this day
        available_tickers = availability.loc[day][availability.loc[day] == 1].index.tolist()
        
        if not available_tickers:
            continue
            
        # Adjust allocations to use only available tickers
        day_allocations = {}
        total_allocation = 0
        for ticker in available_tickers:
            if ticker in allocation_dict:
                day_allocations[ticker] = allocation_dict[ticker]
                total_allocation += allocation_dict[ticker]
        
        # Normalize allocations
        if total_allocation > 0:
            for ticker in day_allocations:
                day_allocations[ticker] /= total_allocation
        
        # Calculate value for this day
        day_value = 0.0
        for ticker, allocation in day_allocations.items():
            # For the first day a ticker appears, calculate adjusted shares
            first_idx = all_data[ticker].first_valid_index()
            if first_idx is not None and day == all_data.index[all_data.index.get_loc(first_idx)]:
                initial_price = float(all_data.loc[day, ticker])
                # Use absolute value for share calculation, sign comes from allocation
                adjusted_shares = (initial_investment * abs(allocation)) / initial_price
                # Apply short position sign
                if allocation < 0:
                    adjusted_shares *= -1
                
                initial_ticker_values[ticker] = {
                    'shares': adjusted_shares,
                    'initial_day': day
                }
            
            # Calculate value contribution using consistent share count
            if ticker in initial_ticker_values:
                adjusted_shares = initial_ticker_values[ticker]['shares']
                day_value += float(adjusted_shares * all_data.loc[day, ticker])
        
        # Store the day's value
        portfolio_values.loc[day, 'value'] = float(day_value)  # Ensure value is float
    
    # Fill any remaining NaN values with forward fill then backward fill
    # Update to use recommended methods instead of deprecated fillna(method='ffill')
    portfolio_values['value'] = portfolio_values['value'].ffill().bfill()
    
    # Calculate daily returns with proper compounding
    portfolio_values['daily_return'] = portfolio_values['value'].pct_change(fill_method=None)
    
    # Handle first day return explicitly
    if not portfolio_values.empty:
        initial_value = portfolio_values['value'].iloc[0]
        first_day_return = (portfolio_values['value'].iloc[1] - initial_value) / initial_value
        portfolio_values.at[portfolio_values.index[0], 'daily_return'] = 0  # Set first day to 0%
        portfolio_values.at[portfolio_values.index[1], 'daily_return'] = first_day_return

    # Fill any remaining NA values with 0 (should only be first element)
    portfolio_values['daily_return'] = portfolio_values['daily_return'].fillna(0)

    # Calculate cumulative returns with proper geometric compounding
    portfolio_values['cumulative_return'] = (1 + portfolio_values['daily_return']).cumprod() - 1
    
    # Verify consistency between value and returns
    calculated_values = initial_investment * (1 + portfolio_values['cumulative_return'])
    value_discrepancy = np.abs(portfolio_values['value'] - calculated_values)
    
    if (value_discrepancy > 1).any():  # Allow $1 tolerance for floating point errors
        print("⚠️ Warning: Value/return mismatch detected - check calculation logic")
        print("Max discrepancy: ${:.2f}".format(value_discrepancy.max()))
        
    # Improved drawdown calculation
    portfolio_values['peak'] = portfolio_values['value'].cummax()
    portfolio_values['drawdown'] = (portfolio_values['value'] - portfolio_values['peak']) / portfolio_values['peak']
    
    # Annualized return using log returns for better accuracy
    daily_log_returns = np.log(1 + portfolio_values['daily_return'])
    ann_return = np.exp(daily_log_returns.mean() * 252) - 1
    
    # Calculate annualized volatility
    daily_returns = portfolio_values['daily_return'].values
    ann_volatility = np.std(daily_returns) * np.sqrt(252)
    
    # Calculate Sharpe ratio
    sharpe_ratio = ann_return / ann_volatility if ann_volatility != 0 else 0
    
    # Ensure no NaN values in the final value
    if pd.isna(portfolio_values['value'].iloc[-1]):
        # Use the last valid value if the last value is NaN
        last_valid_value = portfolio_values['value'].dropna().iloc[-1]
        portfolio_values.loc[portfolio_values.index[-1], 'value'] = last_valid_value
    
    print(f"📊 Portfolio calculated for {len(portfolio_values)} days")
    return portfolio_values, allocation_dict

# Calculate portfolio returns but don't plot
print("\n📈 Calculating portfolio returns...")
portfolio_values, allocation_dict = calculate_portfolio_returns(json7, historical_data, portfolio_value)

if portfolio_values is not None:
    # Print summary statistics
    print("\n📊 Portfolio Performance Summary:")
    print(f"Initial Portfolio Value: ${portfolio_values['value'].iloc[0]:,.2f}")
    print(f"Final Portfolio Value: ${portfolio_values['value'].iloc[-1]:,.2f}")
    
    total_return = portfolio_values['cumulative_return'].iloc[-1] * 100
    print(f"Total Return: {total_return:.2f}%")
    
    # Print daily returns information
    print("\n📅 Daily Returns Summary:")
    print(f"Mean Daily Return: {portfolio_values['daily_return'].mean() * 100:.4f}%")
    print(f"Std Dev of Daily Returns: {portfolio_values['daily_return'].std() * 100:.4f}%")
    print(f"Min Daily Return: {portfolio_values['daily_return'].min() * 100:.4f}%")
    print(f"Max Daily Return: {portfolio_values['daily_return'].max() * 100:.4f}%")
    
    # Print portfolio allocation information
    print("\n💰 Portfolio Allocation Used:")
    for ticker, allocation in allocation_dict.items():
        print(f"{ticker}: {allocation*100:.2f}%")

    # Print annualized metrics
    trading_days_per_year = 252
    ann_return = ((1 + portfolio_values['cumulative_return'].iloc[-1]) ** (trading_days_per_year/len(portfolio_values))) - 1
    ann_volatility = portfolio_values['daily_return'].std() * np.sqrt(trading_days_per_year)
    sharpe_ratio = ann_return / ann_volatility if ann_volatility != 0 else 0
    
    # Calculate max drawdown
    portfolio_values['peak'] = portfolio_values['value'].cummax()
    portfolio_values['drawdown'] = (portfolio_values['value'] - portfolio_values['peak']) / portfolio_values['peak']
    max_drawdown = portfolio_values['drawdown'].min() * 100
    
    # Get max drawdown date - convert to readable format
    try:
        min_idx = portfolio_values['drawdown'].idxmin()
        max_drawdown_date = min_idx.strftime('%Y-%m-%d') if isinstance(min_idx, pd.Timestamp) else "Date not found"
    except Exception as e:
        print(f"Error getting drawdown date: {e}")
        max_drawdown_date = "Date not found"
    
    print("\n📈 Annualized Metrics:")
    print(f"Annualized Return: {ann_return*100:.2f}%")
    print(f"Annualized Volatility: {ann_volatility*100:.2f}%")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Maximum Drawdown: {max_drawdown:.2f}%")
    print(f"Maximum Drawdown Date: {max_drawdown_date}")

    # Create interactive Plotly visualization for cumulative returns
    fig = go.Figure()

    # Add optimized portfolio cumulative returns trace
    # Convert the index directly to dates without mapping through reference_dates
    fig.add_trace(
        go.Scatter(
            x=portfolio_values.index,  # Use the index directly as it contains the date info
            y=portfolio_values['cumulative_return'] * 100,
            mode='lines',
            name='Optimized Portfolio',
            line=dict(color='#2ecc71', width=2)
        )
    )

    # Add SPY cumulative returns trace
    if 'SPY' in historical_data and historical_data['SPY'] is not None:
        spy_data = historical_data['SPY']
        # Create a DataFrame with date index to match portfolio_values
        spy_df = pd.DataFrame(index=spy_data['date'])
        spy_df['close'] = spy_data['close'].values
        spy_df.index = pd.to_datetime(spy_df.index)  # Ensure datetime index
        
        # Filter SPY data to match portfolio_values start date
        portfolio_start_date = portfolio_values.index.min()
        spy_df = spy_df[spy_df.index >= portfolio_start_date]
        
        # Calculate returns
        spy_returns = spy_df['close'].pct_change(fill_method=None).fillna(0)
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

    # Calculate and add current portfolio returns if available
    if current_holdings:
        # Get historical data for current holdings
        # Create a DataFrame with datetime index for current portfolio
        current_portfolio_df = pd.DataFrame(index=portfolio_values.index)
        
        total_value = sum(abs(holding['market_value']) for holding in current_holdings.values())
        
        # Reconnect to IB for historical data
        ib = connect_to_ib()
        if ib:
            try:
                for symbol, holding in current_holdings.items():
                    # Get historical data for this symbol
                    symbol_data = get_ib_historical_data(ib, symbol)
                    if symbol_data is not None and not symbol_data.empty:
                        # Convert dates to datetime
                        symbol_dates = pd.to_datetime(symbol_data['date'])
                        symbol_returns = pd.Series(index=symbol_dates)
                        
                        # Calculate symbol returns
                        for i in range(1, len(symbol_data)):
                            prev_close = symbol_data['close'].iloc[i-1]
                            current_close = symbol_data['close'].iloc[i]
                            if prev_close > 0:
                                daily_return = (current_close - prev_close) / prev_close
                            else:
                                daily_return = 0
                            symbol_returns.iloc[i] = daily_return
                        
                        # First element is NaN, fill with 0
                        symbol_returns.iloc[0] = 0
                        
                        # Weight returns by portfolio allocation
                        weight = abs(holding['market_value']) / total_value
                        weighted_returns = symbol_returns * weight
                        
                        # If short position, negate the returns
                        if holding['shares'] < 0:
                            weighted_returns = -weighted_returns
                        
                        # Reindex to match the date range of the main portfolio
                        for date, value in weighted_returns.items():
                            if date in current_portfolio_df.index:
                                if 'returns' not in current_portfolio_df.columns:
                                    current_portfolio_df['returns'] = 0.0  # Explicitly use float
                                current_portfolio_df.loc[date, 'returns'] += value
                
                # Fill missing returns with 0
                if 'returns' in current_portfolio_df.columns:
                    current_portfolio_df['returns'] = current_portfolio_df['returns'].fillna(0)
                    
                    # Calculate cumulative returns
                    current_portfolio_df['cumulative'] = (1 + current_portfolio_df['returns']).cumprod() - 1
                    
                    # Add the trace for current portfolio
                    fig.add_trace(
                        go.Scatter(
                            x=current_portfolio_df.index,
                            y=current_portfolio_df['cumulative'] * 100,
                            mode='lines',
                            name='Current Portfolio',
                            line=dict(color='#e74c3c', width=2)
                        )
                    )
            finally:
                # Disconnect after getting all historical data
                ib.disconnect()

    # Update layout for a clean, professional look
    fig.update_layout(
        title='Portfolio Performance Comparison',
        height=600,
        showlegend=True,
        xaxis_title='Date',
        yaxis_title='Cumulative Returns (%)',
        hovermode='x unified',
        template='plotly_white',
        margin=dict(t=50, l=50, r=50, b=50),
        yaxis=dict(
            tickformat='.1f',
            gridcolor='lightgrey',
            gridwidth=1
        ),
        xaxis=dict(
            gridcolor='lightgrey',
            gridwidth=1
        )
    )

    # Display the plot
    fig.show()
    
