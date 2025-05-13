# --- NEW IMPORTS ---
import os
import json
import pandas as pd
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

from ib_insync import Stock

# Project utility imports
from src.utils.ib_utils import get_ib, disconnect_from_ib
from src.utils.file_utils import load_schema_data
from src.utils.database import get_default_db_config
from sqlalchemy import create_engine, text
# --- END NEW IMPORTS ---

def get_quarterly_estimates(ticker: str) -> str:
    """
    Connects to IB, fetches quarterly fundamental estimates for a given ticker,
    filters for Q2 2025 onwards, and returns them as a compact JSON string.
    
    Parameters:
    - ticker: The stock ticker symbol (e.g., "AAPL")
    
    Returns:
    - A JSON string containing the quarterly estimates or an error message.
    """
    # Obtain a connected IB instance using the shared utility
    ib = get_ib()

    # Bail out early if connection could not be established
    if ib is None or not ib.isConnected():
        return json.dumps({"error": "Unable to connect to Interactive Brokers."})

    try:
        # Try with SMART exchange first; fall back to primary US exchanges if no data returned
        exchanges_to_try = ["SMART", "NASDAQ", "NYSE", "AMEX"]
        xml_data = None
        for exch in exchanges_to_try:
            contract = Stock(ticker, exch, "USD")
            try:
                xml_data = ib.reqFundamentalData(contract, reportType="RESC")
            except Exception:
                xml_data = None

            if xml_data:
                break  # Successfully received data

        if not xml_data:
            error_json = json.dumps({"error": f"Failed to retrieve fundamental data for {ticker}."})
            return error_json

        # Parse XML
        root = ET.fromstring(xml_data)

        # Define metrics to extract
        metrics = ["EPS", "SREV", "EBITD", "CFSHR", "SCEX", "EBIT", "BVPS", "GROSMGN", "NETDEBT", "ROEPCT"]

        # Store results - Only quarterly
        results_data = {
            "quarterly_estimates": [] # Initialize as list
        }

        # Extract quarterly estimates for each metric
        quarterly_data_frames = []
        for metric in metrics:
            # --- Inlined extract_estimates logic for period_type="Q" ---
            metric_estimates = []
            # Find all FYEstimate elements with specified type
            for fy_estimate in root.findall(f'.//FYEstimate[@type="{metric}"]'):
                # Find all FYPeriod elements with periodType="Q"
                for period in fy_estimate.findall('./FYPeriod[@periodType="Q"]'):
                    year = period.get('fYear')
                    quarter = period.get('periodNum') # Should always exist for quarterly

                    if not year or not quarter: # Basic validation
                        continue

                    # Handle period identifier (year+quarter)
                    period_id = f"{year} Q{quarter}"

                    # Find the Mean ConsEstimate
                    mean_estimate = period.find('./ConsEstimate[@type="Mean"]')
                    if mean_estimate is not None:
                        # Find the current ConsValue
                        value_element = mean_estimate.find('./ConsValue[@dateType="CURR"]')
                        if value_element is not None and value_element.text:
                            try:
                                metric_estimates.append((period_id, float(value_element.text)))
                            except ValueError:
                                continue # Skip if value is not a valid float
            # --- End Inlined Logic ---

            if metric_estimates:
                # Sort by year and quarter
                metric_estimates.sort(key=lambda x: (int(x[0].split()[0]), int(x[0].split()[1][1:])))
                # Create a DataFrame for the current metric
                df = pd.DataFrame(metric_estimates, columns=['Period', metric])
                df.set_index('Period', inplace=True)
                quarterly_data_frames.append(df)

        # Combine all quarterly DataFrames into one
        if quarterly_data_frames:
            quarterly_df = pd.concat(quarterly_data_frames, axis=1, sort=True)

            # Handle potential NaNs introduced by concat if periods don't align perfectly
            quarterly_df.fillna(value=pd.NA, inplace=True)

            # Filter out rows where the index is not in 'YYYY QQ' format before multi-index creation
            valid_indices = [idx for idx in quarterly_df.index if isinstance(idx, str) and len(idx.split()) == 2 and idx.split()[1].startswith('Q')]
            quarterly_df = quarterly_df.loc[valid_indices]

            if not quarterly_df.empty: # Proceed only if there are valid rows left
                # Sort the final DataFrame by period (Year, Quarter)
                quarterly_df.index = pd.MultiIndex.from_tuples(
                    [(int(idx.split()[0]), int(idx.split()[1][1:])) for idx in quarterly_df.index],
                    names=['Year', 'Quarter']
                )
                quarterly_df.sort_index(inplace=True)

                # --- Filtering Step ---
                # Filter for data from Q2 2025 onwards
                min_year = 2025
                min_quarter = 2
                quarterly_df = quarterly_df[
                    (quarterly_df.index.get_level_values('Year') > min_year) |
                    ((quarterly_df.index.get_level_values('Year') == min_year) &
                     (quarterly_df.index.get_level_values('Quarter') >= min_quarter))
                ]
                # --- End Filtering Step ---

                # Convert DataFrame to a list of dictionaries for JSON serialization only if not empty
                if not quarterly_df.empty:
                    quarterly_df_reset = quarterly_df.reset_index()
                    # Replace NaN/NA with None for JSON compatibility
                    quarterly_df_reset = quarterly_df_reset.where(pd.notna(quarterly_df_reset), None)
                    results_data["quarterly_estimates"] = quarterly_df_reset.to_dict(orient='records')
                # If filtering results in an empty DataFrame, results_data["quarterly_estimates"] remains []

        # Output the results as a compact JSON string
        return json.dumps(results_data)

    except ET.ParseError as e:
        print(f"Error parsing XML for {ticker}: {e}")
        return json.dumps({"error": f"Invalid XML received for {ticker}."})
    except ConnectionRefusedError as e:
         print(f"Connection refused when connecting to IB for {ticker}. Is TWS/Gateway running and API enabled? Error: {e}")
         return json.dumps({"error": "Connection to IB Gateway/TWS refused."})
    except Exception as e:
        # Consider more specific error logging/handling
        print(f"Error in get_quarterly_estimates for {ticker}: {type(e).__name__} - {e}") # Log type of error
        
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})
    finally:
        # Do NOT disconnect here – let the caller manage the lifecycle to avoid reconnecting for every ticker
        pass

# --- NEW CODE: Bulk retrieval & database push ---

def _get_sqlalchemy_engine(db_name: str):
    """Create a SQLAlchemy engine for the given database using default env config."""
    db_cfg = get_default_db_config()
    if not db_cfg or not all(db_cfg.values()):
        raise ValueError("Database environment variables (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT) must be set.")

    conn_str = (
        f"postgresql://{db_cfg['user']}:{db_cfg['password']}@{db_cfg['host']}:{db_cfg['port']}/{db_name}"
    )
    return create_engine(conn_str, pool_pre_ping=True)


def _push_estimates_dataframe(
    df: pd.DataFrame,
    db_name: str,
    schema_name: str,
    table_name: str,
) -> None:
    """Append the given DataFrame to ``schema_name.table_name`` (auto-creates if needed)."""
    if df.empty:
        return  # Nothing to insert

    # Ensure column names are lowercase and safe for SQL
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    engine = _get_sqlalchemy_engine(db_name)

    # Ensure schema exists (except for default 'public')
    if schema_name != "public":
        with engine.begin() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

    # Use pandas to_sql with "append" behaviour. Auto-creates table.
    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema_name,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )


def update_all_ticker_fundamental_estimates(min_year: int = 2025, min_quarter: int = 2,
                                            start_sector: str | None = None,
                                            start_schema: str | None = None) -> None:
    """Loop through every ticker in database_schemas.json, fetch quarterly estimates and store them in the DB."""

    schema_data = load_schema_data()
    if not schema_data:
        print("⚠️ Could not load database schema definitions. Aborting.")
        return

    processed_tickers: set[str] = set()

    resume_started = start_sector is None  # If no start_sector provided, start immediately

    for sector_name, sector_info in schema_data.items():
        # Skip ETF sectors (they don't have fundamentals from IB)
        if "etf" in sector_name.lower():
            continue

        # If resume point not reached yet, skip sectors until we match start_sector
        if not resume_started:
            sector_key_match = sector_name == start_sector or sector_info.get("database") == start_sector
            if sector_key_match:
                resume_started = True
            else:
                continue  # Still skipping until we reach desired sector

        base_db_name = sector_info.get("database")
        if not base_db_name:
            continue
        fundamentals_db = f"{base_db_name}_fundamentals"

        # Iterate schemas, possibly skipping until start_schema if provided and resume just started
        schemas_iter = sector_info.get("schemas", {}).items()
        for schema_name, schema_info in schemas_iter:
            if start_schema and resume_started and start_schema != schema_name and sector_name == start_sector and not processed_tickers:
                # Skip schemas before the start_schema only in the first sector iteration
                continue

            # Collect tickers for this schema
            schema_tickers: List[str] = []
            for table_details in schema_info.get("tables", {}).values():
                schema_tickers.extend(table_details.get("tickers", []))

            if not schema_tickers:
                continue

            print(f"\n📚 Processing {len(schema_tickers)} tickers in {fundamentals_db}.{schema_name} …")

            # Process each ticker individually so we can store in its own table
            for ticker in schema_tickers:
                ticker = ticker.upper()
                if ticker in processed_tickers:
                    continue  # Avoid duplicate API calls if ticker appears in multiple tables

                try:
                    estimates_json_str = get_quarterly_estimates(ticker)
                    estimates_data: Dict[str, Any] = json.loads(estimates_json_str)
                except Exception as e:
                    print(f"❌ Failed to fetch/parse estimates for {ticker}: {e}")
                    processed_tickers.add(ticker)
                    continue

                # If IB returned an error (e.g., code 430 - no data) skip further processing
                if "error" in estimates_data:
                    print(f"⚠️  No fundamental data available for {ticker}: {estimates_data['error']}")
                    processed_tickers.add(ticker)
                    continue

                estimates_list = estimates_data.get("quarterly_estimates", [])
                if not estimates_list:
                    processed_tickers.add(ticker)
                    continue  # Nothing to store

                df = pd.DataFrame(estimates_list)
                if df.empty:
                    continue

                # No global table; store without extra ticker column to avoid redundancy

                # Push immediately into <ticker>_fundamental_estimates table
                table_name = f"{ticker.lower()}_fundamental_estimates"
                try:
                    _push_estimates_dataframe(df, fundamentals_db, schema_name, table_name)
                    print(
                        f"✅ Inserted/updated {len(df)} rows into {fundamentals_db}.{schema_name}.{table_name}"
                    )
                except Exception as db_err:
                    print(
                        f"🚨 Database insertion error for {fundamentals_db}.{schema_name}.{table_name}: {db_err}"
                    )

                processed_tickers.add(ticker)

    print("\n🎉 Finished updating quarterly fundamental estimates for all tickers.")

    # Disconnect from IB once all processing is complete
    disconnect_from_ib()


if __name__ == "__main__":
    # Run the update when this script is executed directly
    # Allow simple resume by environment variables or command-line arguments
    import sys, os

    # Usage: python -m ...update_fundamental_predictions <start_sector> <start_schema>
    # cli_args = sys.argv[1:]
    # start_sector = cli_args[0] if len(cli_args) >= 1 else os.environ.get("RESUME_START_SECTOR")
    # start_schema = cli_args[1] if len(cli_args) >= 2 else os.environ.get("RESUME_START_SCHEMA")
    start_sector = 'equity_sector_consumer_discretionary'
    start_schema = 'diversified_consumer_services'
    update_all_ticker_fundamental_estimates(start_sector=start_sector, start_schema=start_schema)




# --- END NEW CODE ---
