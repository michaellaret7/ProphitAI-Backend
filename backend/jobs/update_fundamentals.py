"""
Author: @Michael Laret
=====================================================================
Update fundamental data from the financialdatasets.ai API to the database.
1. Loop through the tickers in the database 
2. Get the most recent fundamental data for the ticker
3. Update the database with the new data
4. Repeat for all tickers
"""

import requests
import json

api_key = '7b14137a-24fa-45d3-a752-6889558f551f'
ticker = "AAPL"
period = "quarterly"
limit = "100"

def get_financial_data(ticker, period, limit):
    """
    Fetch financial data from external API and return formatted results.
    
    Makes API calls to get income statements, balance sheets, cash flow statements,
    and financial metrics for a specified ticker symbol.
    
    Args:
        ticker: Stock ticker symbol to retrieve data for.
        period: Data frequency - "quarterly" or "annual".
        limit: Number of periods to retrieve (e.g., "100").
        
    Returns:
        Dict: Combined financial data including statements and metrics.
    """
    # First API call - Get income statements, balance sheets, and cash flow statements
    financials_url = "https://api.financialdatasets.ai/financials"
    
    querystring = {"ticker": ticker, "period": period, "limit": limit}
    headers = {"X-API-KEY": api_key}
    
    financials_response = requests.request("GET", financials_url, headers=headers, params=querystring)
    financials_data = json.loads(financials_response.text)
    
    # Second API call - Get financial metrics
    metrics_url = "https://api.financialdatasets.ai/financial-metrics"
    
    metrics_response = requests.request("GET", metrics_url, headers=headers, params=querystring)
    metrics_data = json.loads(metrics_response.text)
    
    # Combine the data
    combined_data = financials_data
    if "financial_metrics" in metrics_data:
        combined_data["financial_metrics"] = metrics_data["financial_metrics"]
    
    # Display nicely formatted JSON
    print("\n=== COMPLETE FINANCIAL DATA ===\n")
    print(json.dumps(combined_data, indent=2))

    return combined_data