"""
Author: @Michael Laret
=====================================================================
This file retrieves the averages of fundamental data for a given ticker and sector from the database.
It then writes a fundamental analysis report for the ticker using the averages and the DeepSeek LLM.
"""

import os
import json
import pandas as pd
import numpy as np
from openai import OpenAI
from src.utils.caching import cache_result
from src.phaseTwo.data_retrieval import get_fundamentals_data
import psycopg2
from src.utils.file_utils import load_schema_data
from src.utils.database import get_default_db_config, get_cursor

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load environment variables
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_model = os.environ.get("DEEPSEEK_MODEL")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# Data retrieval functions
def get_sector_averages(ticker):
    """
    Locate the sector database for the supplied ``ticker`` and return the
    dictionary of sector‐level average fundamentals stored in
    sector_averages.averages_table.

    The helper walks the ``database_schemas.json`` structure (via
    ``load_schema_data``) to find which sector the ticker belongs to, then
    connects to the corresponding *fundamentals* database using the default
    credentials from the ``.env`` file. Only the first row of the averages
    table is returned because the ETL that creates this table keeps a single
    record containing the latest run-level averages.
    """
    schema_data = load_schema_data()
    ticker_upper = ticker.upper()

    # ---------- 1️⃣  find sector & database ----------
    sector_db = None
    for sector_name, sector_info in schema_data.items():
        for schema_name, schema_info in sector_info.get("schemas", {}).items():
            for table_cat, table_data in schema_info.get("tables", {}).items():
                # table_data contains {"tickers": [...]}  
                tickers = table_data.get("tickers", [])
                if any(t.upper() == ticker_upper for t in tickers):
                    # sector_info["database"] holds e.g. "equity_sector_energy"
                    base_db = sector_info.get("database")
                    if base_db:
                        sector_db = f"{base_db}_fundamentals"  # append suffix
                    break
            if sector_db:
                break
        if sector_db:
            break

    if not sector_db:
        print(f"Sector database not found for ticker {ticker_upper}.")
        return {}

    # ---------- 2️⃣  query sector averages ----------
    db_config = get_default_db_config()
    try:
        with get_cursor(dbname=sector_db, db_config=db_config) as cur:
            cur.execute('SELECT * FROM "sector_averages"."averages_table" LIMIT 1')
            row = cur.fetchone()
            if row is None:
                return {}
            col_names = [desc[0] for desc in cur.description]
            # Exclude technical columns like run_id if present
            return {col: row[idx] for idx, col in enumerate(col_names) if col not in ("run_id",)}
    except psycopg2.Error as e:
        print(f"Database error while fetching sector averages for {ticker_upper}: {e}")
        return {}

def get_ticker_averages(ticker):
    """
    Calculate the average of each fundamental metric for ``ticker`` limited to
    the set of columns present in the sector averages. The function pulls all
    available data through ``get_fundamentals_data`` and computes simple means
    (ignoring NULL / non-numeric values).
    """
    sector_avgs = get_sector_averages(ticker)
    if not sector_avgs:
        return {}

    target_cols = list(sector_avgs.keys())
    raw_data = get_fundamentals_data(ticker)
    if not raw_data:
        return {}

    # collect numeric values for each column across all fundamental tables
    values_map = {col: [] for col in target_cols}

    def _to_float(val):
        try:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            return float(str(val).replace(',', ''))
        except (ValueError, TypeError):
            return None

    for table_data in raw_data.values():  # balance_sheets, etc.
        for record in table_data:
            for col in target_cols:
                if col in record:
                    num = _to_float(record[col])
                    if num is not None and not (isinstance(num, float) and (np.isnan(num) or np.isinf(num))):
                        values_map[col].append(num)

    ticker_avgs = {}
    for col, vals in values_map.items():
        ticker_avgs[col] = float(np.mean(vals)) if vals else None

    return ticker_avgs

# Fundamental analysis functions
def debug_json_encoding(data, ticker):
    """
    Debug function to identify which fields are causing JSON encoding issues.
    
    Args:
        data (list): List of dictionaries to encode
        ticker (str): Ticker symbol for logging
        
    Returns:
        tuple: (success_flag, error_message)
    """
    print(f"DEBUG: Testing JSON encoding for {ticker} item by item")
    
    # First try individual records
    for i, record in enumerate(data):
        try:
            json.dumps(record)
        except Exception as e:
            print(f"  Failed to encode record {i}: {e}")
            
            # Try each field individually
            for key, value in record.items():
                try:
                    json.dumps({key: value})
                except Exception as e:
                    print(f"    Problem field: '{key}' with value '{value}' (type: {type(value)}): {e}")
                    
                    # Try to fix this problematic field
                    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                        record[key] = None
                        print(f"      Fixed by replacing with None")
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        record[key] = str(value)
                        print(f"      Fixed by converting to string: '{record[key]}'")
                    else:
                        record[key] = None
                        print(f"      Fixed by replacing with None")
    
    # Try with fixed data
    try:
        json_str = json.dumps(data)
        print(f"  Final JSON encoding successful: {len(json_str)} bytes")
        return True, json_str
    except Exception as e:
        print(f"  Final JSON encoding still failed: {e}")
        return False, str(e)

def generate_fundamental_analysis_report(ticker):
    """
    Analyze fundamental data for a specific stock using LLM
    
    Args:
        ticker (str): The stock ticker symbol
        
    Returns:
        str: Analysis results
    """
    # Get fundamental data - specifically financial_metrics only
    raw_data = get_fundamentals_data(ticker)
    if not raw_data or 'financial_metrics' not in raw_data:
        print(f"DEBUG: No fundamental data found for {ticker}")
        return f"No fundamental data found for {ticker}"
        
    # --- Get sector average columns to define metrics ---
    sector_avgs = get_sector_averages(ticker)
    if not sector_avgs:
        print(f"Could not retrieve sector averages for {ticker}. Cannot determine metrics.")
        return f"Could not retrieve sector averages for {ticker} to determine which metrics to analyze."
        
    # Target columns from sector averages, plus always include 'date' and 'ticker'
    target_cols = ['date', 'ticker'] + list(sector_avgs.keys())
    
    # Define mandatory base columns and specific requested metrics
    mandatory_cols = ['date', 'ticker', 'debt_to_equity', 'inventory_turnover']

    # Get columns from sector averages
    sector_avg_cols = list(sector_avgs.keys())

    # Combine mandatory and sector average columns, removing duplicates
    target_cols = list(set(mandatory_cols + sector_avg_cols))
    
    print(f"DEBUG: Using target columns (mandatory + sector averages) for {ticker}: {target_cols}")
    # --- End of changes ---

    # Combine data from all tables, merging by date
    data_by_date = {}
    for table_type, table_data in raw_data.items():
        if not isinstance(table_data, list):
            print(f"Warning: Data for table type '{table_type}' is not a list, skipping.")
            continue
            
        print(f"Processing {len(table_data)} records from {table_type}")
        for item in table_data:
            if not isinstance(item, dict):
                print(f"Warning: Skipping non-dictionary item in {table_type}: {type(item)}")
                continue
                
            date = item.get('date')
            if not date:
                # print(f"Warning: Skipping item with no date in {table_type}: {item}")
                continue
                
            if date not in data_by_date:
                data_by_date[date] = {'date': date, 'ticker': ticker.upper()}
            
            # Add/update metrics from target_cols found in this item
            for col in target_cols:
                if col in item and item[col] is not None: # Check if col exists in the item
                    # Only add if not already present or if the existing value is None
                    if col not in data_by_date[date] or data_by_date[date].get(col) is None:
                         data_by_date[date][col] = item[col]

    # Convert merged data dict to a list
    merged_data = list(data_by_date.values())
    
    # Sort by date
    merged_data.sort(key=lambda x: x.get('date', ''))
    
    print(f"Found {len(merged_data)} records after merging data across tables for {ticker}")

    # Final filter: Only keep records that have at least one target metric (besides date/ticker)
    filtered_data = []
    for record in merged_data:
        has_data = False
        for col, value in record.items():
            if col not in ('date', 'ticker') and value is not None:
                has_data = True
                break
        if has_data:
            filtered_data.append(record)
        else:
             # Debugging why a record might be skipped after merging
            # print(f"DEBUG: Skipping merged record for {ticker} date {record.get('date')} due to all target metrics being None. Record: {record}")
            pass

    # Debug: Print filtered data structure
    print(f"DEBUG: Filtered data after merging and final filtering for {ticker}: {len(filtered_data)} records")

    # Check if raw_data has data
    if not raw_data:
        return f"No financial metrics found for {ticker}"
        
    print(f"Found {len(raw_data)} financial metric records for {ticker}")
    
    # Create system prompt
    system_prompt = f"""
Role: You are an expert Senior Financial Analyst specializing in fundamental equity analysis. 
Task: Generate an in-depth, comprehensive fundamental analysis report for a given company based on the provided time-series financial data.

The input data will be a JSON list of dictionaries, where each dictionary represents a quarterly period. The specific financial metrics included may vary but will be drawn from common fundamental indicators. The keys in the JSON dictionary will indicate the metric names (e.g., 'price_to_earnings_ratio', 'net_margin', 'revenue_growth', etc.), along with 'date' and 'ticker'.

Analyze the provided data points over time to identify trends, strengths, and weaknesses. Structure your report clearly, addressing relevant aspects like:
1.  **Valuation:** Analyze available valuation ratios (e.g., P/E, EV/EBITDA). Discuss trends and what they suggest about market expectations.
2.  **Profitability:** Examine available margin metrics (e.g., Gross, Operating, Net Margins) and profit growth indicators (e.g., EPS Growth). Discuss trends and health.
3.  **Growth:** Evaluate available growth metrics (e.g., Revenue Growth, EPS Growth). Discuss trends and sustainability.
4.  **Financial Health & Stability:** Assess available liquidity and leverage ratios (e.g., Current Ratio, Debt-to-Equity). Discuss trends and risk.
5.  **Cash Flow:** Look at available cash flow metrics (e.g., FCF per Share, FCF Yield). Discuss generation strength and trends.
6.  **Efficiency:** Analyze available efficiency ratios (e.g., Inventory Turnover), if present.
7.  **Trend Analysis:** Synthesize the trends observed across *all provided metrics*. Identify consistent patterns or warning signs.
8.  **Overall Fundamental Assessment:** Provide a concluding summary of the company's fundamental health based *solely* on the provided metrics. Identify key strengths/weaknesses evident from the data. State any limitations due to missing metrics compared to a standard analysis.

**IMPORTANT INSTRUCTIONS:**
- Adapt your analysis based on *which specific metrics are present* in the JSON data provided in the user message.
- Provide a detailed, in-depth analysis for each relevant section based on the available data. Go beyond simply stating the values; interpret what they mean for the company.
- Analyze the trends *over the period covered by the data*.
- Base your entire analysis *only* on the provided JSON data. Do not invent data or assume external knowledge beyond general financial principles and the metric names themselves.
- If data for a specific metric included in the JSON is consistently missing or unavailable (e.g., all values are null), state that clearly and explain the implication of not having that metric for the analysis.
- Structure the output clearly using headings for relevant sections (adapt the sections above based on data availability).
- Write in a professional, analytical tone suitable for an investment report.
- Keep the response around 2500 tokens.
- DO NOT INCLUDE THE LIMITATIONS OF THE DATA IN YOUR REPORT.

The specific columns included in the JSON data are: {', '.join(target_cols)}
"""

    try:
        # Sanitize data by converting non-serializable objects and removing problematic values
        sanitized_data = []
        for item in filtered_data:
            sanitized_item = {}
            for key, value in item.items():
                # Handle date objects
                if key == 'date' and isinstance(value, str):
                    # Ensure the date is in a valid format
                    sanitized_item[key] = value
                # Handle None, NaN, Inf values
                elif value is None:
                    sanitized_item[key] = None
                elif isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                    sanitized_item[key] = None
                else:
                    # Convert all other values to simple types
                    try:
                        # Try to convert to simpler types if needed
                        if isinstance(value, (int, float, str, bool)):
                            sanitized_item[key] = value
                        else:
                            sanitized_item[key] = str(value)
                    except:
                        # If conversion fails, just use None
                        sanitized_item[key] = None
            
            sanitized_data.append(sanitized_item)
        
        # Debug output - inspect the data before trying to encode
        print(f"DEBUG: Sanitized data for {ticker}:")
        if sanitized_data and len(sanitized_data) > 0:
            print(f"  First sanitized record: {sanitized_data[0]}")
        else:
            print("  Empty sanitized data")
        
        print(f"Preparing to encode data for {ticker} ({len(sanitized_data)} records)")
        
        # Use the debug function to find and fix problems
        success, json_result = debug_json_encoding(sanitized_data, ticker)
        
        if success:
            financial_data_json = json_result
            print(f"Successfully encoded JSON data for {ticker} - length: {len(financial_data_json)}")
            if len(financial_data_json) < 1000:  # Only print if it's not too large
                print(f"DEBUG: JSON data: {financial_data_json[:500]}...")
        else:
            # Fall back to a simplified approach if debug function fails
            print(f"Using simplified data for {ticker}")
            # Create a very simple list with only numbers and strings
            simple_data = []
            for item in sanitized_data:
                simple_item = {}
                for key, value in item.items():
                    if isinstance(value, (int, float)) and not (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                        simple_item[key] = value
                    elif isinstance(value, str):
                        simple_item[key] = value
                    else:
                        simple_item[key] = None
                simple_data.append(simple_item)
            
            financial_data_json = json.dumps(simple_data)
        

        sector_averages = get_sector_averages(ticker)
        ticker_averages = get_ticker_averages(ticker)

        # Create messages with the sanitized data
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Analyze the fundamental data for {ticker.upper()}. Here is the full historical financial data:\n{financial_data_json}. 
            Here are the sector averages:\n{sector_averages} for comparison. 
            Here are the ticker averages:\n{ticker_averages}. 
            """}
        ]

        # Make a single API call with the data already included
        response = client.chat.completions.create(
            model='deepseek-reasoner',
            messages=messages,
            max_tokens=3500,
            temperature=1.0
        )
        final_content = response.choices[0].message.content
        # Remove asterisks and strip whitespace
        final_content = final_content.replace('*', '').strip()
        # print(final_content) # Optionally print the cleaned content for debugging
        # Return the cleaned text content directly without any parsing
        return final_content
    except Exception as e:
        print(f"Error in fundamental analysis for {ticker}: {str(e)}")
        # Try with a simpler approach - convert to string directly
        try:
            print(f"Attempting fallback with str() for {ticker}")
            simple_data = str(filtered_data)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze the fundamental data for {ticker.upper()}. Here is the financial data (in string format):\n{simple_data}"}
            ]
            
            response = client.chat.completions.create(
                model=deepseek_model,
                messages=messages,
                max_tokens=1500,
                temperature=1.0
            )
            
            return response.choices[0].message.content
        except Exception as e2:
            print(f"Fallback also failed for {ticker}: {e2}")
            return f"Error analyzing fundamental data for {ticker}: {str(e)}" 

if __name__ == "__main__":
    print(generate_fundamental_analysis_report("AAPL"))