import xml.etree.ElementTree as ET
import os
from ib_insync import IB, Stock, util
import pandas as pd
import json

from finvizfinance.quote import finvizfinance

def get_asset_description(ticker):

    # Create a finvizfinance object for the ETF
    etf = finvizfinance(ticker)

    # Get only the description of the ETF
    etf_description = etf.ticker_description()

    # Print the description
    print(etf_description)

    return etf_description


get_asset_description('QAI')