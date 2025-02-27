from xbbg import blp
import pandas as pd
from datetime import datetime, timedelta

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