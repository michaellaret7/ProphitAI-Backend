import os
import json
import pandas as pd
import numpy as np
import concurrent.futures
from openai import OpenAI

# Import from utils package
from src.utils.caching import cache_result

# Import from our modules
from src.phaseTwo.data_retrieval import get_stock_tickers
from src.phaseTwo.financial_metrics import calculate_stock_metrics, generate_fundamental_analysis_report
from src.phaseTwo.sentiment_analysis import get_news_sentiment, batch_analyze_news_sentiment

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load environment variables for the LLM client used in analyze_tickers_and_generate_recommendations
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_model = "deepseek-reasoner"
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_model = os.environ.get("OPENAI_MODEL")
grok_api_key = os.environ.get("GROK_API_KEY")
grok_model = os.environ.get("GROK_MODEL")

# Determine which model and client to use (ensure consistency with phaseTwo.py)
model = deepseek_model  # Or choose based on logic if needed elsewhere

def get_llm_client():
    """Get LLM client for final recommendations based on selected model."""
    if model == openai_model:
       return OpenAI(api_key=openai_api_key)
    elif model == deepseek_model:
       return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    elif model == grok_model:
       return OpenAI(api_key=grok_api_key, base_url="https://api.grok.com")
    else:
        raise ValueError(f"Unsupported model for final recommendations: {model}")

def _calculate_and_filter_metrics(ticker_list):
    """Calculate metrics for tickers and filter out those with insufficient data."""
    all_metrics = {}
    for ticker in ticker_list:
        metrics = calculate_stock_metrics(ticker)
        all_metrics[ticker] = metrics

    valid_metrics_data = []
    for ticker, metrics in all_metrics.items():
        if metrics.get('date_range') and metrics.get('average_daily_volume', 0) >= 10000:
            metrics_row = {'Ticker': ticker}
            metrics_row.update(metrics)
            valid_metrics_data.append(metrics_row)

    if not valid_metrics_data:
        return pd.DataFrame() # Return empty DataFrame if no valid data

    return pd.DataFrame(valid_metrics_data)

def _calculate_composite_scores(df):
    """Calculate z-scores and composite scores for ranking."""
    if df.empty:
        return pd.DataFrame() # Return empty DataFrame if input is empty

    higher_is_better = [
        'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'annualized_return',
        'upside_capture', 'momentum_6m', 'momentum_12m', 'max_drawdown',
    ]
    lower_is_better = [
        'annualized_volatility', 'daily_return_volatility', 'beta',
        'sector_beta', 'downside_capture'
    ]

    z_scores = df.copy()
    for col in higher_is_better + lower_is_better:
        if col in df.columns and not df[col].isnull().all() and df[col].std(ddof=0) != 0: # Check for NaNs and zero std dev
            z_scores[col] = (df[col] - df[col].mean()) / df[col].std(ddof=0)
        else:
            z_scores[col] = 0 # Assign 0 if column missing, all NaN, or no variation

    for col in lower_is_better:
        if col in z_scores.columns:
            z_scores[col] = -z_scores[col]

    metric_columns = [col for col in higher_is_better + lower_is_better if col in z_scores.columns]
    z_scores['composite_score'] = z_scores[metric_columns].sum(axis=1)

    return z_scores.sort_values(by='composite_score', ascending=False)

@cache_result
def select_top_performing_stocks(ticker_input):
    """
    Filter stocks based on quantitative metrics using z-scores.

    Args:
        ticker_input: Either a dictionary {filter_value: [tickers]} or a list of tickers

    Returns:
        If input is a dictionary: Dictionary with filter_value as key and list of top tickers as value
        If input is a list: List of top tickers
    """
    if isinstance(ticker_input, list):
        # Handle list input
        df_metrics = _calculate_and_filter_metrics(ticker_input)
        if df_metrics.empty:
            print("Warning: No valid metrics found for the provided list of tickers. Returning empty list.")
            return []

        print("--- DataFrame with Valid Metrics (filter_stocks - list input) ---")
        print(df_metrics)
        print("-----------------------------------------------------------------")

        ranked_df = _calculate_composite_scores(df_metrics)
        if ranked_df.empty:
            return []

        print("--- Ranked DataFrame with Z-Scores (filter_stocks - list input) ---")
        print(ranked_df)
        print("------------------------------------------------------------------")

        max_stocks = 10
        available_stocks = min(max_stocks, len(ranked_df))
        return ranked_df.head(available_stocks)['Ticker'].tolist()

    elif isinstance(ticker_input, dict):
        # Handle dictionary input
        result_dict = {}
        for filter_value, ticker_list in ticker_input.items():
            df_metrics = _calculate_and_filter_metrics(ticker_list)
            if df_metrics.empty:
                print(f"Warning: No valid metrics found for filter '{filter_value}'. Skipping this filter.")
                result_dict[filter_value] = []
                continue

            print(f"--- DataFrame with Valid Metrics (filter_stocks - dict input: {filter_value}) ---")
            print(df_metrics)
            print("----------------------------------------------------------------------")

            ranked_df = _calculate_composite_scores(df_metrics)
            if ranked_df.empty:
                 result_dict[filter_value] = []
                 continue

            print(f"--- Ranked DataFrame with Z-Scores (filter_stocks - dict input: {filter_value}) ---")
            print(ranked_df)
            print("-------------------------------------------------------------------")

            max_stocks = 7
            available_stocks = min(max_stocks, len(ranked_df))
            result_dict[filter_value] = ranked_df.head(available_stocks)['Ticker'].tolist()
        return result_dict
    else:
        raise TypeError("Input must be a list of tickers or a dictionary {filter_value: [tickers]}")


_ETF_CATEGORIES = [
    "alternative_etfs", "commodity_etfs", "equity_etfs", "fixed_income_etfs",
    "private_equity_exposure_etfs", "business_development_companies",
    "closed_end_funds_that_hold_private_equity_late_sta", "equity_selection_hedge_fund_holding_clones",
    "hedge_funds", "ipo_focused_etfs_late_stage_tech_pre_ipo_th", "softs",
    "broad_commodity_etfs", "energy_focused_etfs", "grains", "industrial_metals",
    "livestock", "precious_metals_etfs", "single_country_and_regional_etfs_in_emerging_marke",
    "sector_specific_etfs", "barra_styleetfs", "broad_us_market",
    "broad_based_emerging_market_equity_etfs", "factor_style_and_specialized_em_etfs",
    "global_international_etfs", "convertible_bonds", "high_yield_junk_bond_etfs",
    "investment_grade_corporate_bond_etfs", "treasury_and_inflation_bond_etfs"
]

def _get_tickers_and_etf_map(tickers):
    """Determine ticker list and ETF status map."""
    if tickers is None:
        print("Retrieving all stock tickers...")
        tickers = get_stock_tickers(None) # Assuming this returns a dict {category: [tickers]}

    ticker_list = []
    is_etf_map = {}

    if isinstance(tickers, dict):
        for category, industry_tickers in tickers.items():
            is_etf = category in _ETF_CATEGORIES
            for ticker in industry_tickers:
                ticker_list.append(ticker)
                is_etf_map[ticker] = is_etf
    elif isinstance(tickers, list):
        ticker_list = tickers
        # Assume list input contains only non-ETFs unless specified otherwise
        # A more robust approach might require additional info if lists can contain ETFs
        is_etf_map = {ticker: False for ticker in tickers}
    else:
        raise TypeError("Tickers input must be a dictionary or a list.")

    return ticker_list, is_etf_map

def _get_default_metrics():
    """Return default metrics dictionary for error handling."""
    return {
        "sharpe_ratio": 0, "sortino_ratio": 0, "calmar_ratio": 0,
        "annualized_return": 0, "annualized_volatility": 0,
        "daily_return_volatility": 0, "max_drawdown": 0, "beta": 0,
        "sector_beta": 0, "upside_capture": 0, "downside_capture": 0,
        "momentum_6m": 0, "momentum_12m": 0, "average_daily_volume": 0
    }

def _process_metrics_and_fundamentals(ticker_list, is_etf_map, max_workers):
    """Process metrics and fundamentals in parallel."""
    print("Phase 1: Processing metrics and fundamentals...")
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        # Submit metrics tasks
        for ticker in ticker_list:
            futures[executor.submit(calculate_stock_metrics, ticker)] = (ticker, "metrics")

        # Submit fundamentals tasks (skip ETFs)
        for ticker in ticker_list:
            if not is_etf_map.get(ticker, False):
                futures[executor.submit(generate_fundamental_analysis_report, ticker)] = (ticker, "fundamentals")

        # Process completed futures
        for future in concurrent.futures.as_completed(futures):
            ticker, data_type = futures[future]
            if ticker not in results:
                results[ticker] = {}
            try:
                result = future.result()
                # Remove sector_beta for ETFs
                if data_type == "metrics" and is_etf_map.get(ticker, False):
                    result.pop('sector_beta', None)
                results[ticker][data_type] = result
                print(f"Completed {data_type} for {ticker}")
            except json.JSONDecodeError as e:
                print(f"{data_type} analysis of {ticker} generated a JSON decode exception: {e} (Line: {e.lineno}, Col: {e.colno})")
                if data_type == "metrics":
                    results[ticker][data_type] = _get_default_metrics()
                elif data_type == "fundamentals":
                    results[ticker][data_type] = f"Error analyzing fundamentals for {ticker}: JSON parsing error"
            except Exception as exc:
                print(f"{data_type} analysis of {ticker} generated an exception: {exc}")
                if data_type == "metrics":
                    results[ticker][data_type] = _get_default_metrics()
                elif data_type == "fundamentals":
                    results[ticker][data_type] = f"Error analyzing fundamentals for {ticker}: {str(exc)}"

    # Add placeholder fundamentals for ETFs
    for ticker in ticker_list:
        if is_etf_map.get(ticker, False) and ticker in results:
            if "fundamentals" not in results[ticker]: # Only add if not already errored out
                results[ticker]["fundamentals"] = "ETF fundamental data not analyzed"
        elif ticker not in results: # Handle cases where ticker failed entirely
             results[ticker] = {"metrics": _get_default_metrics(), "fundamentals": "Error retrieving data"}


    return results

def _generate_sentiment_query(ticker, is_etf):
    """Generate the appropriate sentiment query for a ticker."""
    if is_etf:
        return f"{ticker} etf recent performance analyst ratings news institutional ownership price targets forecasts"
    else:
        return f"{ticker} stock recent performance analyst ratings news institutional ownership price targets earnings forecasts"

def _process_sentiment(ticker_list, is_etf_map, max_workers, batch_sentiment):
    """Process sentiment analysis, either batch or individual."""
    print("Phase 2: Processing news sentiment...")
    sentiment_results = {}

    if batch_sentiment:
        ticker_queries = [
            (ticker, _generate_sentiment_query(ticker, is_etf_map.get(ticker, False)))
            for ticker in ticker_list
        ]
        sentiment_results = batch_analyze_news_sentiment(ticker_queries) # Assumes this handles errors internally
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(get_news_sentiment, _generate_sentiment_query(ticker, is_etf_map.get(ticker, False))): ticker
                for ticker in ticker_list
            }
            for future in concurrent.futures.as_completed(futures):
                ticker = futures[future]
                try:
                    sentiment_results[ticker] = future.result()
                    print(f"Completed sentiment analysis for {ticker}")
                except Exception as exc:
                    print(f"Sentiment analysis of {ticker} generated an exception: {exc}")
                    sentiment_results[ticker] = f"Error analyzing sentiment for {ticker}"

    return sentiment_results

def _combine_analysis_results(ticker_list, metrics_fundamentals_results, sentiment_results, is_etf_map):
    """Combine results, using is_etf_map for accurate fundamental placeholders."""
    all_analysis_data = {}
    for ticker in ticker_list:
        all_analysis_data[ticker] = metrics_fundamentals_results.get(ticker, {})
        sentiment_data = sentiment_results.get(ticker, f"No sentiment data available for {ticker}")
        all_analysis_data[ticker]["sentiment"] = sentiment_data

        if "metrics" not in all_analysis_data[ticker]:
            all_analysis_data[ticker]["metrics"] = _get_default_metrics()

        if "fundamentals" not in all_analysis_data[ticker]:
            if is_etf_map.get(ticker, False):
                all_analysis_data[ticker]["fundamentals"] = "ETF fundamental data not analyzed"
            else:
                # If not ETF and fundamentals are missing, it indicates an error during processing
                all_analysis_data[ticker]["fundamentals"] = "Fundamental data retrieval failed"
    return all_analysis_data

def _generate_llm_prompt_content(all_analysis_data):
    """Generate the content for the LLM prompt."""
    num_tickers = len(all_analysis_data)
    system_prompt = f"""
<think>

You are a very skilled portfolio manager with 30 years of experience.

TASK:
You will receive the complete analysis data for {num_tickers} stocks. Your job is to identify the top 2-3 stocks with the best overall performance.

ANALYSIS APPROACH:
1. Review ALL the provided data carefully
2. Evaluate each stock based on a combination of:
   - Performance metrics (sharpe ratio, sortino ratio, etc.)
   - Fundamental data (when available)
   - News sentiment
3. Choose the 2-3 stocks that you believe have the best investment potential(DO NOT EXCEED 3 RECOMMENDATIONS)

OUTPUT FORMAT:
Return your recommendations in this JSON format:
{{
"total_stocks_analyzed": {num_tickers},
"recommendations": [
   {{
   "ticker": [string],
   "justification": [string],
   "fundamental_overview": [string],
   "sentiment": [string],
   "sharpe_ratio": [float],
   "sortino_ratio": [float],
   "calmar_ratio": [float],
   "annualized_return": [float],
   "annualized_volatility": [float],
   "daily_return_volatility": [float],
   "max_drawdown": [float],
   "beta": [float],
   "sector_beta": [float], # Note: May be null/missing for ETFs
   "upside_capture": [float],
   "downside_capture": [float],
   "momentum_6m": [float],
   "momentum_12m": [float]
   }}
]
}}

UNDERSTANDING THE METRICS:
- "sharpe_ratio": Risk-adjusted return metric. Higher values indicate better risk-adjusted performance. Values > 1 are generally good.
- "sortino_ratio": Similar to Sharpe but only penalizes downside volatility. Higher values are better.
- "calmar_ratio": Return relative to maximum drawdown. Higher values indicate better return per unit of downside risk.
- "annualized_return": The total return expressed as annual percentage. Higher values represent stronger performance.
- "annualized_volatility": The standard deviation of returns expressed annually. Lower values indicate more stability.
- "daily_return_volatility": Standard deviation of daily returns. Lower values mean more consistent day-to-day performance.
- "max_drawdown": Maximum loss from peak to trough. Closer to zero means smaller worst-case losses.
- "beta": Stock's movement relative to the market. >1 means more volatile than market, <1 means less volatile.
- "sector_beta": Similar to beta but measured against the stock's sector rather than the S&P 500. (May not be present for ETFs)
- "upside_capture": Measures how much a stock gains relative to the market in up periods. >1 means outperforming in bull markets.
- "downside_capture": Measures losses relative to market in down periods. <1 is better (smaller losses than market).
- "momentum_6m": 6-month cumulative return. Higher values indicate stronger recent performance trend.
- "momentum_12m": 12-month cumulative return. Higher values indicate stronger medium-term performance trend.

IMPORTANT:
- Base your recommendations on the data provided - don't hallucinate additional information
- If there is missing information for certain stocks, you may exclude them from consideration
- For ETFs, fundamental data will be marked as "ETF fundamental data not analyzed" or similar.
- Provide a concise but thorough justification for each recommendation
</think>
"""
    user_prompt = f"Here is the complete analysis data for {num_tickers} tickers: {json.dumps(all_analysis_data)}"

    user_prompt += "\n\nPlease analyze this data and provide your top 2-3 stock recommendations."

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

def _get_llm_recommendations(messages):
    """Get final recommendations from the LLM."""
    client = get_llm_client()
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # If using DeepSeek or another model that supports it, try to request JSON format
            response_format = None
            if model == openai_model or model == grok_model:
                response_format = {"type": "json_object"}
            
            # Request with lower temperature for more structured output
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,  # Lower temperature for more consistent JSON formatting
                response_format=response_format if response_format else None
            )
            
            recommendations = response.choices[0].message.content
            
            # Extract JSON if there's any extra text around it
            start_index = recommendations.find('{')
            end_index = recommendations.rfind('}')
            
            if start_index != -1 and end_index != -1 and end_index > start_index:
                cleaned_json_str = recommendations[start_index : end_index + 1]
                
                # Validate the JSON structure
                try:
                    json_data = json.loads(cleaned_json_str)
                    # Check for required structure
                    if "recommendations" in json_data:
                        return cleaned_json_str
                except json.JSONDecodeError:
                    print(f"Attempt {retry_count + 1}: Failed to parse JSON, retrying...")
                    retry_count += 1
                    continue
            
            # If we get here, the response isn't valid JSON or is missing required fields
            if retry_count < max_retries - 1:
                # Add a message clarifying the need for valid JSON
                clarification_message = {
                    "role": "user", 
                    "content": """Your previous response was not properly formatted JSON. 
                    Please provide ONLY valid JSON in the exact format requested:
                    {
                      "total_stocks_analyzed": <number>,
                      "recommendations": [
                        {
                          "ticker": "<ticker symbol>",
                          "justification": "<reason for recommendation>",
                          "fundamental_overview": "<overview>",
                          "sentiment": "<sentiment summary>",
                          "sharpe_ratio": <number>,
                          "sortino_ratio": <number>,
                          "calmar_ratio": <number>,
                          "annualized_return": <number>,
                          "annualized_volatility": <number>,
                          "daily_return_volatility": <number>,
                          "max_drawdown": <number>,
                          "beta": <number>,
                          "sector_beta": <number or null>,
                          "upside_capture": <number>,
                          "downside_capture": <number>,
                          "momentum_6m": <number>,
                          "momentum_12m": <number>
                        }
                      ]
                    }"""
                }
                messages.append(clarification_message)
                retry_count += 1
            else:
                # Final attempt failed, return a valid fallback JSON
                print("Warning: All attempts to get valid JSON failed. Returning empty recommendations.")
                return json.dumps({"error": "Unable to generate valid JSON from LLM", "recommendations": []})
        
        except Exception as e:
            print(f"Error calling LLM for recommendations: {e}")
            if retry_count < max_retries - 1:
                print(f"Retrying... (attempt {retry_count + 1}/{max_retries})")
                retry_count += 1
            else:
                # Return a structured error message after all retries fail
                return json.dumps({"error": f"LLM API call failed after {max_retries} attempts: {str(e)}", "recommendations": []})
    
    # Should never reach here, but just in case
    return json.dumps({"error": "Failed to generate recommendations after maximum retries", "recommendations": []})

def analyze_tickers_and_generate_recommendations(tickers=None, max_workers=4, batch_sentiment=True):
   """
   Run the portfolio manager to analyze stocks and make recommendations.

   Args:
      tickers (dict or list, optional): Tickers to analyze. Fetches all if None.
      max_workers (int): Max parallel workers.
      batch_sentiment (bool): Use batch sentiment analysis.

   Returns:
       str: JSON string containing the LLM's recommendations.
   """
   # 1. Get ticker list and ETF map
   ticker_list, is_etf_map = _get_tickers_and_etf_map(tickers)
   if not ticker_list:
       print("No tickers found or provided.")
       return json.dumps({"error": "No tickers to analyze", "recommendations": []})


   # 2. Process metrics and fundamentals
   metrics_fundamentals_results = _process_metrics_and_fundamentals(ticker_list, is_etf_map, max_workers)

   # 3. Process sentiment
   sentiment_results = _process_sentiment(ticker_list, is_etf_map, max_workers, batch_sentiment)

   # 4. Combine results
   # Pass is_etf_map to the top-level helper
   all_analysis_data = _combine_analysis_results(ticker_list, metrics_fundamentals_results, sentiment_results, is_etf_map)


   # 5. Generate LLM prompt
   messages = _generate_llm_prompt_content(all_analysis_data)

   # 6. Get LLM recommendations
   print(f"Completed analysis of all tickers ({len(all_analysis_data)}). Preparing final recommendations...")
   final_recommendations = _get_llm_recommendations(messages)

   print("Analysis complete!")
   # print(all_analysis_data) # Optional: Print combined data before recommendations
   return final_recommendations
