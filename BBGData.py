from xbbg import blp
import pandas as pd
from datetime import datetime, timedelta
import requests
import json
import psycopg2


def get_fixed_income_data(ticker):
    # Define the ticker and fields
    fields = ["PX_LAST", "YLD_YTM_BID", "YLD_YTM_ASK"]

    # Set end date to current date and calculate start date
    end_date = datetime.now()  # This will use the actual current date
    start_date = end_date - timedelta(days=20*365)

    # Convert dates to strings in the format Bloomberg expects
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch historical data for the last 3 years
    historical_data = blp.bdh(ticker, fields, start_date_str, end_date_str)

    # Display the data
    # print(historical_data)
    return historical_data

# df = pd.read_excel("RatesTickers.xlsx", sheet_name="FI")

# for ticker in df["Tickers"]:
#     # print(df[df["Tickers"] == ticker]["Category"].values[0])
    
#     d = get_fixed_income_data(ticker)
#     if d.empty:
#         print(ticker)

def commodity_data(ticker):
    # Define the ticker and fields for NGA comdty data
    ticker = "NGA Comdty"
    fields = ["PX_LAST", "PX_LOW", "PX_HIGH", "PX_OPEN", "PX_VOLUME"]

    # Set end date to current date and calculate start date for the last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15*365)

    # Convert dates to strings in the format Bloomberg expects
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch historical NGA comdty data for the last 6 months in 15-minute intervals
    historical_data = blp.bdh(ticker, fields, start_date_str, end_date_str)

    # Display the data
    print(historical_data)


