"""
Author: @Michael Laret
=====================================================================
This file contains the functions for the fundamental analysis.
It queries the pre generated fundamental report from the database.
"""
import os
import json
import pandas as pd
import numpy as np
from openai import OpenAI
from src.utils.caching import cache_result
from src.portfolio_optimization.phase_two.data_retrieval import get_fundamentals_data

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load environment variables
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_model = os.environ.get("DEEPSEEK_MODEL")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

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

# change this to query the fundamental report from the database given the ticker 
@cache_result
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
        
    fundamentals = raw_data['financial_metrics']
    
    # Debug: Print raw fundamentals data structure
    print(f"DEBUG: Raw fundamentals data for {ticker}:")
    if fundamentals and len(fundamentals) > 0:
        print(f"  First record type: {type(fundamentals[0])}")
        print(f"  Number of records: {len(fundamentals)}")
        if len(fundamentals) > 0:
            # Print keys from first record
            print(f"  Keys in first record: {list(fundamentals[0].keys())}")
            # Print a sample of values to check for problematic data
            print(f"  Sample values from first record:")
            for key, value in list(fundamentals[0].items())[:5]:  # Show first 5 items
                print(f"    {key}: {value} (type: {type(value)})")
    else:
        print("  Empty fundamentals data")
    
    # Check if fundamentals has data
    if not fundamentals:
        return f"No financial metrics found for {ticker}"
        
    print(f"Found {len(fundamentals)} financial metric records for {ticker}")
    
    # Filter to only include the specific metrics requested
    filtered_data = []
    for item in fundamentals:
        filtered_item = {
            'date': item.get('date'),
            'ticker': ticker.upper(),
            'price_to_earnings_ratio': item.get('price_to_earnings_ratio'),
            'enterprise_value_to_ebitda_ratio': item.get('enterprise_value_to_ebitda_ratio'),
            'net_margin': item.get('net_margin'),
            'revenue_growth': item.get('revenue_growth'),
            'current_ratio': item.get('current_ratio'),
            'debt_to_equity': item.get('debt_to_equity'),
            'free_cash_flow_per_share': item.get('free_cash_flow_per_share'),
            'inventory_turnover': item.get('inventory_turnover'),
            'earnings_per_share_growth': item.get('earnings_per_share_growth'),
            'free_cash_flow_yield': item.get('free_cash_flow_yield'),
            'operating_margin': item.get('operating_margin'),
            'gross_margin': item.get('gross_margin')
        }
        # Only add items that have at least some data
        filtered_data.append(filtered_item)
    
    # Debug: Print filtered data structure
    print(f"DEBUG: Filtered data for {ticker}:")
    if filtered_data and len(filtered_data) > 0:
        print(f"  First filtered record: {filtered_data[0]}")
    else:
        print("  Empty filtered data")

    # Create system prompt
    system_prompt = """
You are an expert Senior Financial Analyst specializing in fundamental equity analysis. Your task is to generate an in-depth, comprehensive fundamental analysis report for a given company based on the provided time-series financial data.

The input data will be a JSON list of dictionaries, where each dictionary represents a period (e.g., quarterly or annually) and contains the following key financial metrics:
- 'date': The date of the data point.
- 'ticker': The stock ticker symbol.
- 'price_to_earnings_ratio': P/E Ratio (Valuation)
- 'enterprise_value_to_ebitda_ratio': EV/EBITDA (Valuation)
- 'net_margin': Net Profit Margin (%) (Profitability)
- 'revenue_growth': Revenue Growth Rate (%) (Growth)
- 'current_ratio': Current Ratio (Liquidity/Financial Health)
- 'debt_to_equity': Debt-to-Equity Ratio (Leverage/Financial Health)
- 'free_cash_flow_per_share': FCF per Share (Cash Flow)
- 'inventory_turnover': Inventory Turnover (Efficiency)
- 'earnings_per_share_growth': EPS Growth Rate (%) (Growth/Profitability)
- 'free_cash_flow_yield': FCF Yield (%) (Cash Flow/Valuation)
- 'operating_margin': Operating Profit Margin (%) (Profitability)
- 'gross_margin': Gross Profit Margin (%) (Profitability)

Analyze the provided data points over time to identify trends, strengths, and weaknesses. Structure your report clearly, addressing the following aspects in detail:

1.  **Valuation:** Analyze the P/E and EV/EBITDA ratios. Are they high, low, or average compared to typical industry ranges (if known)? How have they trended? What does this suggest about market expectations?
2.  **Profitability:** Examine Gross, Operating, and Net Margins. Are they improving, declining, or stable? How healthy are they? Analyze EPS Growth trends.
3.  **Growth:** Evaluate Revenue Growth and EPS Growth trends. Is the company growing? Is the growth accelerating or decelerating?
4.  **Financial Health & Stability:** Assess the Current Ratio and Debt-to-Equity ratio. Does the company have sufficient liquidity? Is its debt level manageable? How have these metrics trended?
5.  **Cash Flow:** Look at Free Cash Flow per Share and FCF Yield. Is the company generating strong free cash flow? Is it improving? What does the FCF Yield indicate about valuation and cash generation relative to price?
6.  **Trend Analysis:** Synthesize the trends observed across all metrics. Are there consistent patterns (e.g., improving profitability alongside growth)? Are there warning signs (e.g., rising debt with falling margins)?
7.  **Overall Fundamental Assessment:** Provide a concluding summary of the company's fundamental health based *solely* on the provided metrics. Identify the key strengths and weaknesses evident from the data. State any limitations due to missing information (e.g., lack of industry comparison data).

**IMPORTANT INSTRUCTIONS:**
- Provide a detailed, in-depth analysis for each section. Go beyond simply stating the values; interpret what they mean for the company.
- Analyze the trends *over the period covered by the data*.
- Base your entire analysis *only* on the provided JSON data. Do not invent data or assume external knowledge beyond general financial principles.
- If data for a metric is consistently missing or unavailable (e.g., all values are null), state that clearly and explain the implication of not having that metric.
- Structure the output clearly using headings for each of the 7 sections listed above.
- Write in a professional, analytical tone suitable for an investment report.
- Do not include '#' or '*' characters in your response formatting.
- Keep the response around 1500 tokens.
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
        
        # Create messages with the sanitized data
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze the fundamental data for {ticker.upper()}. Here is the financial data:\n{financial_data_json}"}
        ]

        # Make a single API call with the data already included
        response = client.chat.completions.create(
            model=deepseek_model,
            messages=messages,
            max_tokens=2500,
            temperature=1.0
        )

        # Return the text content directly without any parsing
        return response.choices[0].message.content
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




