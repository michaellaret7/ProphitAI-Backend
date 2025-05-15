import requests
import pandas as pd
from datetime import datetime, timedelta

def get_stock_15min_bars(ticker, api_key, start_date=None, end_date=None):
    """
    Fetches 15-minute bars for a given stock from financialdatasets.ai
    
    Args:
        ticker (str): The stock ticker symbol (e.g., 'AAPL', 'MSFT')
        api_key (str): Your financialdatasets.ai API key
        start_date (str, optional): Start date in 'YYYY-MM-DD' format. Defaults to 7 days ago.
        end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to today.
    
    Returns:
        pandas.DataFrame: DataFrame containing the 15-minute bar data
    """
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d')
    
    # API endpoint and parameters
    url = "https://api.financialdatasets.ai/prices"
    headers = {
        "X-API-KEY": api_key
    }
    params = {
        "ticker": ticker,
        "interval": "minute",
        "interval_multiplier": 15,
        "start_date": start_date,
        "end_date": end_date
    }
    
    try:
        # Make the API request
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        # Parse response to DataFrame
        data = response.json()
        df = pd.DataFrame(data["prices"])
        df.drop(columns=["time_milliseconds"], inplace=True)
        
        # Convert timestamp to datetime
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df.rename(columns={"time": "timestamp"}, inplace=True)
            df.set_index("timestamp", inplace=True)
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Error parsing response: {e}")
        return None

# Example usage
if __name__ == "__main__":
    api_key = "7b14137a-24fa-45d3-a752-6889558f551f"  # Replace with your actual API key
    df = get_stock_15min_bars("AAPL", api_key, start_date="2024-01-01", end_date="2024-01-31")
    
    if df is not None:
        print(df)