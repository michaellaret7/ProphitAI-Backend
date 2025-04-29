import os
import json
import time
from datetime import datetime
import concurrent.futures

# Import from phaseTwo modules
from src.phaseTwo.data_retrieval import get_stock_tickers
from src.phaseTwo.stock_selection import select_top_performing_stocks, analyze_tickers_and_generate_recommendations

def extract_asset_classes(json_data):
    """
    Extract asset classes from portfolio JSON data.
    
    Args:
        json_data (dict): JSON data containing portfolio data
        
    Returns:
        dict: Dictionary mapping asset classes to their allocations, with 'cash' filtered out
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

def process_asset_class(asset, allocation):
    """
    Process an asset class to find optimal stocks.
    
    Args:
        asset (str): The asset class name
        allocation (float): The allocation percentage for this asset class
        
    Returns:
        dict: Dictionary mapping tickers to {'allocation': float, 'reason': str}
    """
    print(f"Processing asset class: {asset} with allocation: {allocation}%")
    ticker_dict = get_stock_tickers(asset)
    print(f"Got {len(ticker_dict.get(asset, []))} tickers for {asset}")
    
    filtered_tickers_dict = select_top_performing_stocks(ticker_dict)
    filtered_tickers = filtered_tickers_dict.get(asset, [])
    print(f"Filtered down to {len(filtered_tickers)} tickers for {asset}")

    # Use optimized portfolio manager with reasonable defaults for parallelism
    max_workers = min(4, os.cpu_count() or 2)
    result_json = analyze_tickers_and_generate_recommendations(filtered_tickers, max_workers=max_workers, batch_sentiment=True)
    
    try:
        # First, try direct JSON parsing
        try:
            result_data = json.loads(result_json)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from text
            start_index = result_json.find('{')
            end_index = result_json.rfind('}')
            
            if start_index != -1 and end_index != -1 and end_index > start_index:
                cleaned_json_str = result_json[start_index : end_index + 1]
                
                # Try parsing the extracted JSON
                result_data = json.loads(cleaned_json_str)
            else:
                # If no valid JSON structure found, create an error response
                print(f"Could not find valid JSON structure in response for {asset}")
                return {}
        
        # Extract recommendations
        recommendations = {}
        
        # Check if recommendations key exists and is a list
        if 'recommendations' in result_data and isinstance(result_data['recommendations'], list):
            # Count number of recommendations to distribute allocation
            num_recommendations = len(result_data['recommendations'])
            if num_recommendations > 0:
                # Distribute allocation evenly among selected stocks
                per_stock_allocation = allocation / num_recommendations
                
                for recommendation in result_data['recommendations']:
                    # Check if recommendation is a dict
                    if not isinstance(recommendation, dict):
                        continue
                        
                    ticker = recommendation.get('ticker')
                    justification = recommendation.get('justification', 'No justification provided')
                    
                    # Ensure ticker is valid
                    if ticker and isinstance(ticker, str) and ticker.strip():
                        recommendations[ticker.strip()] = {
                            'allocation': round(per_stock_allocation, 2),
                            'reason': justification
                        }
            
            if not recommendations:
                print(f"No valid recommendations extracted for {asset} despite valid JSON structure")
        else:
            print(f"No 'recommendations' key or empty recommendations list in response for {asset}")
            
        # Check for error message
        if 'error' in result_data:
            print(f"Error in LLM response for {asset}: {result_data['error']}")
            
        return recommendations

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON for {asset}: {e}")
        return {}
    except Exception as e:
        print(f"An error occurred while processing recommendations for {asset}: {e}")
        return {}

def analyze_portfolio(portfolio_data):
    """
    Analyze a portfolio to recommend optimal stocks for each asset class.
    
    Args:
        portfolio_data (dict): A dictionary containing portfolio data with asset classes
                              and their allocations.
                              
    Returns:
        dict: A dictionary mapping tickers to their allocations and justifications
        float: Total execution time in seconds
    """
    # Start the timer
    start_time = time.time()
    print(f"Starting portfolio analysis at {datetime.now().strftime('%H:%M:%S')}")
    
    final = {}

    # Extract asset classes with their allocations
    asset_class_allocations = extract_asset_classes(portfolio_data)
    print(f"Extracted asset classes with allocations: {asset_class_allocations}")

    # Determine optimal number of workers based on system capabilities and number of asset classes
    max_workers_asset_class = min(len(asset_class_allocations), os.cpu_count() or 2)  # Use CPU count as upper limit
    
    # Process asset classes in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_asset_class) as executor:
        # Submit all asset class analysis tasks
        future_to_asset = {
            executor.submit(process_asset_class, asset, allocation): asset 
            for asset, allocation in asset_class_allocations.items()
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_asset):
            asset = future_to_asset[future]
            try:
                asset_recommendations = future.result()
                final.update(asset_recommendations)
                print(f"Added recommendations for asset class: {asset}")
            except Exception as exc:
                print(f"Processing asset class {asset} generated an exception: {exc}")

    print("Final recommendations dictionary:")
    print(final)
    
    # End the timer and calculate elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print(f"\n========== PROCESS COMPLETED ==========")
    print(f"Total execution time: {minutes} minutes and {seconds} seconds")
    print(f"Finished at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Processed {len(asset_class_allocations)} asset classes with {len(final)} final recommendations")
    
    return final, elapsed_time 

