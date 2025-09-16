import json

# Use helper from file_utils to resolve the new path of the schema file
from .file_utils import get_schema_path

# Resolve the canonical path to the schema JSON inside ``src/data/database``
DATABASE_SCHEMA_PATH = str(get_schema_path())

def is_etf_ticker(ticker: str) -> bool:
    """Checks if the given ticker is an ETF by looking in the etf_data section of the database schema.

    Args:
        ticker: The ticker symbol to check (e.g., 'SPY', 'QQQ').

    Returns:
        True if the ticker is found in any ETF data schema,
        False otherwise.
    """
    try:
        with open(DATABASE_SCHEMA_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Database schema file not found at {DATABASE_SCHEMA_PATH}")
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {DATABASE_SCHEMA_PATH}")
        return False

    try:
        # Get the etf_data section
        etf_data = data.get('etf_data', {})
        etf_schemas = etf_data.get('schemas', {})
        
        # Convert ticker to uppercase for consistent comparison
        ticker = ticker.upper()
        
        # Search through all ETF schemas and tables
        for schema_name, schema_data in etf_schemas.items():
            tables = schema_data.get('tables', {})
            for table_name, table_data in tables.items():
                tickers = table_data.get('tickers', [])
                if ticker in tickers:
                    return True
                    
        return False
        
    except Exception as e:
        print(f"An unexpected error occurred while checking ETF data: {e}")
        return False

def is_etf_asset_class(asset_class: str) -> bool:
    """Checks if the given asset class is an ETF asset class by looking for the table name in the etf_data section.

    Args:
        asset_class: The asset class (table name) to check (e.g., 'crypto', 'energy', 'us_major_index').

    Returns:
        True if the asset class is found as a table within any ETF data schema,
        False otherwise.
    """
    try:
        with open(DATABASE_SCHEMA_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Database schema file not found at {DATABASE_SCHEMA_PATH}")
        return False
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {DATABASE_SCHEMA_PATH}")
        return False

    try:
        # Get the etf_data section
        etf_data = data.get('etf_data', {})
        etf_schemas = etf_data.get('schemas', {})
        
        # Search through all ETF schemas for the asset class as a table name
        for schema_name, schema_data in etf_schemas.items():
            tables = schema_data.get('tables', {})
            if asset_class in tables:
                return True
                
        return False
        
    except Exception as e:
        print(f"An unexpected error occurred while checking ETF asset classes: {e}")
        return False

if __name__ == "__main__":
    # Test with a few known ETFs
    print(f"SPY is ETF: {is_etf_ticker('SPY')}")
    print(f"QQQ is ETF: {is_etf_ticker('QQQ')}")
    print(f"AAPL is ETF: {is_etf_ticker('AAPL')}")  # Should be False
    
    # Test ETF asset classes
    print(f"crypto is ETF asset class: {is_etf_asset_class('crypto')}")
    print(f"energy is ETF asset class: {is_etf_asset_class('hedge_fund_replication')}")
    print(f"us_major_index is ETF asset class: {is_etf_asset_class('other_specialized_reits')}")
    print(f"invalid_class is ETF asset class: {is_etf_asset_class('industrial_metals')}")  # Should be False