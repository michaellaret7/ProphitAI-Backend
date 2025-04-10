from optimizerAnalysts import free_search, communication_services_analyst, consumer_staples_analyst, consumer_discretionary_analyst, energy_analyst, financials_analyst, commodities_analyst, etf_analyst, treasuries_analyst, foreign_exchange_analyst, ig_credit_analyst, high_yield_analyst, emerging_market_analyst, healthcare_analyst, industrials_analyst, information_technology_analyst, materials_analyst, real_estate_analyst, utilities_analyst, get_equity_universe, get_etf_universe
from optimizerFormatting import format
from openai import OpenAI
import json
import os
from datetime import datetime
import traceback
from dotenv import load_dotenv
import re
import anthropic
import difflib  
import time

# Start timer
start_time = time.time()

# Load environment variables from .env file
load_dotenv()

# API KEYS
OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DeepSeek_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
Anthropic_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# MODELS
openai_model = os.environ.get("OPENAI_MODEL")
deepseek_model = os.environ.get("DEEPSEEK_MODEL")
anthropic_model = os.environ.get("ANTHROPIC_MODEL")

# MODEL
model = openai_model
client = OpenAI(api_key=OpenAI_API_KEY)

def parse_json_with_openai(text):
    # Simple regex to find JSON between triple quotes
    json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    json_matches = re.findall(json_pattern, text)
    
    if json_matches:
        try:
            # Try to parse the first JSON block found
            parsed_json = json.loads(json_matches[0])
            return parsed_json
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "portfolio": []}
    
    return {"error": "No JSON found in triple quotes", "portfolio": []}


def validate_and_fix_allocations(portfolio_content):
    """
    Validates portfolio allocations sum to 100% and fixes them if necessary.
    Also ensures each asset has required fields.
    
    Args:
        portfolio_content: The raw portfolio recommendation content
        
    Returns:
        The final validated portfolio JSON
    """
    model_client = OpenAI(api_key=DeepSeek_API_KEY, base_url="https://api.deepseek.com")
    model = "deepseek-reasoner"

    # Parse the initial JSON
    portfolio_json = parse_json_with_openai(portfolio_content)
    
    # Check for required structure
    if "portfolio" not in portfolio_json:
        print("Warning: No portfolio array found in JSON")
        # Create basic structure if missing
        portfolio_json = {"portfolio": []}
        return portfolio_json
    
    if not isinstance(portfolio_json["portfolio"], list):
        print("Warning: Portfolio is not an array")
        portfolio_json["portfolio"] = []
        return portfolio_json
    
    # Check for required fields in each asset
    required_fields = ["asset_class", "allocation", "reason"]
    for i, asset in enumerate(portfolio_json["portfolio"]):
        if not isinstance(asset, dict):
            print(f"Warning: Asset {i} is not a dictionary")
            continue
            
        for field in required_fields:
            if field not in asset:
                print(f"Warning: Missing required field '{field}' in asset {i}")
                # Add default value for missing field
                if field == "asset_class":
                    asset[field] = "unknown"
                elif field == "allocation":
                    asset[field] = "0"
                elif field == "reason":
                    asset[field] = "No reason provided"
    
    # Validate the allocations
    total_allocation = 0
    
    for asset in portfolio_json["portfolio"]:
        if "allocation" in asset:
            # Handle allocation as string (remove % sign if present)
            allocation_str = str(asset["allocation"]).strip()
            if allocation_str.endswith("%"):
                allocation_str = allocation_str[:-1]
            
            try:
                allocation = float(allocation_str)
                total_allocation += allocation
            except ValueError:
                print(f"Warning: Could not parse allocation value: {asset['allocation']}")
                # Set default allocation
                asset["allocation"] = "0"
    
    # Check if total allocation is 100% (allowing for small floating point errors)
    is_valid = abs(total_allocation - 100.0) < 0.5
    
    print("JSON:")
    print("-"*100)
    print(portfolio_json)
    
    # If allocations sum to 100%, return the original
    if is_valid:
        return portfolio_json
    
   
    # Otherwise, send a follow-up request to fix allocations
    print(f"\nWARNING: Total allocation is {total_allocation}%, which is not 100%.")
    print("Sending follow-up request to fix allocations...\n")
    
    # Create follow-up request to fix allocations
    follow_up_message = f"""
Your portfolio recommendation has allocations that sum to {total_allocation}%, which is not 100%.

Please adjust the allocations to ensure they sum to exactly 100%.
Remember:
1. Keep 5-7% of the portfolio in cash
2. Make sure there are at least 5 asset classes
3. ONLY use asset classes from the get_equity_universe and get_etf_universe tools
4. Return the COMPLETE portfolio with adjusted allocations in the same JSON format
5. EACH ASSET MUST INCLUDE asset_class, allocation, and reason fields

Original portfolio recommendation:
{json.dumps(portfolio_json, indent=2)}
"""
    
    # Use the provided client for follow-up request
    fix_response = model_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": """You are an elite portfolio manager who creates optimized investment portfolios. Your task now is to fix allocation percentages to ensure they sum to exactly 100%. Make sure each asset has an asset_class, allocation, and reason field.
                """
            },
            {
                "role": "user",
                "content": follow_up_message
            }
        ],
    )
    
    fixed_content = fix_response.choices[0].message.content
    print("\nFixed portfolio recommendation received.")
    
    # Parse the fixed JSON
    fixed_json = parse_json_with_openai(fixed_content)
    
    # Check if fixed JSON has required structure
    if "portfolio" not in fixed_json:
        print("Warning: Fixed JSON doesn't have a portfolio array")
        return portfolio_json
    
    # Check for required fields in each asset
    for i, asset in enumerate(fixed_json["portfolio"]):
        if not isinstance(asset, dict):
            print(f"Warning: Asset {i} in fixed JSON is not a dictionary")
            continue
            
        for field in required_fields:
            if field not in asset:
                print(f"Warning: Missing required field '{field}' in fixed asset {i}")
                # Keep original value if available, otherwise use default
                if field in portfolio_json["portfolio"][i] if i < len(portfolio_json["portfolio"]) else False:
                    asset[field] = portfolio_json["portfolio"][i][field]
                else:
                    if field == "asset_class":
                        asset[field] = "unknown"
                    elif field == "allocation":
                        asset[field] = "0"
                    elif field == "reason":
                        asset[field] = "No reason provided"
    
    # Validate the fixed allocations
    fixed_total = 0
    for asset in fixed_json.get("portfolio", []):
        if "allocation" in asset:
            allocation_str = str(asset["allocation"]).strip()
            if allocation_str.endswith("%"):
                allocation_str = allocation_str[:-1]
            
            try:
                allocation = float(allocation_str)
                fixed_total += allocation
            except ValueError:
                print(f"Warning: Could not parse fixed allocation value: {asset['allocation']}")
    
    is_fixed_valid = abs(fixed_total - 100.0) < 0.5
    
    print(f"Fixed allocations sum to {fixed_total}%")
    print("Fixed JSON:")
    print("-"*100)
    print(fixed_json)
    
    # Return the fixed JSON if it's valid, otherwise the original
    if is_fixed_valid:
        return fixed_json
    else:
        print(f"WARNING: Fixed allocations still don't sum to 100% (total: {fixed_total}%)")
        return portfolio_json


def validate_asset_classes(portfolio_json):
    """
    Validates that asset classes in the portfolio JSON exist in the database.
    If an asset class doesn't exist, finds the most similar one.
    Also ensures each portfolio item has required fields.
    
    Args:
        portfolio_json: The portfolio recommendation JSON
        
    Returns:
        The final validated portfolio JSON with valid asset classes
    """
    print("Validating asset classes...")
    
    try:
        # First, check for basic structure and required fields
        if not isinstance(portfolio_json, dict):
            print("Error: Portfolio JSON is not a dictionary")
            return {"portfolio": []}
            
        if "portfolio" not in portfolio_json:
            print("Error: Portfolio JSON does not contain 'portfolio' key")
            return {"portfolio": []}
            
        if not isinstance(portfolio_json["portfolio"], list):
            print("Error: Portfolio is not an array")
            portfolio_json["portfolio"] = []
            return portfolio_json
        
        # Check for required fields in each asset
        required_fields = ["asset_class", "allocation", "reason"]
        for i, asset in enumerate(portfolio_json["portfolio"]):
            if not isinstance(asset, dict):
                print(f"Warning: Asset {i} is not a dictionary")
                portfolio_json["portfolio"][i] = {"asset_class": "unknown", "allocation": "0", "reason": "Invalid asset"}
                continue
                
            for field in required_fields:
                if field not in asset:
                    print(f"Warning: Missing required field '{field}' in asset {i}")
                    # Add default value for missing field
                    if field == "asset_class":
                        asset[field] = "unknown"
                    elif field == "allocation":
                        asset[field] = "0"
                    elif field == "reason":
                        asset[field] = "No reason provided"
        
        # Load valid asset classes directly from database_schemas.json
        with open('database_schemas.json', 'r') as f:
            schema_data = json.load(f)
        
        # Extract all valid asset classes
        valid_asset_classes = []
        
        # Process equity sectors from database_schemas.json
        for sector_name, sector_info in schema_data.items():
            schemas = sector_info.get('schemas', {})
            
            # Add sector name
            valid_asset_classes.append(sector_name)
            
            for schema_name, schema_info in schemas.items():
                # Add industry name
                valid_asset_classes.append(schema_name)
                
                tables = schema_info.get('tables', {})
                for table_name in tables.keys():
                    # Add subindustry name
                    valid_asset_classes.append(table_name)
        
        # Add ETF categories from database_schemas.json schema "etf_data"
        if "etf_data" in schema_data:
            etf_schemas = schema_data.get("etf_data", {}).get("schemas", {})
            for etf_category in etf_schemas.keys():
                # Add ETF category
                valid_asset_classes.append(etf_category)
                
                tables = etf_schemas[etf_category].get('tables', {})
                for etf_type in tables.keys():
                    # Add ETF type
                    valid_asset_classes.append(etf_type)
        
        # Add "cash" as a valid asset class
        valid_asset_classes.append("cash")
        
        # Remove duplicates
        valid_asset_classes = list(set(valid_asset_classes))
        
        # Check each asset class in the portfolio
        replacements_made = False
        for asset in portfolio_json["portfolio"]:
            current_asset_class = asset.get("asset_class")
            
            # Skip if no asset class or already valid
            if not current_asset_class:
                asset["asset_class"] = "unknown"
                replacements_made = True
                continue
                
            if current_asset_class in valid_asset_classes:
                continue
            
            # Find the most similar asset class
            closest_match = difflib.get_close_matches(current_asset_class, valid_asset_classes, n=1, cutoff=0.6)
            
            if closest_match:
                print(f"Replacing invalid asset class '{current_asset_class}' with '{closest_match[0]}'")
                asset["asset_class"] = closest_match[0]
                replacements_made = True
            else:
                print(f"Warning: No close match found for '{current_asset_class}'. Setting to 'unknown'")
                asset["asset_class"] = "unknown"
                replacements_made = True
                    
        if replacements_made:
            print("Asset class validation complete - replacements were made")
        else:
            print("Asset class validation complete - all asset classes are valid")
            
        return portfolio_json
        
    except Exception as e:
        print(f"Error during asset class validation: {e}")
        traceback.print_exc()
        return portfolio_json  # Return original if validation fails


def optimize():
    current_date = datetime.now().strftime('%Y-%m-%d')
    account_info, positions_table, formatted_diversification, portfolio_metrics, stock_metrics, monthly_performance, correlations = format()
    
    # Ensure output directory exists
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create output file with timestamp in output directory
    output_filename = os.path.join(output_dir, f"portfolio_optimization_{current_date}.txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"PORTFOLIO OPTIMIZATION REPORT - {current_date}\n")
        f.write("="*80 + "\n\n")

    # Create the content string with portfolio data
    content = f"""
Analyze the provided portfolio data, which consists of positions in asset class representatives such as sector ETFs, bond ETFs, and other instruments. Recommend specific actions to improve returns and reduce risk by adjusting exposures to different asset classes.

REMEMBER THE CURRENT DATE IS {current_date}

------------------------------------------------------------------------------------------------------

### Current Asset Class Positions:

{positions_table}

### Account Information:

{account_info}

### Portfolio Metrics:

{portfolio_metrics}

### Monthly Performance:

{monthly_performance}

### Diversification:

{formatted_diversification}

### Correlation Matrix:

{correlations}

------------------------------------------------------------------------------------------------------

### RULES (YOU MUST FOLLOW THESE RULES):
1. NO HALLUCINATIONS, IF THERE IS SOMETHING YOU DO NOT KNOW OR IF THERE IS DATA MISSING, SAY YOU DO NOT KNOW, AND PROCEED LOGICALLY.
2. BE VERY SPECIFIC AND EXACT WITH YOUR RECOMMENDATIONS.
3. BE SUCCINCT AND CONCISE, BUT MAKE SURE TO EXPLAIN YOUR REASONING.
4. BE CREATIVE AND THINK OUTSIDE THE BOX.
5. KEEP 5-7% OF THE PORTFOLIO IN CASH.
6. THE SUM OF ALL POSITIONS SHOULD BE EQUAL TO 93%-95% OF THE ORIGINAL CASH VALUE OF THE PORTFOLIO.
7. MAKE SURE ALL OF THE ALLOCATION PERCENTAGES ADD UP TO 100% OF THE PORTFOLIO
    - IF ALL OF THE RECOMENDATIONS ADD UP TO LESS THAN 100% YOU MUST ADD MORE ASSET CLASSES TO THE PORTFOLIO UNTIL IT ADDS UP TO 100%
8. MAKE SURE THERE ARE AT LEAST 5 ASSET CLASSES IN THE PORTFOLIO
    - IF THERE ARE LESS THAN 5 ASSET CLASSES YOU MUST ADD MORE ASSET CLASSES TO THE PORTFOLIO

### Directions:
1. Analyze the current portfolio positions, account information, portfolio metrics, asset class metrics, monthly performance, diversification, and correlation matrix.
2. Identify the most significant issues affecting portfolio performance, focusing on asset class exposures.
3. IMPORTANT: You MUST use the data from the get_equity_universe and get_etf_universe tools to make specific recommendations for:
   - Specific equity sectors, industries, and sub-industries using ONLY the final category names from get_equity_universe
   - Specific ETFs using ONLY the final category names from get_etf_universe
   - Specific bond categories (Treasuries, Investment Grade, High Yield)
   - Specific commodities
   - Real Estate segments
   - Foreign Exchange exposures
   - Alternative Investments
4. DO NOT recommend generic ETF categories - use the specific sector/industry/ETF names exactly as they appear in the data tools.
5. Explain how each recommendation will improve the portfolio's return potential and risk profile.
6. Return portfolio in JSON format.

IMPORTANT:
- Be as granular and specific as possible with your recommendations.
- If you think a certain industry or sub industry will do really well based on the research add it to the allocation.
- I want you to be creative and think outside the box.
- The Goal is to create a portfolio that will outperform the S&P 500. 
- BE AS SPECIFIC AS POSSIBLE WITH YOUR RECOMMENDATIONS
- YOU CAN ONLY CHOOSE FROM THE ASSET CLASSES AND SECTORS/INDUSTRIES/SUBINDUSTRIES THAT ARE IN THE get_equity_universe and get_etf_universe tools.
- USE ONLY THE FINAL/LEAF NODE NAME AS THE ASSET_CLASS VALUE, NOT THE FULL HIERARCHICAL PATH.
- For example, use "multi_utilities" NOT "equity_sector_utilities_multi_utilities"

IMPORTANT: IN ADDITION to providing a human-readable recommendation, you MUST also output the same recommendation in a machine-readable JSON format for automated processing.

Clear Example of Correct Asset Class Format:
- ✓ CORRECT: "asset_class": "multi_utilities"  
- ✗ INCORRECT: "asset_class": "equity_sector_utilities_multi_utilities"

Your response should have two parts:
1. Human-readable portfolio recommendation
2. JSON-formatted recommendation with the following structure:

===JSON OUTPUT===
```json
{{
    "portfolio": [
    {{
      "asset_class": "ONLY USE THE FINAL NODE NAME from get_equity_universe or get_etf_universe (Example: Use 'multi_utilities' NOT 'equity_sector_utilities_multi_utilities')",
      "allocation": "percentage of the portfolio allocated to this asset class",
      "reason": "reason for the allocation"
    }},
  ]
}}
```
"""

    try:
        # Define all analyst tools in a more efficient way
        def create_analyst_tool(name, description):
            return {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        
        # Define search tool
        search_tool = {
            "type": "function",
            "function": {
                "name": "free_search",
                "description": "Search the internet for critical investment information that will enhance portfolio optimization. Construct DETAILED and SPECIFIC search queries to get the highest quality information. Follow these guidelines for effective searches:\n\n1. Be specific about the information you need (e.g., instead of 'tech stocks' use 'semiconductor industry outlook 2025 and top mid-cap opportunities')\n2. Include relevant timeframes in your query\n3. Target specific sectors, industries, or market segments\n4. Request numerical data like P/E ratios, growth rates, or market projections\n5. Break complex research needs into multiple focused searches\n\nYou should conduct AT LEAST 3-5 searches on different topics before making final recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Detailed, specific search query to find high-quality investment information. Include timeframes, metrics, sectors, or specific market segments."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
        
        # Define analyst tools with descriptions
        analyst_tools = {
            "communication_services_analyst": "Generate a comprehensive equity research report that provides actionable insights into the global equity market. The report covers market trends, sector performance, geopolitical events, investor sentiment, emerging opportunities, key risks, market valuation, and investment styles.",
            "commodities_analyst": "Generate a comprehensive commodities market analysis covering energy, metals, and agricultural markets. The report includes supply-demand fundamentals, price trends, physical market dynamics, inventory levels, forward curves, and geopolitical factors affecting commodity prices.",
            "etf_analyst": "Generate a comprehensive ETF market analysis covering equity, fixed income, commodity, and specialty ETFs. The report includes performance analysis, structural considerations, liquidity conditions, and specific ETF recommendations with rationale.",
            "treasuries_analyst": "Generate a comprehensive US Treasury market analysis covering yield curves, interest rate trends, and macroeconomic factors. The report includes analysis of recent economic data's impact on government bonds, behavior of the 2s10s yield curve, and upcoming factors likely to influence Treasury rates.",
            "foreign_exchange_analyst": "Generate a comprehensive foreign exchange market analysis covering currency valuation methodologies and key drivers of the U.S. Dollar. The report includes analysis of parity conditions, fundamental analysis, market-based valuation, and how these models interact over different time horizons.",
            "ig_credit_analyst": "Generate a comprehensive analysis of U.S. Investment Grade (IG) credit markets covering corporate fundamentals, interest rates, credit spreads, economic conditions, and sector-specific trends. The report examines key drivers affecting IG bond performance and provides outlook for credit markets.",
            "high_yield_analyst": "Generate a comprehensive analysis of high yield bonds and emerging market debt, comparing U.S. high yield factors with emerging market considerations. The report covers credit spreads, default risks, liquidity conditions, and macroeconomic influences affecting these higher-yielding fixed income assets.",
            "emerging_market_analyst": "Generate a comprehensive analysis of emerging markets (EM) equities and bonds, examining both global macro drivers and domestic fundamentals. The report covers the interplay between U.S. rates, risk sentiment, commodity prices, local economic conditions, and political factors that influence EM asset performance.",
            "consumer_staples_analyst": "Generate a comprehensive analysis of the consumer staples sector, examining market trends, consumer behavior, pricing dynamics, and competition. The report covers defensive characteristics, inflation impacts, global exposure, and growth opportunities within this essential sector.",
            "consumer_discretionary_analyst": "Generate a comprehensive analysis of the consumer discretionary sector, examining consumer spending trends, e-commerce developments, luxury vs. mass market dynamics, and cyclical factors. The report covers how economic conditions, interest rates, and consumer confidence affect discretionary spending patterns.",
            "energy_analyst": "Generate a comprehensive analysis of the energy sector, examining global supply-demand dynamics, price trends, regulatory influences, and the energy transition. The report covers both traditional fossil fuels and renewable energy sources, with analysis of key industry drivers and future outlooks.",
            "financials_analyst": "Generate a comprehensive analysis of the financial sector, examining banking, insurance, asset management, and fintech trends. The report covers interest rate sensitivities, credit conditions, regulatory developments, and technological disruption in financial services.",
            "healthcare_analyst": "Generate a comprehensive analysis of the healthcare sector, examining pharmaceutical, biotechnology, medical devices, and healthcare services trends. The report covers regulatory developments, innovation pipelines, pricing pressures, demographic trends, and competitive dynamics in healthcare.",
            "industrials_analyst": "Generate a comprehensive analysis of the industrials sector, examining manufacturing, transportation, aerospace, defense, and construction trends. The report covers global supply chains, automation, infrastructure spending, and industrial production cycles.",
            "information_technology_analyst": "Generate a comprehensive analysis of the information technology sector, examining software, hardware, semiconductors, and IT services trends. The report covers digital transformation, cloud computing, AI/ML developments, cybersecurity, and competitive dynamics in tech.",
            "materials_analyst": "Generate a comprehensive analysis of the materials sector, examining chemicals, mining, metals, and construction materials trends. The report covers commodity prices, supply-demand dynamics, sustainability initiatives, and global trade patterns affecting materials companies.",
            "real_estate_analyst": "Generate a comprehensive analysis of the real estate sector, examining residential, commercial, industrial, and specialized property trends. The report covers interest rate impacts, occupancy rates, rent growth, development pipelines, and sector-specific dynamics within real estate.",
            "utilities_analyst": "Generate a comprehensive analysis of the utilities sector, examining electric, gas, water, and renewable energy utilities. The report covers regulatory frameworks, interest rate sensitivity, environmental policies, infrastructure investments, and the energy transition's impact on utilities.",
            "get_equity_universe": "Retrieve and format sector/industry/subindustry data from database_schemas.json for optimal LLM ingestion, providing a hierarchical classification structure for financial markets.",
            "get_etf_universe": "Retrieve and format ETF classification data from the etf_data database for optimal LLM ingestion, providing a hierarchical ETF classification structure."
        }
        
        # Create all tools dynamically
        tool_map = {"free_search": search_tool}
        for name, description in analyst_tools.items():
            tool_map[name] = create_analyst_tool(name, description)
        
        # Helper function to process tool responses
        def process_tool_call(tool_call):
            function_name = tool_call.function.name
            
            # Common template for all tool responses
            def write_to_file(report_title, research_report):
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{'='*40}\n")
                    f.write(f"{report_title}\n")
                    f.write(f"{'='*40}\n\n")
                    f.write(research_report)
                    f.write("\n\n")
            
            # Special case for free search
            if function_name == "free_search":
                function_args = json.loads(tool_call.function.arguments)
                query = function_args.get("query")
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m for query: '{query}'\033[0m")
                
                # Search system prompt
                system_prompt = """You are a financial research analyst with 20+ years of experience who provides comprehensive, data-rich investment analysis. 
                Your responses should include specific numbers, trends, metrics, and expert insights. 
                Include relevant data points like P/E ratios, growth rates, market caps, dividend yields, sector-specific metrics, and comparative statistics whenever available. 
                Structure your response with clear sections and emphasize actionable insights that would help with portfolio construction. Be thorough, precise, and quantitative."""
                
                try:
                    search_response = free_search(system_prompt, query)
                except Exception as e:
                    print(f"Error during web search: {e}")
                    search_response = f"I attempted to search for information about '{query}' but encountered an error. Please try a different search query or continue with the available information."
                
                tool_response = f"Web Search Results for: '{query}'\n\n{search_response}\n\nNOTE: This information should be incorporated into your portfolio analysis. You should conduct additional searches on other topics to build a comprehensive view before making final recommendations."
                write_to_file(f"FREE SEARCH: {query}", search_response)
            
            # Special cases for get_equity_universe and get_etf_universe
            elif function_name == "get_equity_universe":
                print(f"\033[97m🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                try:
                    equity_universe_data = get_equity_universe()
                except Exception as e:
                    print(f"Error generating equity universe data: {e}")
                    equity_universe_data = f"I attempted to retrieve the equity universe data but encountered an error. Please continue with the available information or try using other research tools."
                
                tool_response = f"Equity Universe Data:\n\n{equity_universe_data}\n\nNOTE: Use this hierarchical classification data to inform your portfolio allocation decisions across different sectors and industries."
                write_to_file("EQUITY UNIVERSE DATA", equity_universe_data)
                
            elif function_name == "get_etf_universe":
                print(f"\033[97m🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                try:
                    etf_universe_data = get_etf_universe()
                except Exception as e:
                    print(f"Error generating ETF universe data: {e}")
                    etf_universe_data = f"I attempted to retrieve the ETF universe data but encountered an error. Please continue with the available information or try using other research tools."
                
                tool_response = f"ETF Universe Data:\n\n{etf_universe_data}\n\nNOTE: Use this hierarchical classification data to inform your portfolio allocation decisions across different ETF categories."
                write_to_file("ETF UNIVERSE DATA", etf_universe_data)
            
            # All other analyst tools
            else:
                print(f"\033[97m🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Map function names to their respective functions
                analyst_functions = {
                    "communication_services_analyst": communication_services_analyst,
                    "commodities_analyst": commodities_analyst,
                    "etf_analyst": etf_analyst,
                    "treasuries_analyst": treasuries_analyst,
                    "foreign_exchange_analyst": foreign_exchange_analyst,
                    "ig_credit_analyst": ig_credit_analyst,
                    "high_yield_analyst": high_yield_analyst,
                    "emerging_market_analyst": emerging_market_analyst,
                    "consumer_staples_analyst": consumer_staples_analyst,
                    "consumer_discretionary_analyst": consumer_discretionary_analyst,
                    "energy_analyst": energy_analyst,
                    "financials_analyst": financials_analyst,
                    "healthcare_analyst": healthcare_analyst,
                    "industrials_analyst": industrials_analyst,
                    "information_technology_analyst": information_technology_analyst,
                    "materials_analyst": materials_analyst,
                    "real_estate_analyst": real_estate_analyst,
                    "utilities_analyst": utilities_analyst,
                    "get_equity_universe": get_equity_universe,
                    "get_etf_universe": get_etf_universe
                }
                
                # Get the appropriate function and call it
                analyst_func = analyst_functions.get(function_name)
                
                try:
                    research_report = analyst_func()
                except Exception as e:
                    print(f"Error generating {function_name} report: {e}")
                    research_report = f"I attempted to generate a comprehensive {function_name} report but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format response based on function name
                friendly_name = function_name.replace("_", " ").title()
                tool_response = f"{friendly_name} Report:\n\n{research_report}\n\nNOTE: Use this analysis to inform your portfolio allocation decisions."
                write_to_file(f"{function_name.upper()} REPORT", research_report)
            
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_response
            }
        
        # Recursive function to handle multiple rounds of tool calls
        def handle_conversation(messages, tools, remaining_required_tools, round_num=1, max_rounds=50):
            print(f"\nStarting conversation round {round_num}...")
            
            # Phase definitions
            phase1_tools = list(analyst_tools.keys())
            phase2_min_searches = 3
            phase2_max_searches = 8
            
            # Track tool usage
            tool_calls_so_far = []
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "tool":
                    tool_calls_so_far.append(msg.get("name"))
                elif hasattr(msg, "role") and msg.role == "tool" and hasattr(msg, "name"):
                    tool_calls_so_far.append(msg.name)
            
            # Count searches and determine phase progress
            phase2_searches_completed = sum(1 for tool in tool_calls_so_far if tool == "free_search")
            phase1_index = sum(1 for tool in phase1_tools if tool in tool_calls_so_far)
            
            # Determine current phase
            current_phase = 1 if phase1_index < len(phase1_tools) else 2
            if (current_phase == 2 and phase2_searches_completed >= phase2_max_searches):
                current_phase = 3
                
            print(f"Round {round_num}: Phase {current_phase}, Phase1 tools: {phase1_index}/{len(phase1_tools)}, Searches: {phase2_searches_completed}/{phase2_max_searches}")
            
            # Handle max rounds reached
            if round_num > max_rounds:
                print(f"Reached maximum rounds ({max_rounds}). Getting final recommendation...")
                final_response = client.chat.completions.create(
                    model=model,
                    messages=messages + [{
                        "role": "user",
                        "content": "You've reached the maximum number of tool calls. Please provide your final portfolio recommendation now based on the information you have gathered so far. Remember to include both human-readable and JSON formats as specified in the original instructions."
                    }],
                    temperature=0.7
                )
                final_content = final_response.choices[0].message.content
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{'='*40}\nFINAL PORTFOLIO RECOMMENDATION (AFTER MAX ROUNDS)\n{'='*40}\n\n{final_content}")
                print(f"Final recommendation saved to {output_filename}")
                return final_content
            
            # Handle phase-specific actions
            if current_phase == 1:
                # Force usage of the next analyst tool in sequence
                next_tool = phase1_tools[phase1_index]
                print(f"Round {round_num}: Using {next_tool} (Phase 1)")
                
                forced_response = client.chat.completions.create(
                    model=model,
                    messages=messages + [{
                        "role": "user", 
                        "content": f"Please ONLY use the {next_tool} tool now."
                    }],
                    tools=[tool_map[next_tool]],
                    temperature=0.7
                )
                
                forced_message = forced_response.choices[0].message
                tool_calls = forced_message.tool_calls
                
                if tool_calls and tool_calls[0].function.name == next_tool:
                    messages.append(forced_message)
                    tool_response = process_tool_call(tool_calls[0])
                    messages.append(tool_response)
                    
                    if next_tool in remaining_required_tools:
                        remaining_required_tools.remove(next_tool)
                else:
                    messages.append({
                        "role": "user",
                        "content": f"You MUST use the {next_tool} tool before continuing."
                    })
                
            elif current_phase == 2:
                # Encourage free searches in phase 2
                remaining_searches = phase2_max_searches - phase2_searches_completed
                search_msg = f"Please use the free_search tool to search for specific market information. You have {remaining_searches} searches remaining."
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages + [{"role": "user", "content": search_msg}],
                    tools=[search_tool],
                    temperature=0.7
                )
                
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                
                if tool_calls:
                    messages.append(response_message)
                    for tool_call in tool_calls:
                        tool_response = process_tool_call(tool_call)
                        messages.append(tool_response)
            
            # Final recommendation in phase 3 or when minimum searches are completed
            if current_phase == 3 or (current_phase == 2 and phase2_searches_completed >= phase2_min_searches):
                print(f"Round {round_num}: Requesting final recommendation")
                
                final_response = client.chat.completions.create(
                    model=model,
                    messages=messages + [{
                        "role": "user", 
                        "content": "Now provide your final portfolio recommendation based on all the data gathered. Include both human-readable and JSON formats as specified."
                    }],
                    temperature=0.7
                )
                
                final_content = final_response.choices[0].message.content
                
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{'='*40}\nFINAL PORTFOLIO RECOMMENDATION\n{'='*40}\n\n{final_content}")
                print(f"Final recommendation saved to {output_filename}")
                return final_content
            
            # Continue to next round
            return handle_conversation(messages, tools, remaining_required_tools, round_num + 1, max_rounds)
        
        # Setup system message
        system_message = {
            "role": "system",
            "content": """You are an elite portfolio manager who creates optimized investment portfolios. Your exceptional track record comes from conducting EXTENSIVE RESEARCH before making any recommendation.
            
RESEARCH METHODOLOGY REQUIREMENTS:
1. Conduct AT LEAST 5-7 detailed searches on different aspects of the market before making recommendations.
2. For each search query, construct DETAILED and SPECIFIC prompts that will yield high-quality information.
3. Research multiple sectors, market caps, geographies, and asset classes.
4. Analyze macroeconomic trends, sector rotations, valuation metrics, and risk factors.
5. Investigate both tactical (1-6 month) and strategic (1-3 year) opportunities.
6. IMPORTANT: You MUST use the get_equity_universe and get_etf_universe tools first to understand available investment options before making recommendations.
7. ALWAYS use SPECIFIC names of sectors, industries, ETFs, and other assets exactly as they appear in the data from get_equity_universe and get_etf_universe.

ONLY after conducting all required research using the specified tools and any additional free searches should you formulate your final recommendation."""
        }
        
        # Required tools list
        required_tools = list(analyst_tools.keys())
        
        # Initial user message with process instructions
        user_message = {
            "role": "user",
            "content": content + "\n\nTo optimize the portfolio, follow this specific process:\n\n" +
            "1. First, use the get_equity_universe and get_etf_universe tools to see all available investment options\n" +
            "2. Then, use ALL the other required analyst tools in sequence\n" +
            "3. Then, use the free_search tool 3-6 times to research specific opportunities\n" +
            "4. Finally, provide your comprehensive portfolio recommendation using SPECIFIC asset names from the equity/ETF universe with both human-readable and JSON formats.\n\n"
        }
        
        # Set up initial messages and start conversation
        initial_messages = [system_message, user_message]
        remaining_required_tools = set(required_tools)
        all_tools = list(tool_map.values())
        
        print("Starting portfolio optimization research...")
        final_content = handle_conversation(initial_messages, all_tools, remaining_required_tools)
        
        if final_content:
            print("\n=== Final Portfolio Recommendation ===")
            return final_content
        else:
            error_msg = "No recommendation was generated."
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*40}\nERROR\n{'='*40}\n\n{error_msg}")
            print(error_msg)
            return error_msg
            
    except Exception as e:
        print(f"Error in portfolio optimization: {e}")
        traceback.print_exc()
        error_msg = f"An error occurred: {str(e)}"
        
        try:
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*40}\nERROR\n{'='*40}\n\n{error_msg}")
        except:
            pass
            
        return error_msg


# Main execution flow
final_content = optimize()
print(final_content)

portfolio_json = validate_and_fix_allocations(final_content)

portfolio_json = validate_asset_classes(portfolio_json)

print(portfolio_json)

from phaseTwo import analyze_portfolio

# Additional safety check before passing to analyze_portfolio
if not isinstance(portfolio_json, dict):
    print("Error: Portfolio JSON is not a dictionary, creating empty portfolio")
    portfolio_json = {"portfolio": []}

if "portfolio" not in portfolio_json:
    print("Error: Portfolio JSON does not contain 'portfolio' key, creating empty portfolio")
    portfolio_json = {"portfolio": []}

if not isinstance(portfolio_json["portfolio"], list):
    print("Error: Portfolio is not an array, creating empty portfolio array")
    portfolio_json["portfolio"] = []

# Check if the portfolio has any entries
if not portfolio_json["portfolio"]:
    print("Warning: Portfolio is empty, no assets to analyze")
    # Create a default portfolio to prevent downstream errors
    portfolio_json["portfolio"] = [
        {
            "asset_class": "unknown",
            "allocation": "100",
            "reason": "Default portfolio created due to empty portfolio data"
        }
    ]

# Final check for required fields in each asset
required_fields = ["asset_class", "allocation", "reason"]
for i, asset in enumerate(portfolio_json["portfolio"]):
    if not isinstance(asset, dict):
        print(f"Error: Asset {i} is not a dictionary, replacing with default asset")
        portfolio_json["portfolio"][i] = {
            "asset_class": "unknown",
            "allocation": "0",
            "reason": "Invalid asset entry"
        }
        continue
        
    for field in required_fields:
        if field not in asset:
            print(f"Error: Asset {i} missing required field '{field}', adding default value")
            if field == "asset_class":
                asset[field] = "unknown"
            elif field == "allocation":
                asset[field] = "0"
            elif field == "reason":
                asset[field] = "No reason provided"

# Now we can safely call analyze_portfolio
try:
    analyze_portfolio(portfolio_json)
    print("Portfolio analysis completed successfully")
except Exception as e:
    print(f"Error during portfolio analysis: {e}")
    traceback.print_exc()

# End timer and print execution time
end_time = time.time()
total_time = end_time - start_time
print(f"\nTotal processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")