from xbbg import blp
import pandas as pd
from datetime import datetime, timedelta
import requests
import json


def get_fixed_income_data(ticker):
    # Define the ticker and fields
    ticker = "FDTR Index"
    fields = ["PX_LAST"]

    # Set end date to current date and calculate start date
    end_date = datetime.now()  # This will use the actual current date
    start_date = end_date - timedelta(days=20*365)

    # Convert dates to strings in the format Bloomberg expects
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch historical data for the last 3 years
    historical_data = blp.bdh(ticker, fields, start_date_str, end_date_str)

    # Display the data
    print(historical_data)


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
