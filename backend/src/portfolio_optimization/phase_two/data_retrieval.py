import os
import pandas as pd
import psycopg2
from decimal import Decimal
from datetime import datetime, timedelta
from finvizfinance.quote import finvizfinance
import json 
from backend.src.utils.caching import cache_result
from backend.src.utils.file_utils import load_schema_data

@cache_result
def get_stock_tickers(asset_class):
    """
    Retrieve stock tickers from database schemas filtered by asset class.
    
    Searches database_schemas.json to find tickers matching the specified asset class,
    which can be a sector, industry, or subindustry classification.
    
    Args:
        asset_class: Asset class name to filter on, or None to return all tickers.
    
    Returns:
        Dict: Dictionary with asset_class as key and list of matching tickers as value,
        or {"all": tickers} if asset_class is None.
    """
    schema_data = load_schema_data()
    
    # List to store all matching tickers
    matching_tickers = []
    
    # If no filter is provided, return all tickers
    if asset_class is None:
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
                tables = schema_info.get('tables', {})
                
                for table_name, table_info in tables.items():
                    tickers = table_info.get('tickers', [])
                    matching_tickers.extend(tickers)
                    
        return {"all": matching_tickers}
    
    # Check if filter_value is a sector
    if asset_class in schema_data:
        # Filter by sector
        sector_info = schema_data[asset_class]
        schemas = sector_info.get('schemas', {})
        
        for schema_name, schema_info in schemas.items():
            tables = schema_info.get('tables', {})
            
            for table_name, table_info in tables.items():
                tickers = table_info.get('tickers', [])
                matching_tickers.extend(tickers)
    else:
        # Check for industry or subindustry match
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            for schema_name, schema_info in schemas.items():
                # Check if schema name matches the filter (industry)
                if schema_name == asset_class:
                    tables = schema_info.get('tables', {})
                    for table_name, table_info in tables.items():
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
                
                # Check for subindustry match in table names
                tables = schema_info.get('tables', {})
                for table_name, table_info in tables.items():
                    if table_name == asset_class:
                        tickers = table_info.get('tickers', [])
                        matching_tickers.extend(tickers)
    
    # Remove duplicates and sort list
    sorted_tickers = sorted(list(set(matching_tickers)))
    
    # Return dictionary with filter_value as key and ticker list as value
    return {asset_class: sorted_tickers}

def get_asset_description(ticker):
    """
    Retrieve ETF description using finvizfinance API.
    
    Fetches detailed description information for ETF tickers to provide
    context for investment analysis and portfolio construction.
    
    Args:
        ticker: ETF ticker symbol to get description for.
        
    Returns:
        str: Description text of the ETF, or None if retrieval fails.
    """
    # Create a finvizfinance object for the ETF
    etf = finvizfinance(ticker)

    # Get only the description of the ETF
    etf_description = etf.ticker_description()

    return etf_description

def extract_asset_classes(json_data):
    """
    Extract asset classes and allocations from portfolio JSON data.
    
    Parses portfolio JSON structure to extract asset class names and their
    corresponding allocation percentages, filtering out cash positions.
    
    Args:
        json_data: Dictionary containing portfolio data with asset class allocations.
        
    Returns:
        Dict: Dictionary mapping asset class names to allocation percentages,
        with cash positions excluded, or empty dict if parsing fails.
    """
    # Parse the JSON string
    data = json_data
    
    # Check if data has expected structure
    if not isinstance(data, dict):
        print("Error: Portfolio data is not a dictionary")
        return {}
    
    if "portfolio" not in data:
        print("Error: Portfolio data does not contain 'portfolio' key")
        return {}
    
    if not isinstance(data["portfolio"], list) or not data["portfolio"]:
        print("Error: Portfolio array is empty or not a list")
        return {}
    
    # Extract asset classes with allocations
    asset_classes = {}
    for item in data["portfolio"]:
        if not isinstance(item, dict):
            print(f"Warning: Portfolio item is not a dictionary: {item}")
            continue
            
        asset_class = item.get("asset_class")
        allocation = item.get("allocation")
        
        if not asset_class:
            print(f"Warning: Missing 'asset_class' in portfolio item: {item}")
            continue
            
        if allocation is None:
            print(f"Warning: Missing 'allocation' in portfolio item: {item}")
            continue
        
        # Convert allocation to float if it's a string (handle % if present)
        if isinstance(allocation, str):
            allocation = float(allocation.strip("%"))
        
        asset_classes[asset_class] = allocation
    
    # Filter out 'cash' from the dictionary
    asset_classes = {k: v for k, v in asset_classes.items() if k.lower() != 'cash'}
    
    if not asset_classes:
        print("Warning: No valid asset classes found in portfolio data")
        
    return asset_classes

