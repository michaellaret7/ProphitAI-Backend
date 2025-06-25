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
import re
from openai import OpenAI
from dotenv import load_dotenv
from backend.src.portfolio_optimization.phase_two.data_retrieval import (
    extract_asset_classes,
    get_stock_tickers,
    get_asset_description,
)
from backend.src.portfolio_optimization.phase_two.phase_two_calculations import (
    calculate_and_filter_metrics,
    calculate_composite_scores,
)
from backend.src.data.user_information import get_user_information
from backend.src.utils.determine_etf import is_etf_asset_class
import time
from backend.src.utils.choose_model_and_client import deepseek_model_and_client, openai_model_and_client, grok_model_and_client, perplexity_model_and_client
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
# ---------------------------------------------------------------------------
# Phase-two prompt templates & constants
# ---------------------------------------------------------------------------
from backend.src.portfolio_optimization.phase_two.phase_two_prompts import (
    NUM_TOP_TICKERS,
    build_system_prompt,
    build_user_prompt,
)
import logging
from backend.src.utils.logging_config import init_logger, patch_print_for_logging

# Load environment variables from .env file
load_dotenv()

# Initialise logging and quiet-print mechanism early -------------------------
logger = init_logger(__name__)
patch_print_for_logging()
logger.info("[Phase-Two] Phase-two module initialised …")

# Load environment variables
model, client = openai_model_and_client()

def pick_top_tickers_from_asset_classes(portfolio_json):
    """
    Select top tickers from each asset class with quantitative analysis.
    
    Processes each asset class from portfolio JSON, retrieves tickers, calculates metrics,
    ranks by composite scores, and compiles fundamental data for top performers.
    
    Args:
        portfolio_json: Dictionary containing portfolio asset classes and allocations.
        
    Returns:
        Dict: Dictionary mapping asset classes to their top ticker data including
        allocation, metrics, fundamental reports, and predictions.
    """
    start_time = time.perf_counter()

    # Extract asset classes from portfolio data
    asset_classes_dict = extract_asset_classes(portfolio_json)
    all_asset_class_data = {} # Initialize a dictionary to hold data for all asset classes

    for asset_class, _ in asset_classes_dict.items(): # Loop through each asset class
        logger.info("Processing asset class: %s", asset_class)

        # Get tickers for the current asset class
        tickers_data = get_stock_tickers(asset_class)
        
        # Check if tickers_data is None or empty for the asset class
        if tickers_data is None or asset_class not in tickers_data or not tickers_data[asset_class]:
            print(f"No tickers found or unable to retrieve tickers for asset class: {asset_class}. Skipping.")
            all_asset_class_data[asset_class] = {} # Assign empty dict if no tickers
            continue # Skip to the next asset class

        tickers = tickers_data[asset_class]

        try:
            df = calculate_and_filter_metrics(tickers) # calculate metrics and filter out stocks with under 10,000 daily average volume

            new_df = calculate_composite_scores(df) # calculate composite scores for each stock and pick the top 10
            new_df = new_df[:NUM_TOP_TICKERS]

            # Filter the original df to include only the top 5 tickers
            top_tickers = new_df['Ticker'].tolist()
            df_top_tickers = df[df['Ticker'].isin(top_tickers)]

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Top %d tickers for %s:\n%s", NUM_TOP_TICKERS, asset_class, df_top_tickers.to_string())

            # Create the final dictionary for the current asset class
            final_stock_data = {}

            for index, row in df_top_tickers.iterrows():
                ticker = row['Ticker']
                stock_metrics = row.drop('Ticker').to_dict()

                # Check if the asset class itself is considered an ETF class
                if is_etf_asset_class(asset_class):
                    if 'sector_beta' in stock_metrics:
                        del stock_metrics['sector_beta']

                    # print(f"Ticker {ticker} in ETF asset class '{asset_class}', removing sector_beta and getting description.")

                    fundamental_report = get_asset_description(ticker)
                    # ETFs don't have fundamental predictions, set to None or skip
                    fundamental_predictions = None 
                else:
                    print(f"Ticker {ticker} in non-ETF asset class '{asset_class}', retrieving fundamental report.")
                    fundamental_report_raw = FundamentalDataRepository().fetch_fundamental_report(ticker)
                    
                    # Handle the list returned by the repository
                    if fundamental_report_raw and isinstance(fundamental_report_raw, list):
                        fundamental_report = fundamental_report_raw  # Keep as list since it's List[Dict]
                    else:
                        fundamental_report = []  # Empty list if no data

                    # Get fundamental predictions only for non-ETFs
                    print(f"Fetching fundamental predictions for {ticker}...")
                    try:
                        # Fetch fundamental predictions (returns List[Dict])
                        fundamental_predictions_raw = FundamentalDataRepository().fetch_fundamental_estimates(ticker)
                        
                        # Handle the list returned by the repository
                        if fundamental_predictions_raw and isinstance(fundamental_predictions_raw, list):
                            fundamental_predictions = fundamental_predictions_raw  # Keep as list
                        else:
                            fundamental_predictions = {"error": "No Predictions Found for this ticker"}
                    except Exception as e: # Catch any errors during data fetching
                         print(f"Warning: An unexpected error occurred fetching predictions for {ticker}: {e}")
                         fundamental_predictions = {"error": f"Unexpected error fetching predictions: {e}"}

                stock_metrics['fundamental_report'] = fundamental_report
                # Only add predictions if they were successfully fetched and parsed
                if fundamental_predictions:
                    # Check if it's a list (successful fetch) or dict with error
                    if isinstance(fundamental_predictions, list):
                        stock_metrics['fundamental_predictions'] = fundamental_predictions
                    elif isinstance(fundamental_predictions, dict) and not fundamental_predictions.get("error"):
                        stock_metrics['fundamental_predictions'] = fundamental_predictions
                
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

    logger.info("Finished processing all asset classes.")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Aggregated data: %s", json.dumps(all_asset_class_data))

    end_time = time.perf_counter()
    duration = end_time - start_time
    logger.info("Phase-two ticker selection completed in %.2fs", duration)
    return all_asset_class_data

def make_phaseTwo_recommendations(asset_class_top_tickers):
    """
    Generate LLM-based investment recommendations for asset class tickers.
    
    Sends top ticker data to OpenAI API for analysis and recommendations,
    with JSON parsing and allocation validation for each asset class.
    
    Args:
        asset_class_top_tickers: Dictionary containing asset class allocation and ticker data.
        
    Returns:
        str: JSON string containing LLM recommendations with validated allocations,
        or None if API call fails or produces invalid output.
    """
    try:
        data_preview = json.dumps(asset_class_top_tickers, indent=2, default=str) if asset_class_top_tickers else "None"
        logger.info("Starting make_phaseTwo_recommendations with data: %s", data_preview)
    except Exception as e:
        logger.info("Starting make_phaseTwo_recommendations with data (serialization failed): %s", str(asset_class_top_tickers))
    try:
        # Convert the input dictionary to a JSON string for the prompt content
        data_string = json.dumps(asset_class_top_tickers)

        # --------------------------------------------------------------
        # Helper 🧹  to salvage almost-JSON strings coming back from the LLM
        # --------------------------------------------------------------
        def _attempt_safe_json_load(txt: str):
            """Try increasingly lenient strategies to convert *txt* to dict."""
            try:
                return json.loads(txt)
            except Exception:
                pass

            # 1️⃣  Strip trailing commas before } or ]
            no_trailing_commas = re.sub(r",\s*([\]}])", r"\\1", txt)
            try:
                return json.loads(no_trailing_commas)
            except Exception:
                pass

            # 2️⃣  Replace single quotes with double quotes (coarse but helps)
            swapped_quotes = no_trailing_commas.replace("'", '"')
            try:
                return json.loads(swapped_quotes)
            except Exception:
                pass

            # 3️⃣  Replace Python-ish literals with JSON equivalents
            literals_fixed = re.sub(r"\bTrue\b", "true", swapped_quotes)
            literals_fixed = re.sub(r"\bFalse\b", "false", literals_fixed)
            literals_fixed = re.sub(r"\bNone\b", "null", literals_fixed)
            try:
                return json.loads(literals_fixed)
            except Exception:
                return None

        user_profile = get_user_information()
        # Format the user profile in a more readable way
        user_info = user_profile.get("user_information", {})
        user_profile_formatted = f"""
Age: {user_info.get("age", "N/A")}
Net Worth: {user_info.get("net_worth", "N/A")}
Investment Size (as a percentage of net worth): {user_info.get("investment size(as a percentage of net worth)", "N/A")}
Risk Tolerance: {user_info.get("risk_tolerance", "N/A")}
Investment Goals: {user_info.get("investment_goals", "N/A")}
Time Horizon: {user_info.get("time_horizon", "N/A")}
Description: {user_info.get("Overall Description", "N/A").strip()}
"""

        # -------------------------------------------------------------------
        # Build prompts via the external templates to keep this file tidy
        # -------------------------------------------------------------------
        system_prompt = build_system_prompt(user_profile_formatted)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Phase-two system prompt:\n%s", system_prompt)
        user_prompt = build_user_prompt(data_string)

        logger.info("Calling OpenAI API for recommendations...")
        completion = client.chat.completions.create(
            model=model, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        logger.info("OpenAI API call completed successfully")

        # Extract and return the content from the response
        if completion.choices and completion.choices[0].message:
            response_content = completion.choices[0].message.content
            logger.info("Received API response, length: %d characters", len(response_content) if response_content else 0)

            # Clean the response content: Strip whitespace and remove markdown fences
            cleaned_content = response_content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:] # Remove ```json\n
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3] # Remove ```
            
            # Strip again in case there was whitespace around the fences
            cleaned_content = cleaned_content.strip() 

            # First, try a direct JSON parse of the cleaned content
            try:
                result_json = _attempt_safe_json_load(cleaned_content)
                if result_json is None:
                    raise json.JSONDecodeError("Could not parse after cleaning", cleaned_content, 0)
                
                # Validate and adjust the allocations provided by the LLM
                sector_alloc = asset_class_top_tickers.get('allocation', 0)
                recs = result_json.get('recommendations', [])
                if recs:
                    # Gracefully handle allocation key and ensure it's a float
                    for rec in recs:
                        alloc_val = 0.0
                        if 'allocation_percentage_within_asset_class' in rec:
                            alloc_val = rec.pop('allocation_percentage_within_asset_class')
                        elif 'allocation' in rec:
                            alloc_val = rec['allocation']
                        
                        try:
                            rec['allocation'] = float(alloc_val)
                        except (ValueError, TypeError):
                            logger.warning("Could not parse allocation value '%s' for ticker %s", alloc_val, rec.get('ticker'))
                            rec['allocation'] = 0.0

                    # Calculate the difference between LLM sum and target
                    llm_total_alloc = sum(rec.get('allocation', 0) for rec in recs)
                    adjustment = sector_alloc - llm_total_alloc

                    # If the difference is non-trivial, adjust the smallest allocation
                    if abs(adjustment) > 0.01 and len(recs) > 0:
                        logger.warning(
                            "LLM allocation sum (%.2f%%) differs from target (%.2f%%). Adjusting smallest allocation.",
                            llm_total_alloc, sector_alloc
                        )
                        min_alloc_rec = min(recs, key=lambda r: r.get('allocation', 0))
                        new_allocation = min_alloc_rec.get('allocation', 0) + adjustment

                        if new_allocation < 0:
                            logger.error(
                                "Adjustment for '%s' results in negative allocation (%.2f). Cannot balance. Check LLM output.",
                                min_alloc_rec.get('ticker'), new_allocation
                            )
                        else:
                            min_alloc_rec['allocation'] = new_allocation
                            logger.info(
                                "Adjusted allocation for '%s' by %.2f%% to meet target.",
                                min_alloc_rec.get('ticker'), adjustment
                            )

                logger.info("Successfully processed recommendations, returning JSON")
                return json.dumps(result_json)
            except json.JSONDecodeError:
                # Attempt to salvage JSON by extracting the first JSON object between braces
                json_match = re.search(r"\\{[\\s\\S]*\\}", cleaned_content)
                if json_match:
                    try:
                        result_json = _attempt_safe_json_load(json_match.group(0))
                        if result_json is None:
                            raise json.JSONDecodeError("Could not parse extracted braces", json_match.group(0), 0)
                        
                        # Also validate and adjust allocations in this fallback path
                        sector_alloc = asset_class_top_tickers.get('allocation', 0)
                        recs = result_json.get('recommendations', [])
                        if recs:
                            for rec in recs:
                                alloc_val = 0.0
                                if 'allocation_percentage_within_asset_class' in rec:
                                    alloc_val = rec.pop('allocation_percentage_within_asset_class')
                                elif 'allocation' in rec:
                                    alloc_val = rec['allocation']

                                try:
                                    rec['allocation'] = float(alloc_val)
                                except (ValueError, TypeError):
                                    rec['allocation'] = 0.0

                            llm_total_alloc = sum(rec.get('allocation', 0) for rec in recs)
                            adjustment = sector_alloc - llm_total_alloc

                            if abs(adjustment) > 0.01 and len(recs) > 0:
                                logger.warning(
                                    "LLM allocation sum (%.2f%%) differs from target (%.2f%%) in fallback. Adjusting.",
                                    llm_total_alloc, sector_alloc
                                )
                                min_alloc_rec = min(recs, key=lambda r: r.get('allocation', 0))
                                new_allocation = min_alloc_rec.get('allocation', 0) + adjustment
                                
                                if new_allocation < 0:
                                    logger.error(
                                        "Adjustment for '%s' in fallback results in negative allocation (%.2f).",
                                        min_alloc_rec.get('ticker'), new_allocation
                                    )
                                else:
                                    min_alloc_rec['allocation'] = new_allocation
                        
                        logger.info("Successfully processed recommendations in fallback path, returning JSON")
                        return json.dumps(result_json)
                    except json.JSONDecodeError:
                        # Still invalid – will fall through to final error
                        pass

            # If all attempts fail we log and return a structured error message
            print("Error: LLM response is not valid JSON even after cleaning or extracting.")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Original LLM Response:\n%s", response_content)
                logger.debug("Cleaned Response Attempted:\n%s", cleaned_content)
            return json.dumps({"error": "LLM response was not valid JSON."})
        else:
            print("Error: No response content received from API.")
            return None

    except Exception as e:
        logger.error("An error occurred while calling the API or processing data: %s", str(e))
        logger.error("Exception type: %s", type(e).__name__)
        import traceback
        logger.error("Full traceback: %s", traceback.format_exc())
        print(f"An error occurred while calling the API or processing data: {e}")
        return None

def run_phase_two(portfolio_data):
    """
    Execute complete Phase Two ticker selection and recommendation workflow.
    
    Orchestrates the full Phase Two process including ticker selection, metric calculation,
    LLM-based analysis, and final portfolio recommendation compilation.
    
    Args:
        portfolio_data: Portfolio dictionary containing asset class allocations from Phase One.
        
    Returns:
        Dict: Final portfolio recommendations dictionary mapping asset classes
        to their recommended tickers and allocations.
    """
    # ===============================================================================
    picks = pick_top_tickers_from_asset_classes(portfolio_data)
    # ===============================================================================

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Ticker picks: %s", json.dumps(picks))

    final_portfolio = {}

    logger.info("="*60)

    # Or if you're looping
    for asset_class_name in picks:
        data_for_class = picks[asset_class_name]

        # -------------------------------------------------------------
        # Skip classes with no usable ticker data to avoid pointless
        # (and often error-prone) LLM calls that return non-JSON text.
        # -------------------------------------------------------------
        if not data_for_class or data_for_class.get("error"):
            final_portfolio[asset_class_name] = {
                "error": data_for_class.get("error", "No data available for this asset class.")
            }
            logger.info("Skipping %s - no usable data available.", asset_class_name)
            continue
        if not data_for_class.get("tickers"):
            final_portfolio[asset_class_name] = {
                "error": "No valid tickers with sufficient data were found for this asset class."
            }
            logger.info("Skipping %s - no tickers passed the data quality filters.", asset_class_name)
            continue

        logger.info("Generating recommendations for asset class: %s", asset_class_name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Data for %s: %s", asset_class_name, json.dumps(data_for_class))

        # ===============================================================================
        recommendations_json = make_phaseTwo_recommendations(data_for_class)
        # ===============================================================================

        logger.info("Recommendations result for %s: %s", asset_class_name, recommendations_json)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Recommendations raw JSON for %s: %s", asset_class_name, recommendations_json)
        
        if recommendations_json:
            try:
                recommendations_data = json.loads(recommendations_json)
                final_portfolio[asset_class_name] = recommendations_data
                logger.info("Successfully parsed recommendations for %s", asset_class_name)

            except json.JSONDecodeError as e:
                logger.warning("Error parsing recommendations for %s: %s", asset_class_name, e)
                final_portfolio[asset_class_name] = {"error": "Failed to parse recommendations"}
        else:
            logger.warning("No recommendations returned for %s (recommendations_json is None or empty)", asset_class_name)
            final_portfolio[asset_class_name] = {"error": "No recommendations generated"}
    
    logger.info("Phase-two complete - final aggregated portfolio ready.")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Final Portfolio JSON:\n%s", json.dumps(final_portfolio, indent=2))
    
    return final_portfolio

if __name__ == "__main__":
    sample_portfolio_data_for_phase_two = {
        "portfolio": [
            {
                "asset_class": "other_specialized_reits",  # Example: Equity Sub-industry
                "allocation": 15.0,
                "reason": "medium conviction to this asset class"
            }
        ],
        "portfolio_thesis": "A growth-focused portfolio with significant allocation to technology and biotechnology, balanced by fixed income for stability. Includes a test for handling unknown asset classes."
    }


    # print(pick_top_tickers_from_asset_classes(sample_portfolio_data_for_phase_two))
    # print(make_phaseTwo_recommendations(pick_top_tickers_from_asset_classes(sample_portfolio_data_for_phase_two)))
    logger.info("Starting isolated run of phase_two with sample data...")
    final_recommendations = run_phase_two(sample_portfolio_data_for_phase_two)

    print("\n===========================================")
    print("Final Portfolio Recommendations (Phase Two):")
    logger.info(json.dumps(final_recommendations, indent=2))
    print("===========================================")

    logger.info("Isolated run of phase_two complete.")





