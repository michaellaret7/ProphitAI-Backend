import json

DATABASE_SCHEMA_PATH = "src/data/database_schemas.json"

def is_etf(asset_class: str) -> bool:
    """Checks if the given asset class exists as a table within the ETF database schemas.

    Args:
        asset_class: The name of the asset class (table) to check.

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
        etf_schemas = data.get('etf_data', {}).get('schemas', {})
        for schema_name, schema_data in etf_schemas.items():
            tables = schema_data.get('tables', {})
            if asset_class in tables:
                return True # Found the asset class as a table name
        return False # Did not find the asset class in any ETF schema tables
    except Exception as e:
        print(f"An unexpected error occurred while checking ETF schemas: {e}")
        return False

