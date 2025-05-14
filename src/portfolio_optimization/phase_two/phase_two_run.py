"""
Author: @Michael Laret
=====================================================================
Workflow for this file:
1. Extract asset classes from portfolio data (extract_asset_classes)
2. Get tickers for the current asset class (get_stock_tickers)
3. Calculate and filter metrics (calculate_and_filter_metrics)
4. Calculate composite scores (calculate_composite_scores)
5. if etf (get_asset_description)
6. if not etf (generate_fundamental_analysis_report)
7. create final dictionary (create_final_dictionary)
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from src.portfolio_optimization.phase_two.data_retrieval import (
    extract_asset_classes,
    get_stock_tickers,
    get_asset_description,
    get_quarterly_estimates,
)
from src.portfolio_optimization.phase_two.phase_two_calculations import (
    calculate_and_filter_metrics,
    calculate_composite_scores,
)
from src.portfolio_optimization.phase_two.retrieve_fundamental_report import (
    get_fundamental_report_from_db
)
from src.data.user_information import get_user_information
from src.utils.determine_etf import is_etf
import time

# Load environment variables from .env file
load_dotenv()

# Load environment variables
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
deepseek_model = os.environ.get("DEEPSEEK_MODEL")
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

NUM_TOP_TICKERS = 10

def pick_top_tickers_from_asset_classes(portfolio_json):
    start_time = time.perf_counter()

    # Extract asset classes from portfolio data
    asset_classes_dict = extract_asset_classes(portfolio_json)
    all_asset_class_data = {} # Initialize a dictionary to hold data for all asset classes

    for asset_class, _ in asset_classes_dict.items(): # Loop through each asset class
        print(f"Processing asset class: {asset_class}")

        # Get tickers for the current asset class
        tickers_data = get_stock_tickers(asset_class)
        
        # Check if tickers_data is None or empty for the asset class
        if tickers_data is None or asset_class not in tickers_data or not tickers_data[asset_class]:
            print(f"No tickers found or unable to retrieve tickers for asset class: {asset_class}. Skipping.")
            all_asset_class_data[asset_class] = {} # Assign empty dict if no tickers
            continue # Skip to the next asset class

        tickers = tickers_data[asset_class]

        try:
            df = calculate_and_filter_metrics(tickers)

            new_df = calculate_composite_scores(df)
            new_df = new_df[:NUM_TOP_TICKERS]

            # Filter the original df to include only the top 5 tickers
            top_tickers = new_df['Ticker'].tolist()
            df_top_tickers = df[df['Ticker'].isin(top_tickers)]

            print(f"Top {NUM_TOP_TICKERS} tickers for {asset_class}:")
            print(df_top_tickers)

            # Create the final dictionary for the current asset class
            final_stock_data = {}

            for index, row in df_top_tickers.iterrows():
                ticker = row['Ticker']
                stock_metrics = row.drop('Ticker').to_dict()

                # Check if the asset class itself is considered an ETF class
                if is_etf(asset_class):
                    if 'sector_beta' in stock_metrics:
                        del stock_metrics['sector_beta']

                    print(f"Ticker {ticker} in ETF asset class '{asset_class}', removing sector_beta and getting description.")

                    fundamental_report = get_asset_description(ticker)
                    # ETFs don't have fundamental predictions, set to None or skip
                    fundamental_predictions = None 
                else:
                    print(f"Ticker {ticker} in non-ETF asset class '{asset_class}', generating fundamental report.")
                    fundamental_report = get_fundamental_report_from_db(ticker)

                    # Get fundamental predictions only for non-ETFs
                    print(f"Fetching fundamental predictions for {ticker}...")
                    predictions_string = get_quarterly_estimates(ticker) # Get the JSON string
                    try:
                        # Parse the JSON string into a Python object (dict)
                        fundamental_predictions = json.loads(predictions_string)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse fundamental predictions JSON for {ticker}")
                        # Store an error indicator instead of the raw string or None
                        fundamental_predictions = {"error": "No Predicitons Found for this ticker"} 
                    except Exception as e: # Catch other potential errors during parsing
                         print(f"Warning: An unexpected error occurred parsing predictions for {ticker}: {e}")
                         fundamental_predictions = {"error": f"Unexpected error parsing predictions: {e}"}

                stock_metrics['fundamental_report'] = fundamental_report
                # Only add predictions if they were successfully fetched and parsed
                if fundamental_predictions and not fundamental_predictions.get("error"): # Check if valid and no error key
                    stock_metrics['fundamental_predictions'] = fundamental_predictions # Add the parsed dict
                
                final_stock_data[ticker] = stock_metrics
            
            # Include sector allocation alongside ticker data
            sector_alloc = asset_classes_dict.get(asset_class, 0)
            all_asset_class_data[asset_class] = {
                "allocation": sector_alloc,
                "tickers": final_stock_data
            }

        except Exception as e:
            print(f"An error occurred while processing asset class {asset_class}: {e}")
            all_asset_class_data[asset_class] = {"error": str(e)} # Store error info

    print("\n--- Final Results for All Asset Classes ---")
    print(json.dumps(all_asset_class_data)) # Print the aggregated results

    end_time = time.perf_counter()
    duration = end_time - start_time
    print(f"\nTotal execution time: {duration:.4f} seconds")
    return all_asset_class_data

def make_phaseTwo_recommendations(asset_class_top_tickers):
    """
    Sends the top ticker data for each asset class to the OpenAI API for recommendations.

    Args:
        asset_class_top_tickers (dict): A dictionary where keys are asset class names and values are dictionaries of top tickers and their data.

    Returns:
        str: The content of the response from the OpenAI API. Returns None if an error occurs during the API call.
    """
    try:
        # Convert the input dictionary to a JSON string for the prompt content
        data_string = json.dumps(asset_class_top_tickers)

        user_profile = get_user_information()
        # Format the user profile in a more readable way
        user_info = user_profile.get("user_information", {})
        user_profile_formatted = f"""
Age: {user_info.get("age", "N/A")}
Net Worth: {user_info.get("net_worth", "N/A")}
Risk Tolerance: {user_info.get("risk_tolerance", "N/A")}
Investment Goals: {user_info.get("investment_goals", "N/A")}
Time Horizon: {user_info.get("time_horizon", "N/A")}
Description: {user_info.get("Overall Description", "N/A").strip()}
"""

        num_tickers = 10

        system_prompt = f"""
<think>

You are a very skilled portfolio manager with 30 years of experience.

USER PROFILE:
{user_profile_formatted}

TASK:
You will receive the complete analysis data for {num_tickers} stocks. Your job is to identify the top 1-4 stocks with the best overall performance that match the user's risk profile and investment goals.

INVESTOR TYPES AND STOCK SELECTION STRATEGIES:
1. Income-Oriented Investors:
    - Focus on stocks with consistent dividend payments and dividend growth history
    - Look for companies with strong cash flows and sustainable payout ratios
    - Prefer established companies in defensive sectors like utilities, consumer staples, REITs
    - Key metrics: dividend yield, dividend growth rate, payout ratio, free cash flow coverage

2. Wealth Preservation Investors:
    - Prioritize stable blue-chip corporations with long operating histories
    - Focus on low volatility stocks with beta values less than 1.0
    - Look for companies with strong balance sheets and low debt-to-equity ratios
    - Prefer consumer staples, healthcare, and utilities sectors
    - Key metrics: debt levels, consistent profitability, low price volatility, strong cash reserves

3. Capital Appreciation Investors:
    - Target companies in their growth phase with strong revenue and earnings growth
    - Look for companies with competitive advantages and large addressable markets
    - Consider innovative companies disrupting established industries
    - May accept higher volatility for greater return potential
    - Key metrics: revenue growth rate, earnings growth, price-to-earnings-growth (PEG) ratio

MATCHING INVESTOR GOALS TO STOCK CHARACTERISTICS:
- Short-term goals (1-3 years): Focus on stability, lower volatility stocks, stronger balance sheets
- Medium-term goals (3-7 years): Balanced approach with growth potential and reasonable valuations
- Long-term goals (7+ years): Can accept higher short-term volatility for long-term growth potential

RISK TOLERANCE ALIGNMENT:
- Low Risk Tolerance: Favor stocks with lower volatility (beta < 0.8), stronger balance sheets, stable earnings, and established market positions. Prioritize companies with defensive characteristics that perform well in economic downturns.
- Medium Risk Tolerance: Balance between growth and stability. Look for companies with moderate volatility (beta 0.8-1.2), reasonable valuations, and consistent but not necessarily exceptional growth.
- High Risk Tolerance: Can include higher volatility stocks (beta > 1.2) with stronger growth metrics, emerging market exposure, and cyclical industries. May accept less established companies with greater upside potential.

ANALYSIS APPROACH:
1. Review ALL the provided data carefully
2. Evaluate each stock based on a combination of:
    - Performance metrics (sharpe ratio, sortino ratio, beta, momentum, etc.)
    - Historical fundamental data (from `fundamental_report` when available). Assess trends in profitability, solvency, etc.
    - **Forward-looking fundamental estimates** (from `fundamental_predictions` when available). Analyze trends in estimated EPS and Revenue (SREV) growth.
    - Qualitative factors implied by the data (e.g., high momentum might suggest strong recent market sentiment).
    - Alignment with user's risk tolerance and investment goals.
3. **Synthesize Findings:** Compare stocks across different asset classes. Identify the 1-4 stocks that offer the most compelling risk/reward profile based on the integrated analysis (performance, historical fundamentals, future estimates, user profile). DO NOT EXCEED 3 RECOMMENDATIONS IN TOTAL.

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
- `fundamental_report`: Contains historical financial statement data (Balance Sheets, Income Statements, etc.). Use this to assess past performance, financial health, and stability.
- `fundamental_predictions`: Contains **analyst estimates** for future quarterly performance (EPS, SREV, etc.). Use this to gauge growth expectations and potential future trajectory.

STOCK SELECTION BEST PRACTICES:
1. **Integrate Historical and Future Data:** Don't rely solely on past performance or future estimates. Use historical data (`fundamental_report`) to understand the company's track record and stability. Use future estimates (`fundamental_predictions`) to assess growth potential.
2. **Valuation Context:** While direct valuation metrics (like P/E) might not be explicitly provided for all stocks, use the available data (e.g., recent performance, estimated future earnings growth from `fundamental_predictions`) to qualitatively assess if a stock seems reasonably valued relative to its growth prospects and risk profile. High anticipated growth might justify higher current performance metrics.
3. **Qualitative Assessment:** Consider factors like management quality, competitive positioning, and industry trends (as described in the `fundamental_report` summary, if available) alongside the quantitative data.
4. **Risk Assessment:** Pay close attention to volatility (annualized_volatility, beta), drawdown (max_drawdown), and downside capture, especially in relation to the user's risk tolerance.
5. **User Alignment:** Always prioritize recommendations that align with the user's stated goals (growth, income, preservation), time horizon, and risk tolerance.

IMPORTANT CONSIDERATIONS:
- Base your recommendations *only* on the data provided. Do not introduce external information or metrics not present in the input data.
- If there is missing information (e.g., no `fundamental_report` or `fundamental_predictions`), acknowledge this limitation in your reasoning if relevant, but still make recommendations based on available data (like performance metrics).
- For ETFs, fundamental data (`fundamental_report`, `fundamental_predictions`) will likely be missing or marked as not applicable. Evaluate ETFs based primarily on their performance metrics, description (if provided), and alignment with the represented asset class's role in the portfolio.
- **Disclaimer on Predictions:** The data in `fundamental_predictions` represents *analyst consensus estimates* for future performance. These are projections and are **not guaranteed** future results. Actual outcomes may differ significantly. Use them as indicators of expected trends, not certainties.
- Provide a concise but thorough justification for each recommendation, linking specific data points (performance metrics, fundamental trends, future estimates) to your reasoning and the user profile.
- Consider diversification benefits implicitly, but focus recommendations on the top individual stocks based on the analysis.

DATA POINT WEIGHTS (This is how much you should weight each type of data in your analysis):
- Performance Metrics: 45%
- Historical Fundamental Data: 45%
- Forward-Looking Fundamental Estimates: 10% (since this is a prediction and not the actual future fundamental data, it should not carry a huge amount of weight)

OUTPUT FORMAT:
Return your recommendations in this JSON format ONLY. Do not include any other text outside the JSON structure.
{{
"total_stocks_analyzed": {num_tickers},
"recommendations": [
    {{
    "ticker": "[string]",
    "reason_for_recommendation": "[string explaining rationale based on data and user profile]",
    "supporting_metrics": {{ // Optional: Include a few key metrics supporting the decision
        "key_metric_1": "[value]",
        "key_metric_2": "[value]"
        // e.g., "sharpe_ratio": 1.5, "estimated_eps_growth_trend": "Positive"
        }}
    }}
    // Add up to 2 more recommendations if warranted
]
}}
</think>
"""
        user_prompt = f"""
        Based on the following data for various asset classes, provide investment recommendations for the top 1-4 stocks overall that best fit the user profile:
        {data_string}
        """

        completion = client.chat.completions.create(
            model="deepseek-reasoner", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.0
        )

        # Extract and return the content from the response
        if completion.choices and completion.choices[0].message:
            response_content = completion.choices[0].message.content

            # --- START FIX ---
            # Clean the response content: Strip whitespace and remove markdown fences
            cleaned_content = response_content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:] # Remove ```json\n
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3] # Remove ```
            
            # Strip again in case there was whitespace around the fences
            cleaned_content = cleaned_content.strip() 

            try:
                result_json = json.loads(cleaned_content)
                # Get the original sector allocation
                sector_alloc = asset_class_top_tickers.get('allocation', 0)
                recs = result_json.get('recommendations', [])
                if recs:
                    per_alloc = round(sector_alloc / len(recs), 2)
                    for rec in recs:
                        rec['allocation'] = per_alloc
                return json.dumps(result_json)
            except json.JSONDecodeError:
                print("Error: LLM response is not valid JSON even after cleaning.")
                print(f"Original Response:\n{response_content}")
                print(f"Cleaned Response Attempted:\n{cleaned_content}")
                return json.dumps({"error": "LLM response was not valid JSON."})
        else:
            print("Error: No response content received from API.")
            return None

    except Exception as e:
        print(f"An error occurred while calling the API or processing data: {e}")

        return None

def run_phase_two(portfolio_data):
    picks = pick_top_tickers_from_asset_classes(portfolio_data)
    print(picks)

    final_portfolio = {}

    print("="*100)

    # Or if you're looping
    for asset_class_name in picks:
        print(f"Asset class: {asset_class_name}")
        print(picks[asset_class_name])

        recommendations_json = make_phaseTwo_recommendations(picks[asset_class_name])
        print(recommendations_json)
        
        # Parse JSON string to Python object and add to final_portfolio
        if recommendations_json:
            try:
                recommendations_data = json.loads(recommendations_json)
                final_portfolio[asset_class_name] = recommendations_data
            except json.JSONDecodeError as e:
                print(f"Error parsing recommendations for {asset_class_name}: {e}")
                # Add error info to portfolio if parsing fails
                final_portfolio[asset_class_name] = {"error": "Failed to parse recommendations"}
    
    print("\nFinal Portfolio:")
    print(json.dumps(final_portfolio, indent=2))
    
    return final_portfolio





