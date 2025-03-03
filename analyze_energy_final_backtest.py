import pandas as pd
import numpy as np
from decimal import Decimal
from openai import OpenAI
import os
import json
import traceback
import re
import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from AgentBuilding import NLPDatabaseAgent

# Connect to the energy sector database to get current market data
agent = NLPDatabaseAgent(database="equity_sector_energy", use_nlp=False)

# Get current market data for oil and gas equipment and services companies
print("Getting market data for energy equipment and services companies...")
agent.cursor.execute("""
    SELECT ticker, short_name, p_e, price_d_1, market_cap, ebitda_t12m, 
           net_debt_to_ebitda_lf, alpha_m_3, beta_m_3
    FROM energy_equipment_and_services.oil_and_gas_equipment_and_services
""")
market_data = agent.cursor.fetchall()
market_columns = [desc[0] for desc in agent.cursor.description]

# Convert to DataFrame and clean data
df = pd.DataFrame(market_data, columns=market_columns)

# Extract ticker symbol (remove exchange suffix)
df['ticker_symbol'] = df['ticker'].apply(lambda x: x.split(' ')[0])

# Force numeric types for key metrics
df['p_e'] = pd.to_numeric(df['p_e'], errors='coerce')
df['price_d_1'] = pd.to_numeric(df['price_d_1'], errors='coerce')
df['market_cap'] = pd.to_numeric(df['market_cap'], errors='coerce')
df['ebitda_t12m'] = pd.to_numeric(df['ebitda_t12m'], errors='coerce')
df['net_debt_to_ebitda_lf'] = pd.to_numeric(df['net_debt_to_ebitda_lf'], errors='coerce')
df['alpha_m_3'] = pd.to_numeric(df['alpha_m_3'], errors='coerce')
df['beta_m_3'] = pd.to_numeric(df['beta_m_3'], errors='coerce')

# Connect to fundamentals database to get financial metrics
agent.connect_to_database("equity_sector_energy_fundamentals")

# Create a function to get financial metrics for a ticker
def get_financial_metrics(conn, ticker):
    """Get financial metrics for a ticker from the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'energy_equipment_and_services' 
                AND table_name = %s
            );
        """, (f"{ticker}_financial_metrics",))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"Warning: No financial metrics table found for {ticker}")
            return []
        
        # Get column names for the financial metrics table
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'energy_equipment_and_services' 
            AND table_name = %s;
        """, (f"{ticker}_financial_metrics",))
        columns = [row[0] for row in cursor.fetchall()]
        
        metrics_data = []
        if columns:
            # Build query with all columns
            columns_str = ', '.join(columns)
            query = f"""
                SELECT {columns_str}
                FROM energy_equipment_and_services.{ticker}_financial_metrics
                ORDER BY date DESC
            """
            cursor.execute(query)
            
            for row in cursor.fetchall():
                metrics_row = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    # Convert numeric strings to float for metrics
                    if value is not None and isinstance(value, (str, Decimal)) and column_name != 'date':
                        try:
                            metrics_row[column_name] = float(value)
                        except (ValueError, TypeError):
                            metrics_row[column_name] = value
                    else:
                        metrics_row[column_name] = value
                metrics_data.append(metrics_row)
        
        return metrics_data
    except Exception as e:
        print(f"Error getting financial metrics for {ticker}: {str(e)}")
        return []

# Get income statement data for a ticker
def get_income_data(conn, ticker):
    """Get income statement data for a ticker from the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'energy_equipment_and_services' 
                AND table_name = %s
            );
        """, (f"{ticker}_income_statements",))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"Warning: No income statements table found for {ticker}")
            return []
        
        # Get column names for the income statement table
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'energy_equipment_and_services' 
            AND table_name = %s;
        """, (f"{ticker}_income_statements",))
        columns = [row[0] for row in cursor.fetchall()]
        
        income_data = []
        if columns:
            # Build query with all columns
            columns_str = ', '.join(columns)
            query = f"""
                SELECT {columns_str}
                FROM energy_equipment_and_services.{ticker}_income_statements
                ORDER BY date DESC
            """
            cursor.execute(query)
            
            for row in cursor.fetchall():
                income_row = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    # Convert numeric strings to float for metrics
                    if value is not None and isinstance(value, (str, Decimal)) and column_name != 'date':
                        try:
                            income_row[column_name] = float(value)
                        except (ValueError, TypeError):
                            income_row[column_name] = value
                    else:
                        income_row[column_name] = value
                income_data.append(income_row)
        
        return income_data
    except Exception as e:
        print(f"Error getting income statement data for {ticker}: {str(e)}")
        return []

# Get balance sheet data for a ticker
def get_balance_sheet_data(conn, ticker):
    """Get balance sheet data for a ticker from the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'energy_equipment_and_services' 
                AND table_name = %s
            );
        """, (f"{ticker}_balance_sheets",))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"Warning: No balance sheets table found for {ticker}")
            return []
        
        # Get column names for the balance sheet table
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'energy_equipment_and_services' 
            AND table_name = %s;
        """, (f"{ticker}_balance_sheets",))
        columns = [row[0] for row in cursor.fetchall()]
        
        balance_sheet_data = []
        if columns:
            # Build query with all columns
            columns_str = ', '.join(columns)
            query = f"""
                SELECT {columns_str}
                FROM energy_equipment_and_services.{ticker}_balance_sheets
                ORDER BY date DESC
            """
            cursor.execute(query)
            
            for row in cursor.fetchall():
                balance_sheet_row = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    # Convert numeric strings to float for metrics
                    if value is not None and isinstance(value, (str, Decimal)) and column_name != 'date':
                        try:
                            balance_sheet_row[column_name] = float(value)
                        except (ValueError, TypeError):
                            balance_sheet_row[column_name] = value
                    else:
                        balance_sheet_row[column_name] = value
                balance_sheet_data.append(balance_sheet_row)
        
        return balance_sheet_data
    except Exception as e:
        print(f"Error getting balance sheet data for {ticker}: {str(e)}")
        return []

# Get cash flow data for a ticker
def get_cash_flow_data(conn, ticker):
    """Get cash flow data for a ticker from the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'energy_equipment_and_services' 
                AND table_name = %s
            );
        """, (f"{ticker}_cash_flow_statements",))
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print(f"Warning: No cash flow statements table found for {ticker}")
            return []
        
        # Get column names for the cash flow table
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'energy_equipment_and_services' 
            AND table_name = %s;
        """, (f"{ticker}_cash_flow_statements",))
        columns = [row[0] for row in cursor.fetchall()]
        
        cash_flow_data = []
        if columns:
            # Build query with all columns
            columns_str = ', '.join(columns)
            query = f"""
                SELECT {columns_str}
                FROM energy_equipment_and_services.{ticker}_cash_flow_statements
                ORDER BY date DESC
            """
            cursor.execute(query)
            
            for row in cursor.fetchall():
                cash_flow_row = {}
                for i, value in enumerate(row):
                    column_name = columns[i]
                    # Convert numeric strings to float for metrics
                    if value is not None and isinstance(value, (str, Decimal)) and column_name != 'date':
                        try:
                            cash_flow_row[column_name] = float(value)
                        except (ValueError, TypeError):
                            cash_flow_row[column_name] = value
                    else:
                        cash_flow_row[column_name] = value
                cash_flow_data.append(cash_flow_row)
        
        return cash_flow_data
    except Exception as e:
        print(f"Error getting cash flow data for {ticker}: {str(e)}")
        return []

# Collect comprehensive data for all companies
company_data = []

for idx, row in df.iterrows():
    ticker = row['ticker_symbol']
    ticker_lower = ticker.lower()
    
    print(f"Collecting comprehensive data for {ticker}...")
    
    # Get all financial data
    financial_metrics = get_financial_metrics(agent.conn, ticker_lower)
    income_data = get_income_data(agent.conn, ticker_lower)
    balance_sheet_data = get_balance_sheet_data(agent.conn, ticker_lower)
    cash_flow_data = get_cash_flow_data(agent.conn, ticker_lower)
    
    # Create comprehensive company profile
    company_profile = {
        'ticker': ticker,
        'name': row['short_name'],
        'market_data': {
            'price': row['price_d_1'],
            'market_cap': row['market_cap'],
            'p_e': row['p_e'],
            'ebitda_t12m': row['ebitda_t12m'],
            'net_debt_to_ebitda': row['net_debt_to_ebitda_lf'],
            'alpha_3m': row['alpha_m_3'],
            'beta_3m': row['beta_m_3']
        },
        'financial_metrics': financial_metrics,
        'income_statement': income_data,
        'balance_sheet': balance_sheet_data,
        'cash_flow': cash_flow_data,
        'data_completeness': {
            'has_financial_metrics': len(financial_metrics) > 0,
            'has_income_statement': len(income_data) > 0,
            'has_balance_sheet': len(balance_sheet_data) > 0,
            'has_cash_flow': len(cash_flow_data) > 0
        }
    }
    
    company_data.append(company_profile)

# Function to convert to JSON-compatible format
def json_serialize(obj):
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif pd.isna(obj):
        return None
    else:
        return obj

# Prepare data for OpenAI
OpenAI_API_KEY = "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"

if not OpenAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    exit(1)

client = OpenAI(
    api_key=OpenAI_API_KEY
)

# Create a clean version of company data to prevent circular references
serializable_data = []

# Backtest version: Skip the 4 most recent periods and include older periods
MAX_PERIODS = 4  # Number of historical periods to include in the analysis
SKIP_PERIODS = 4  # Skip this many most recent periods for backtesting

for company in company_data:
    clean_company = {
        'ticker': company['ticker'],
        'name': company['name'],
        'market_data': {},
        'data_completeness': company['data_completeness']
    }
    
    # Copy market data
    for key, value in company['market_data'].items():
        if pd.notna(value):
            clean_company['market_data'][key] = float(value) if isinstance(value, (float, int, np.number)) else value
    
    # Copy financial metrics history (skipping recent periods for backtesting)
    if company['financial_metrics']:
        clean_company['financial_metrics'] = []
        for i, metrics_period in enumerate(company['financial_metrics']):
            if i < SKIP_PERIODS:  # Skip the most recent periods
                continue
            if i >= SKIP_PERIODS + MAX_PERIODS:  # Only include MAX_PERIODS periods after skipping
                break
            clean_period = {}
            for key, value in metrics_period.items():
                if key == 'date' and value is not None:
                    clean_period['date'] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
                elif value is not None and pd.notna(value):
                    clean_period[key] = float(value) if isinstance(value, (float, int, np.number)) else value
            clean_company['financial_metrics'].append(clean_period)
    
    # Copy income statement history (skipping recent periods for backtesting)
    if company['income_statement']:
        clean_company['income_statement'] = []
        for i, income_period in enumerate(company['income_statement']):
            if i < SKIP_PERIODS:  # Skip the most recent periods
                continue
            if i >= SKIP_PERIODS + MAX_PERIODS:  # Only include MAX_PERIODS periods after skipping
                break
            clean_period = {}
            for key, value in income_period.items():
                if key == 'date' and value is not None:
                    clean_period['date'] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
                elif value is not None and pd.notna(value):
                    clean_period[key] = float(value) if isinstance(value, (float, int, np.number)) else value
            clean_company['income_statement'].append(clean_period)
    
    # Copy balance sheet history (skipping recent periods for backtesting)
    if company['balance_sheet']:
        clean_company['balance_sheet'] = []
        for i, balance_period in enumerate(company['balance_sheet']):
            if i < SKIP_PERIODS:  # Skip the most recent periods
                continue
            if i >= SKIP_PERIODS + MAX_PERIODS:  # Only include MAX_PERIODS periods after skipping
                break
            clean_period = {}
            for key, value in balance_period.items():
                if key == 'date' and value is not None:
                    clean_period['date'] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
                elif value is not None and pd.notna(value):
                    clean_period[key] = float(value) if isinstance(value, (float, int, np.number)) else value
            clean_company['balance_sheet'].append(clean_period)
    
    # Copy cash flow history (skipping recent periods for backtesting)
    if company['cash_flow']:
        clean_company['cash_flow'] = []
        for i, cash_flow_period in enumerate(company['cash_flow']):
            if i < SKIP_PERIODS:  # Skip the most recent periods
                continue
            if i >= SKIP_PERIODS + MAX_PERIODS:  # Only include MAX_PERIODS periods after skipping
                break
            clean_period = {}
            for key, value in cash_flow_period.items():
                if key == 'date' and value is not None:
                    clean_period['date'] = value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
                elif value is not None and pd.notna(value):
                    clean_period[key] = float(value) if isinstance(value, (float, int, np.number)) else value
            clean_company['cash_flow'].append(clean_period)
    
    serializable_data.append(clean_company)

# Convert data to JSON string directly without using json_serialize
try:
    print(f"\nPreparing to analyze {len(serializable_data)} companies...")
    print("Breaking data into smaller chunks to avoid token limits...")
    
    # Organize companies into smaller chunks (5 companies per request)
    CHUNK_SIZE = 5
    company_chunks = [serializable_data[i:i + CHUNK_SIZE] for i in range(0, len(serializable_data), CHUNK_SIZE)]
    
    print(f"Data split into {len(company_chunks)} chunks")
    
    all_analyses = []
    
    # Create a detailed prompt for the model
    base_prompt = """
    You are a highly skilled financial analyst specializing in the energy sector. Based on the provided financial data for a subset of energy equipment and services companies, your task is to:

    1. Perform a comprehensive quantitative analysis of each company's fundamental metrics, with MODERATELY GREATER WEIGHT given to:
       - P/E ratio (low is better)
       - Price to book (low is better)
       - Operating margin (high is better)
       - Net margin (high is better)
       - Debt to equity ratio (low is better)
       
       While still considering other metrics like:
       - Leverage and liquidity metrics
       - Valuation metrics (EV/EBITDA, etc.)
       - Historical trends in key financial metrics
       - Balance sheet strength
       - Cash flow data (when available)

    2. Look for patterns in the data like this for example:
        - Free Cash Flow Growth - Consistently positive and growing free cash flow demonstrates real profitability and financial flexibility for reinvestment, debt reduction, and shareholder returns
        - Low Debt-to-Equity Ratio - Manageable debt levels (typically <1) reduce financial risk and interest burden, providing flexibility during economic downturns
        - Consistent Revenue/Earnings Growth - Steady growth exceeding inflation indicates sustainable business model and competitive advantages
        - Attractive Valuation - Low P/E relative to growth rate (PEG <1) and industry peers suggests potential undervaluation
        - High Return on Equity (ROE) - Consistently high ROE (>15%) demonstrates management's ability to efficiently generate profits from shareholder investment
    
    3. Provide a succinct comparative analysis focusing on the quantitavtive metrics and the patterns you see in the data. Be succinct but provide a comprehensive overall analysis.

    4. Select the company that represents the best investment opportunity based on your quantitative analysis and explain:
       - Exactly how the company performs on the five key weighted metrics compared to peers (with exact figures)
       - Any additional supporting metrics that reinforce the selection
       - Brief mention of potential risks

    Please provide your analysis with your TOP PICK from this subset only.

    Here is the detailed financial data for this subset of companies:
    """
    
    top_picks = []
    
    # Process each chunk with OpenAI
    for i, chunk in enumerate(company_chunks):
        print(f"\nProcessing chunk {i+1}/{len(company_chunks)} ({len(chunk)} companies)...")
        print("BACKTESTING: Using historical data (skipping 4 most recent periods)")
        
        # Serialize this chunk
        chunk_json = json.dumps(chunk, indent=2, default=json_serialize)
        print(f"Chunk size: {len(chunk_json)} characters")
        
        # Call OpenAI API for this chunk
        try:
            response = client.chat.completions.create(
                model="o1",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": chunk_json}
                ]
            )
            
            # Get the analysis for this chunk
            chunk_analysis = response.choices[0].message.content
            
            # Remove markdown formatting
            chunk_analysis = chunk_analysis.replace('###', '').replace('##', '').replace('#', '')
            chunk_analysis = chunk_analysis.replace('**', '').replace('*', '')
            
            all_analyses.append(chunk_analysis)
            
            # Extract company name from analysis
            ticker_pattern = r'([A-Z]+) (?:is|represents)'
            ticker_matches = re.findall(ticker_pattern, chunk_analysis)
            if ticker_matches:
                top_pick_in_chunk = ticker_matches[0]
                # Find the full company data for this ticker
                for company in chunk:
                    if company['ticker'] == top_pick_in_chunk:
                        top_picks.append({
                            'ticker': company['ticker'],
                            'name': company['name'],
                            'justification': chunk_analysis
                        })
                        break
                if not any(pick['ticker'] == top_pick_in_chunk for pick in top_picks):
                    top_picks.append({
                        'ticker': top_pick_in_chunk,
                        'justification': chunk_analysis
                    })
            
            print(f"Successfully analyzed chunk {i+1}")
            
        except Exception as e:
            print(f"Error processing chunk {i+1}: {str(e)}")
    
    # Final comparison of top picks from all chunks
    if len(top_picks) > 1:
        print("\n🔍 Performing final comparison of top picks from each chunk...")
        print("BACKTESTING: Using historical data (skipping 4 most recent periods)")
        final_comparison_prompt = """
        As a senior financial analyst specializing in the energy sector, you need to determine the SINGLE BEST investment opportunity from the following top picks. Your process should be:

        1. Perform a comparative quantitative analysis of each company's fundamental metrics, with MODERATELY GREATER WEIGHT given to:
           - P/E ratio (low is better)
           - Price to book (low is better)
           - Operating margin (high is better)  
           - Net margin (high is better)
           - Debt to equity ratio (low is better)
           
           While still considering other metrics like:
           - Leverage and liquidity metrics
           - Valuation metrics (EV/EBITDA, etc.)
           - Historical trends in key financial metrics
           - Balance sheet strength
           - Cash flow data (when available)

        2. Look for patterns in the data like this for example:
            - Free Cash Flow Growth - Consistently positive and growing free cash flow demonstrates real profitability and financial flexibility for reinvestment, debt reduction, and shareholder returns
            - Low Debt-to-Equity Ratio - Manageable debt levels (typically <1) reduce financial risk and interest burden, providing flexibility during economic downturns
            - Consistent Revenue/Earnings Growth - Steady growth exceeding inflation indicates sustainable business model and competitive advantages
            - Attractive Valuation - Low P/E relative to growth rate (PEG <1) and industry peers suggests potential undervaluation
            - High Return on Equity (ROE) - Consistently high ROE (>15%) demonstrates management's ability to efficiently generate profits from shareholder investment

        3. ONLY SHOW THE TOP PICK 
        
        IMPORTANT: Format your response in plain text without any markdown formatting. BE EXTREMELY CONCISE, THIS IS VERY IMPORTANT. Focus on the quantitative metrics with minimal narrative.
        
        Top pick:
        """
        
        # Create summary of top picks for final comparison
        top_picks_summary = ""
        for i, pick in enumerate(top_picks):
            top_picks_summary += f"\nPICK {i+1}: {pick['ticker']}"
            if 'name' in pick:
                top_picks_summary += f" ({pick['name']})\n"
            else:
                top_picks_summary += "\n"
            top_picks_summary += f"Justification: {pick['justification'][:1000]}...\n"
        
        try:
            response = client.chat.completions.create(
                model="o1",
                messages=[
                    {"role": "system", "content": final_comparison_prompt},
                    {"role": "user", "content": top_picks_summary}
                ]
            )
            
            final_analysis = response.choices[0].message.content
            final_analysis = final_analysis.replace('###', '').replace('##', '').replace('#', '')
            final_analysis = final_analysis.replace('**', '').replace('*', '')
            
            print("\n=== OPENAI GPT-4o BACKTESTING INVESTMENT ANALYSIS ===")
            print("--- Analyzing with data excluding 4 most recent periods ---")
            for i, analysis in enumerate(all_analyses):
                print(f"\nCHUNK {i+1} ANALYSIS:")
                print(analysis[:500] + "...\n")
            
            print("\n--- FINAL RECOMMENDATION ---")
            print(final_analysis)
            
            # Extract the selected ticker for backtesting comparison
            ticker_pattern = r'([A-Z]+) (?:is|represents)'
            ticker_matches = re.findall(ticker_pattern, final_analysis)
            selected_ticker = ticker_matches[0] if ticker_matches else "UNKNOWN"
            
            # Save backtesting results to file
            backtest_results = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "selected_ticker": selected_ticker,
                "analysis": final_analysis,
                "skipped_periods": SKIP_PERIODS,
                "analyzed_periods": MAX_PERIODS
            }
            
            # Save to JSON file
            os.makedirs("backtesting_results", exist_ok=True)
            with open(f"backtesting_results/energy_backtest_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                json.dump(backtest_results, f, indent=2)
            
            print(f"\nBacktesting results saved. Selected ticker: {selected_ticker}")
            
        except Exception as e:
            print(f"Error in final comparison: {str(e)}")
            print("\n=== INDIVIDUAL ANALYSES WITHOUT FINAL COMPARISON ===")
            for i, analysis in enumerate(all_analyses):
                print(f"\nCHUNK {i+1} ANALYSIS:")
                print(analysis)
    
    elif len(top_picks) == 1:
        # If only one chunk was processed
        print("\n=== OPENAI GPT-o1 BACKTESTING INVESTMENT ANALYSIS ===")
        print("--- Analyzing with data excluding 4 most recent periods ---")
        print(all_analyses[0])
        
        # Extract the selected ticker for backtesting comparison
        selected_ticker = top_picks[0]['ticker'] if 'ticker' in top_picks[0] else "UNKNOWN"
        
        # Save backtesting results to file
        backtest_results = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "selected_ticker": selected_ticker,
            "analysis": all_analyses[0],
            "skipped_periods": SKIP_PERIODS,
            "analyzed_periods": MAX_PERIODS
        }
        
        # Save to JSON file
        os.makedirs("backtesting_results", exist_ok=True)
        with open(f"backtesting_results/energy_backtest_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(backtest_results, f, indent=2)
        
        print(f"\nBacktesting results saved. Selected ticker: {selected_ticker}")
    
    else:
        print("No analyses were completed successfully.")
        
except Exception as e:
    print(f"Error processing data or calling OpenAI API: {str(e)}")
    
    # Fall back to basic analysis without printing output
    print("\nFalling back to basic analysis due to API error...")

try:
    # Simple scoring mechanism as fallback (without printing results)
    for company in company_data:
        score = 0
        ticker = company['ticker']
        
        # Basic metrics to check
        market_data = company['market_data']
        financials = company['financial_metrics']
        
        # Check P/E ratio
        if market_data.get('p_e') and pd.notna(market_data['p_e']) and isinstance(market_data['p_e'], (int, float)) and market_data['p_e'] > 0 and market_data['p_e'] < 15:
            score += 10
        
        # Get the most recent financial metrics if available
        recent_financials = financials[0] if financials and len(financials) > 0 else {}
        
        # Check debt levels
        if recent_financials.get('debt_to_equity') and pd.notna(recent_financials['debt_to_equity']) and isinstance(recent_financials['debt_to_equity'], (int, float)) and recent_financials['debt_to_equity'] < 1:
            score += 8
        
        # Check ROE
        if recent_financials.get('return_on_equity') and pd.notna(recent_financials['return_on_equity']) and isinstance(recent_financials['return_on_equity'], (int, float)) and recent_financials['return_on_equity'] > 15:
            score += 12
        
        # Check profit margins
        if recent_financials.get('net_profit_margin') and pd.notna(recent_financials['net_profit_margin']) and isinstance(recent_financials['net_profit_margin'], (int, float)) and recent_financials['net_profit_margin'] > 10:
            score += 10
        
        company['fallback_score'] = score
    
    # Sort by fallback score
    sorted_companies = sorted(company_data, key=lambda x: x.get('fallback_score', 0), reverse=True)
    
    # We're removing the print statements here that were showing the TOP PICK BASED ON BASIC ANALYSIS

except Exception as e:
    print(f"Error in fallback analysis: {str(e)}")
    traceback.print_exc()

# Close the database connection
agent.close() 