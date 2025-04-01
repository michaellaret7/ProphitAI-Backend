from optimizerAnalysts import stock_universe, free_search, communication_services_analyst, consumer_staples_analyst, consumer_discretionary_analyst, energy_analyst, financials_analyst, commodities_analyst, etf_analyst, treasuries_analyst, foreign_exchange_analyst, ig_credit_analyst, high_yield_analyst, emerging_market_analyst, healthcare_analyst, industrials_analyst, information_technology_analyst, materials_analyst, real_estate_analyst, utilities_analyst
from optimizerFormatting import format
from openai import OpenAI
import json
import os
from datetime import datetime
import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API KEYS
OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY")
Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
DeepSeek_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# MODELS
openai_model = os.environ.get("OPENAI_MODEL")
perplexity_model = os.environ.get("PERPLEXITY_MODEL")
deepseek_model = os.environ.get("DEEPSEEK_MODEL")

# CLIENTS
client = OpenAI(api_key=OpenAI_API_KEY)
# client = OpenAI(api_key=DeepSeek_API_KEY, base_url="https://api.deepseek.com")

# MODEL
model = "o3-mini"

def optimize():
    current_date = datetime.now().strftime('%Y-%m-%d')
    account_info, positions_table, formatted_diversification, portfolio_metrics, stock_metrics, monthly_performance, correlations = format()
    
    # Create output file with timestamp
    output_filename = f"portfolio_optimization_{current_date}.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"PORTFOLIO OPTIMIZATION REPORT - {current_date}\n")
        f.write("="*80 + "\n\n")

    # Create the content string with portfolio data
    content = f"""
Analyze the provided portfolio data and recommend specific actions to improve returns and reduce risk. 
REMEMBER THE CURRENT DATE IS {current_date} 

------------------------------------------------------------------------------------------------------

### Portfolio Positions:

{positions_table}

### Account Information:

{account_info}

### Portfolio Metrics:

{portfolio_metrics}

### Stock Metrics:

{stock_metrics}

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
    3. BE SUCCUINCT AND CONCISE, BUT MAKE SURE TO EXPLAIN YOUR REASONING.
    4. BE CREATIVE IN YOUR STRATEGIES AND THINK OUTSIDE THE BOX.
    5. KEEP 5-7% OF THE PORTFOLIO IN CASH.
    6. THE SUM OF ALL POSITIONS SHOULD BE EQUAL TO 93%-95% OF THE ORIGINAL CASH VALUE OF THE PORTFOLIO.
    7. THE PORTFOLIO MUST CONTAIN EXACTLY 15-20 POSITIONS. THIS IS A STRICT REQUIREMENT - NEVER FEWER THAN 15 OR MORE THAN 20. IF NEEDED, ADD NEW POSITIONS OR REMOVE EXISTING ONES TO MEET THIS RANGE.

### Directions:
    1. Analyze the current portfolio positions, account information, portfolio metrics, stock metrics, monthly performance, diversification, and correlation matrix
    2. Identify the most significant issues affecting portfolio performance
    3. Recommend specific actions with exact positions and quantities:
        - Which specific positions should be reduced or sold completely (Bad Performers)
        - Which specific positions should be increased (Good Performers)
        - New long positions that should be added (with specific tickers and allocation amounts) 
        - New short positions that should be added (with specific tickers and allocation amounts)
        - Exact percentage adjustments to each position
    4. Explain how each recommendation will improve the portfolio's return potential
    5. Provide a clear implementation plan 
    6. Provide the final portfolio in a neatly organzied table format
    7. Return trade actions and final portfolio in json format

IMPORTANT:
    ### ACTIONS YOU ARE ALLOWED TO TAKE:
    1. BUY NEW ASSETS
    2. SHORT NEW ASSETS
    3. REDUCE EXISTING POSITIONS
    4. INCREASE EXISTING POSITIONS
    4. HOLD POSITIONS (DO NOT CHANGE)

    ### ASSETS YOU ARE ALLOWED TO BUY:
    1. STOCKS/EQUITIES
    2. BONDS
    3. EXCHANGE TRADED FUNDS (ETFS)
    4. COMMODITIES
    5. REAL ESTATE INVESTMENT TRUSTS (REITs)
    6. FOREIGN EXCHANGE
    7. ALTERNATIVE INVESTMENTS 

    ### FORMAT YOUR RESPONSE WITH THESE SECTIONS(BE CONCISE AND TO THE POINT):
    1. Portfolio Assessment
    2. Key Issues
    3. Specific fixes to issues 
    4. Specific Recommendations (with exact allocation size and tickers)
    5. Implementation Plan
    6. Expected Outcome

### THE EXACT TRADE EXECUTION INSTRUCTIONS IN THIS FORMAT:
Trade Action: [action(buy/sell/hold)] | Ticker: [ticker] | Quantity: [quantity]

### THIS IS THE FORMAT YOU SHOULD USE(THESE ARE EXAMPLES, YOU MUST FOLLOW THIS FORMAT, DO NOT PRINT UNCHAGNED ASSETS IN PORTFOLIO):
• SELL 'SOME STOCK' (100 shares) --> entire position  [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• SELL 'SOME STOCK' (50 shares) --> reduce from 100 → 50 [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• BUY 'SOME STOCK' (50 shares) --> increase from 100 → 150 [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• BUY 'SOME STOCK' (500 shares)  [TELL THE USER THE REASON FOR MAKING THIS TRADE]

### FINAL PORTFOLIO POSITIONS FORMAT(MUST BE 15-20 ASSETS):
HEADER: FINAL PORTFOLIO POSITIONS
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------

IMPORTANT: IN ADDITION to providing a human readable recommendation, you MUST also output the same recommendation in a machine-readable JSON format for automated processing.

Your response should have two parts:
1. Human-readable portfolio recommendation
2. JSON-formatted recommendation with the following structure:

===JSON OUTPUT===
```json
{{
  "trade_actions": [
    {{
      "action_type": "SELL|BUY|HOLD|SHORT|REDUCE|INCREASE",
      "ticker": "symbol",
      "quantity": "number or text description",
      "reason": "reason for the trade"
    }},
    ...
  ],
  "final_portfolio": [
    {{
      "ticker": "symbol",
      "position_type": "LONG|SHORT|CASH",
      "shares": "number",
      "allocation": "percentage of the portfolio that is allocated to this asset(this is a required field, do not leave blank and it should be in percent terms)",
    }},
    ...MUST CONTAIN BETWEEN 15-20 ENTRIES. NEVER FEWER THAN 15 OR MORE THAN 20...
  ]
}}
```

Place the JSON output at the end of your response after your human-readable recommendation, clearly separated by "===JSON OUTPUT===".
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
            "stock_universe_analyst": "Access the complete list of available stocks for investment, organized by sector, industry, and sub-industry. Provides access to 5000+ securities across all sectors. YOU MUST SELECT 15-20 DIVERSE POSITIONS FROM THIS UNIVERSE."
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
                    "stock_universe_analyst": stock_universe
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
                    }]
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
                    tools=[tool_map[next_tool]]
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
                    tools=[search_tool]
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
                    }]
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

ONLY after conducting all required research using the specified tools and any additional free searches should you formulate your final recommendation."""
        }
        
        # Required tools list
        required_tools = list(analyst_tools.keys())
        
        # Initial user message with process instructions
        user_message = {
            "role": "user",
            "content": content + "\n\nTo optimize the portfolio, follow this specific process:\n\n" +
            "1. First, use ALL the required analyst tools in sequence\n" +
            "2. Then, use the free_search tool 3-6 times to research specific opportunities\n" +
            "3. Finally, provide your comprehensive portfolio recommendation with both human-readable and JSON formats.\n\n"
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

def parse_json_with_openai(text):
    client = OpenAI(api_key=OpenAI_API_KEY)
    
    system_prompt = """You are a JSON extraction assistant. Your task is to extract ONLY the 'final_portfolio' 
    array from the provided text and return it as a valid, parseable JSON object with the structure:
    {"final_portfolio": [...array items...]}
    
    Do not include any explanations or other content. If the final_portfolio section is not found,
    return an empty array: {"final_portfolio": []}"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the 'final_portfolio' JSON from this text: {text}"}
        ],
        response_format={"type": "json_object"}
    )
    
    extracted_json = response.choices[0].message.content
    
    try:
        # Parse the extracted JSON
        parsed_json = json.loads(extracted_json)
        
        # Return the parsed JSON, ensuring 'final_portfolio' exists
        if isinstance(parsed_json, dict):
            if "final_portfolio" in parsed_json:
                return parsed_json
            # If 'final_portfolio' key is missing but another structure exists
            elif any(isinstance(v, list) for v in parsed_json.values()):
                # Find the first list and use that as final_portfolio
                for key, value in parsed_json.items():
                    if isinstance(value, list):
                        return {"final_portfolio": value}
            
        # If we couldn't find the right structure, return the whole JSON
        return parsed_json
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON from OpenAI response", "final_portfolio": []}


final_content = optimize()
print(final_content)
json = parse_json_with_openai(final_content)
print("JSON:")
print("-"*100)
print(json)