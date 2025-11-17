# import requests
# import pandas as pd
# from datetime import datetime, timedelta

# # Enter your FINRA API credentials here
# CLIENT_ID = 'c56428ff944940fbb2f4'
# CLIENT_SECRET = 'Ml17104021518!'

# def get_access_token(client_id, client_secret):
#     """Authenticate with FINRA and get access token"""
#     token_url = "https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials"
    
#     try:
#         response = requests.post(token_url, auth=(client_id, client_secret))
#         response.raise_for_status()
#         return response.json()["access_token"]
#     except Exception as e:
#         print(f"Authentication error: {e}")
#         return None

# def get_corporate_market_breadth(token, limit=100):
#     """Get corporate bond market breadth data"""
    
#     # Correct endpoint structure
#     group_name = "fixedIncomeMarket"
#     dataset_name = "corporateMarketBreadth"
    
#     api_url = f"https://api.finra.org/data/group/{group_name}/name/{dataset_name}"
    
#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json",
#         "Authorization": f"Bearer {token}"
#     }
    
#     # Request body with filters
#     request_body = {
#         "limit": limit
#     }
    
#     try:
#         response = requests.post(api_url, headers=headers, json=request_body)
#         response.raise_for_status()
#         data = response.json()
        
#         if isinstance(data, list) and len(data) > 0:
#             df = pd.DataFrame(data)
#             return df
#         else:
#             print("No data returned")
#             return pd.DataFrame()
            
#     except requests.exceptions.HTTPError as e:
#         print(f"HTTP Error: {e}")
#         print(f"Response: {response.text}")
#         return pd.DataFrame()
#     except Exception as e:
#         print(f"Error: {e}")
#         return pd.DataFrame()

# def get_treasury_data(token, limit=100):
#     """Get treasury aggregate data as an example"""
    
#     group_name = "fixedIncomeMarket"
#     dataset_name = "treasuryDailyAggregates"
    
#     api_url = f"https://api.finra.org/data/group/{group_name}/name/{dataset_name}"
    
#     headers = {
#         "Content-Type": "application/json",
#         "Accept": "application/json",
#         "Authorization": f"Bearer {token}"
#     }
    
#     request_body = {
#         "limit": limit
#     }
    
#     try:
#         response = requests.post(api_url, headers=headers, json=request_body)
#         response.raise_for_status()
#         data = response.json()
        
#         if isinstance(data, list) and len(data) > 0:
#             df = pd.DataFrame(data)
#             return df
#         else:
#             print("No data returned")
#             return pd.DataFrame()
            
#     except Exception as e:
#         print(f"Error: {e}")
#         return pd.DataFrame()

# # Main execution
# if __name__ == "__main__":
#     # Get access token
#     print("Authenticating with FINRA API...")
#     token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    
#     if token:
#         print("Authentication successful!")
        
#         # Get corporate bond market breadth data
#         print("\nFetching corporate bond market breadth data...")
#         breadth_df = get_corporate_market_breadth(token)
        
#         if not breadth_df.empty:
#             print("\nCorporate Bond Market Breadth Data:")
#             print(breadth_df.head())
#             print(f"\nColumns available: {breadth_df.columns.tolist()}")
            
#             # Save to CSV
#             breadth_df.to_csv('finra_corporate_bonds_breadth.csv', index=False)
#             print("\nData saved to 'finra_corporate_bonds_breadth.csv'")
        
#         # Example: Get treasury data (this works with free public credentials)
#         print("\n\nFetching treasury data as example...")
#         treasury_df = get_treasury_data(token)
        
#         if not treasury_df.empty:
#             print("\nTreasury Data:")
#             print(treasury_df.head())
#     else:
#         print("Failed to authenticate. Check your credentials.")



from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import time

class Quote(BaseModel):
    timestamp: datetime
    symbol: str
    price: float
    day_high: float
    day_low: float
    open: float
    volume: int

def retrieve_live_quotes(tickers: list[str]):
    fmp_api = FMP_API_DATA()
    quotes = fmp_api.get_batch_quote(tickers)
    
    quotes = {d["symbol"]: d for d in quotes}

    x = []

    for symbol, quote in quotes.items():
        quote = Quote(
            timestamp=get_current_utc_time().replace(second=0, microsecond=0),
            symbol=symbol,
            price=quote["price"],
            day_high=quote["dayHigh"],
            day_low=quote["dayLow"],
            open=quote["open"],
            volume=quote["volume"]
        )
        x.append(quote)
    

    return x

def stream(tickers: list[str], output_file: str = "live_quotes.csv", start_time: str = None, end_time: str = None):
    """
    Stream live quote data for given tickers, updating every minute.

    Args:
        tickers: List of ticker symbols to stream
        output_file: CSV filename to save data (default: "live_quotes.csv")
        start_time: Time to start streaming in "HH:MM" format (e.g., "09:30"). If None, starts immediately.
        end_time: Time to stop streaming in "HH:MM" format (e.g., "16:00"). If None, runs indefinitely.

    Returns:
        DataFrame containing all collected quotes with columns:
        timestamp, symbol, price, day_high, day_low, open, volume
    """
    # Initialize empty dataframe
    df = pd.DataFrame()

    # Wait until start_time if provided
    if start_time:
        start_hour, start_minute = map(int, start_time.split(':'))
        while True:
            current_time = get_current_utc_time()
            if current_time.hour > start_hour or (current_time.hour == start_hour and current_time.minute >= start_minute):
                break
            wait_seconds = ((start_hour - current_time.hour) * 3600 + 
                           (start_minute - current_time.minute) * 60 - 
                           current_time.second)
            print(f"Waiting until {start_time} to start streaming... ({wait_seconds} seconds)")
            time.sleep(min(60, wait_seconds))
        print(f"Starting stream at {start_time}")

    try:
        while True:
            # Check if we've reached end_time
            if end_time:
                end_hour, end_minute = map(int, end_time.split(':'))
                current_time = get_current_utc_time()
                if current_time.hour > end_hour or (current_time.hour == end_hour and current_time.minute >= end_minute):
                    print(f"\nReached end time {end_time}")
                    print(f"Final dataframe contains {len(df)} records")
                    print(f"Data saved to {output_file}")
                    return df

            # Retrieve live quotes
            quotes = retrieve_live_quotes(tickers)

            # Convert quotes to dataframe rows
            quote_dicts = [quote.model_dump() for quote in quotes]
            new_df = pd.DataFrame(quote_dicts)

            # Append to main dataframe
            df = pd.concat([df, new_df], ignore_index=True)

            # Write to CSV file
            df.to_csv(output_file, index=False)
            
            print(f"Updated {output_file} - Total records: {len(df)}")
            print(df.tail(len(tickers)))

            # Reason: Calculate seconds until next minute to sync to top of minute
            # If started at 7:52:37, next update will be at 7:53:00
            current_time = get_current_utc_time()
            seconds_until_next_minute = 60 - current_time.second
            time.sleep(seconds_until_next_minute)

    except KeyboardInterrupt:
        print("\n\nStreaming stopped by user")
        print(f"Final dataframe contains {len(df)} records")
        print(f"Data saved to {output_file}")
        return df

    return df


if __name__ == "__main__":
    # Example usage: stream quotes for a list of tickers
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "SPY", "QQQ", "IWM", "DIA"]

    # Start streaming with specific start and end times (UTC)
    # Example: Start at 2:30 PM UTC (9:30 AM EST), end at 9:00 PM UTC (4:00 PM EST)
    df = stream(tickers, start_time="15:50", end_time="21:00")
    

