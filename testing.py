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


from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.db.core.pull_fmp_data import FMP_API_DATA

with MarketSession() as session:
    ticker_obj = (
        session.query(Ticker)
        .filter(Ticker.ticker == "AAPL")
        .first()
    )

fmp_api = FMP_API_DATA()
company_profile = fmp_api.get_company_profile("AAPL")

ticker_obj.description = company_profile[0]["description"]

data = serialize_sqlalchemy_obj(ticker_obj)
data["description"] = ticker_obj.description  # <-- add here

print(data)
