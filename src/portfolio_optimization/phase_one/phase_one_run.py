from openai import OpenAI
import json
import os
from datetime import datetime
import traceback
from dotenv import load_dotenv
import time
from src.portfolio_optimization.phase_two.phase_two_run import (
    pick_top_tickers_from_asset_classes,
    make_phaseTwo_recommendations,
)
from .phase_one_validation import (
    validate_and_fix_allocations,
    validate_asset_classes,
)
from .phase_one_prompts import SYSTEM_PROMPT, build_user_message, min_asset_classes, max_asset_classes
from src.data.user_information import get_user_information

# Start timer
start_time = time.time()

# Load environment variables from .env file
load_dotenv()

# API KEYS
OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
model = os.environ.get("OPENAI_MODEL")
client = OpenAI(api_key=OpenAI_API_KEY)

def optimize():
    # Import moved here
    from src.analysts import (
        free_search, 
        communication_services_analyst, 
        consumer_staples_analyst, 
        consumer_discretionary_analyst, 
        energy_analyst, 
        financials_analyst, 
        commodities_analyst, 
        etf_analyst, 
        treasuries_analyst, 
        foreign_exchange_analyst, 
        ig_credit_analyst, 
        high_yield_analyst, 
        emerging_market_analyst, 
        healthcare_analyst, 
        industrials_analyst, 
        information_technology_analyst, 
        materials_analyst, 
        real_estate_analyst, 
        utilities_analyst, 
        get_equity_universe, 
        get_etf_universe
    )
    
    current_date = datetime.now().strftime('%Y-%m-%d')

    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create output file with timestamp in output directory
    output_filename = os.path.join(output_dir, f"portfolio_optimization_{current_date}.txt")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"PORTFOLIO OPTIMIZATION REPORT - {current_date}\n")
        f.write("="*80 + "\n\n")

    # Build dynamic user prompt content using helper
    # build_user_message now fetches and formats data internally.
    content = build_user_message()

    # # -------------------- DEBUG: print prompts --------------------
    print("\n" + "=" * 100)
    print("SYSTEM PROMPT (Phase One):\n")
    print(SYSTEM_PROMPT)
    print("\n" + "-" * 100)
    print("USER PROMPT (first message to LLM):\n")
    print(content)
    print("=" * 100 + "\n")

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
                "description": """Search the internet for critical investment information that will enhance portfolio optimization. 
                Construct DETAILED, SPECIFIC, and COMPREHENSIVE search queries to get the highest quality, in-depth information. 
                Your queries should aim to uncover nuanced insights, data-driven analysis, and forward-looking perspectives. Follow these guidelines for effective searches:\n\n1. Be EXTREMELY specific about the information you need (e.g., instead of 'tech stocks' use 'Q3 2024 consensus earnings estimates for US large-cap semiconductor companies and key drivers for revisions' or 'Impact of recent Fed policy changes on high-yield corporate bond spreads and default rate outlook for the next 12 months').\n2. Include relevant timeframes, geographical regions, and market capitalizations in your query (e.g., 'next 5 years', 'European emerging markets', 'small-cap biotechnology').\n3. Target specific sectors, industries, sub-industries, or niche market segments. Go beyond broad categories.\n4. Explicitly request quantitative data, including but not limited to: P/E ratios, PEG ratios, growth rates (YoY, CAGR), market projections, valuation multiples, earnings estimates, financial ratios, economic indicators, and statistical correlations.\n5. Formulate queries to uncover underlying trends, competitive landscapes, regulatory impacts, technological disruptions, and macroeconomic influences.\n6. Break complex research needs into multiple, highly focused searches. Each search should target a distinct piece of the puzzle.\n7. Think like a seasoned financial analyst: what specific data or insight would give you an edge?\n\nYou should conduct AT LEAST 3-5 such comprehensive searches on different, strategically chosen topics before making final recommendations. The goal is to build a deeply informed perspective.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Detailed, specific, and comprehensive search query designed to find high-quality, in-depth investment information. Include timeframes, metrics, sectors, specific market segments, and aim for nuanced insights."
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
            "get_etf_universe": "Retrieve and format ETF classification data from the etf_data database for optimal LLM ingestion, providing a hierarchical ETF classification structure.",
            "get_user_information": "Retrieve user profile information like age, risk tolerance, and investment goals to tailor the portfolio."
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
                    # Check if research_report is None and provide a default value
                    if research_report is None:
                        research_report = "No data available for this report."
                        print(f"Warning: Received None for {report_title}")
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
            
            # Handle get_user_information tool
            elif function_name == "get_user_information":
                print(f"\033[97m🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                try:
                    user_info_data = get_user_information()
                    user_info_str = json.dumps(user_info_data, indent=2)
                except Exception as e:
                    print(f"Error getting user information: {e}")
                    user_info_str = f"I attempted to retrieve user information but encountered an error: {e}"
                
                tool_response = f"User Profile Information:\n\n{user_info_str}\n\nNOTE: Use this information to tailor the portfolio recommendations."
                write_to_file("USER INFORMATION", user_info_str)
            
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
                    "get_etf_universe": get_etf_universe,
                    "get_user_information": get_user_information
                }
                
                # Get the appropriate function and call it
                analyst_func = analyst_functions.get(function_name)
                
                try:
                    research_report = analyst_func()
                    # Add check for None result
                    if research_report is None:
                        print(f"Warning: {function_name} returned None. Using default message.")
                        research_report = f"The {function_name} tool was called but did not return any data. This could be due to a connection issue or service interruption."
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
            # Ensure get_user_information is always first
            phase1_tools = ["get_user_information"] + [t for t in analyst_tools.keys() if t != "get_user_information"]
            phase2_min_searches = 4
            phase2_max_searches = 10
            
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
                        "content": f"You've reached the maximum number of tool calls. Please provide your final portfolio recommendation now based on the information you have gathered so far. Ensure your final portfolio contains between {min_asset_classes} and {max_asset_classes} asset classes and adheres to all original formatting instructions."
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
                        "content": f"Now provide your final portfolio recommendation based on all the data gathered. Ensure your final portfolio contains between {min_asset_classes} and {max_asset_classes} asset classes and adheres to all original formatting instructions."
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
        system_message = {"role": "system", "content": SYSTEM_PROMPT}
        
        # Required tools list
        required_tools = list(analyst_tools.keys())
        
        # Initial user message with process instructions
        user_message = {
            "role": "user",
            "content": content
        }
        
        # Set up initial messages and start conversation
        initial_messages = [system_message, user_message]
        remaining_required_tools = set(required_tools)
        all_tools = list(tool_map.values())
        
        print("Starting portfolio optimization research...")
        final_content = handle_conversation(initial_messages, all_tools, remaining_required_tools)
        
        if not final_content:
            error_msg = "No recommendation was generated."
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*40}\nERROR\n{'='*40}\n\n{error_msg}")
            print(error_msg)
            return {"portfolio": []}

        print("\n=== Final Portfolio Recommendation ===")
        print(final_content)
        
        # Process the recommendation and prepare the portfolio for analysis
        portfolio_json = validate_and_fix_allocations(final_content)
        portfolio_json = validate_asset_classes(portfolio_json)

        print(portfolio_json)

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
                    "allocation": 100,
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
                    "allocation": 0,
                    "reason": "Invalid asset entry"
                }
                continue
            
            for field in required_fields:
                if field not in asset:
                    print(f"Error: Asset {i} missing required field '{field}', adding default value")
                    if field == "asset_class":
                        asset[field] = "unknown"
                    elif field == "allocation":
                        asset[field] = 0
                    elif field == "reason":
                        asset[field] = "No reason provided"
            
            # Ensure allocation is a number, not a string
            if field == "allocation" and isinstance(asset[field], str):
                try:
                    asset[field] = float(asset[field])
                except ValueError:
                    print(f"Error: Asset {i} has invalid allocation value, setting to 0")
                    asset[field] = 0

        # Now we can safely call analyze_portfolio
        try:
            # analyze_portfolio(portfolio_json)
            print("Portfolio analysis completed successfully")
        except Exception as e:
            print(f"Error during portfolio analysis: {e}")
            traceback.print_exc()

        # End timer and print execution time
        end_time = time.time()
        total_time = end_time - start_time
        print(f"\nTotal processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        
        return portfolio_json
            
    except Exception as e:
        print(f"Error in portfolio optimization: {e}")
        traceback.print_exc()
        error_msg = f"An error occurred: {str(e)}"
        
        try:
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write(f"\n\n{'='*40}\nERROR\n{'='*40}\n\n{error_msg}")
        except:
            pass
            
        return {"portfolio": []}

if __name__ == "__main__":
    final_portfolio = optimize()
    print(final_portfolio)
    # print("="*100)
    # print("PORTFOLIO SUMMARY:")
    
    # # Check if 'portfolio' key exists and is a list
    # if isinstance(final_portfolio, dict) and 'portfolio' in final_portfolio and isinstance(final_portfolio['portfolio'], list):
    #     for asset in final_portfolio['portfolio']:
    #         # Check if the asset is a dictionary and has the required keys
    #         if isinstance(asset, dict) and 'asset_class' in asset and 'allocation' in asset:
    #             ticker = asset['asset_class']
    #             allocation = asset['allocation']
    #             # Ensure allocation is a number before printing
    #             if isinstance(allocation, (int, float)):
    #                 print(f"{ticker}: {allocation}%")
    #             else:
    #                 print(f"{ticker}: Invalid allocation format ({allocation})")
    #         else:
    #             print(f"Skipping invalid asset entry: {asset}")
    # else:
    #     print("Could not find 'portfolio' list in the returned data or data is not a dictionary.")

    # picks = pick_top_tickers_from_asset_classes(final_portfolio)
    # print(picks)

    # final_portfolio = {}

    # print("="*100)

    # # Or if you're looping
    # for asset_class_name in picks:
    #     print(f"Asset class: {asset_class_name}")
    #     print(picks[asset_class_name])

    #     recommendations_json = make_phaseTwo_recommendations(picks[asset_class_name])
    #     print(recommendations_json)
        
    #     # Parse JSON string to Python object and add to final_portfolio
    #     if recommendations_json:
    #         try:
    #             recommendations_data = json.loads(recommendations_json)
    #             final_portfolio[asset_class_name] = recommendations_data
    #         except json.JSONDecodeError as e:
    #             print(f"Error parsing recommendations for {asset_class_name}: {e}")
    #             # Add error info to portfolio if parsing fails
    #             final_portfolio[asset_class_name] = {"error": "Failed to parse recommendations"}
    
    # print("\nFinal Portfolio:")
    # print(json.dumps(final_portfolio, indent=2))