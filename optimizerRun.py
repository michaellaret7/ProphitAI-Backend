from optimizerAnalysts import free_search, communication_services_analyst, consumer_staples_analyst, consumer_discretionary_analyst, energy_analyst, financials_analyst, commodities_analyst, etf_analyst, treasuries_analyst, foreign_exchange_analyst, ig_credit_analyst, high_yield_analyst, emerging_market_analyst, healthcare_analyst, industrials_analyst, information_technology_analyst, materials_analyst, real_estate_analyst, utilities_analyst
from optimizerFormatting import format
from openai import OpenAI
import json
import numpy as np
import os
from datetime import datetime
import psycopg2
import pandas as pd
import re
import time 
import sys
import random
import itertools
import threading
import math
import curses

OpenAI_API_KEY = "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"
Sonar_API_KEY = "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"

api_key = os.environ.get("OPENAI_API_KEY", OpenAI_API_KEY)

client = OpenAI(
    api_key=api_key,
)

def optimize():

    current_date = datetime.now().strftime('%Y-%m-%d')

    account_info, positions_table, formatted_diversification, portfolio_metrics, stock_metrics, monthly_performance, correlations = format()
    

    # Create the content string with proper f-string interpolation
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

### RULES(YOU MUST FOLLOW THESE RULES):
1. NO HALLUCINATIONS, IF THERE IS SOMETHING YOU DO NOT KNOW OR IF THERE IS DATA MISSING, SAY YOU DO NOT KNOW, AND PROCEED LOGICALLY.
2. BE VERY SPECIFIC AND EXACT WITH YOUR RECOMMENDATIONS.
3. BE SUCCUINCT AND CONCISE, BUT MAKE SURE TO EXPLAIN YOUR REASONING.
4. BE SUCCESSFUL AND MAKE MONEY.
5. BE CREATIVE IN YOUR STRATEGIES AND THINK OUTSIDE THE BOX.
6. KEEP 10% OF THE PORTFOLIO IN CASH.
7. NONE OF THE POSITIONS SHOULD BE LESS THAN $10,000.
8. THE SUM OF ALL POSITIONS SHOULD BE EQUAL TO 85% OF THE PORTFOLIO.
9. THE PORTFOLIO SHOULD CONSIST OF AROUND 15-20 POSITIONS.

### Directions:
1. Analyze the current portfolio positions, account information, portfolio metrics, stock metrics, monthly performance, diversification, and correlation matrix
2. Identify the most significant issues affecting portfolio performance (concentration risk, underperforming assets, etc.)
3. Recommend specific actions with exact positions and quantities:
    - Which specific positions should be reduced or sold completely
    - Which specific positions should be increased
    - New long positions that should be added (with specific tickers and allocation amounts) YOU CAN CHOOSE ANY STOCK FROM ANY SECTOR OR INDUSTRY OR SUBINDUSTRY AND FROM ANY COUNTRY, AS LONG AS ITS A GOOD INVESTMENT AND WILL MAKE MONEY
    - New short positions that should be added (with specific tickers and allocation amounts) YOU CAN CHOOSE ANY STOCK FROM ANY SECTOR OR INDUSTRY OR SUBINDUSTRY AND FROM ANY COUNTRY, AS LONG AS ITS A GOOD INVESTMENT AND WILL MAKE MONEY
    - Exact percentage adjustments to each position
4. Explain how each recommendation will improve the portfolio's return potential
5. Provide a clear implementation plan 
6. Quantify the expected improvement in key metrics (volatility, returns, diversification)
7. Provide the final portfolio in a neatly organzied table

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

### FORMAT YOUR RESPONSE WITH THESE SECTIONS(BE CONCISE AND TO THE POINT):
1. Portfolio Assessment
2. Key Issues
3. Specific Recommendations (with exact position sizes and tickers)
4. Implementation Plan
5. Expected Outcome

### THEN I WANT THE EXACT TRADE EXECUTION INSTRUCTIONS IN THIS FORMAT:
Trade Action: [action(buy/sell/hold)] | Ticker: [ticker] | Quantity: [quantity]

### THIS IS THE FORMAT YOU SHOULD USE(THESE ARE EXAMPLES, YOU MUST FOLLOW THIS FORMAT, DO NOT PRINT UNCHAGNED ASSETS IN PORTFOLIO):
• SELL 'SOME STOCK' (100 shares) --> entire position  [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• SELL 'SOME STOCK' (50 shares) --> reduce from 100 → 50 [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• BUY 'SOME STOCK' (50 shares) --> increase from 100 → 150 [TELL THE USER THE REASON FOR MAKING THIS TRADE]
• BUY 'SOME STOCK' (500 shares)  [TELL THE USER THE REASON FOR MAKING THIS TRADE]

### ONCE YOU HAVE FINISHED YOUR ANALYSIS, THIS IS THE FORMAT YOU SHOULD USE FOR THE NEW PORTFOLIO:
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------
| Ticker | Quantity | Allocation | Market Value | bought/sold/held/position size change |
-----------------------------------------------------------------------------------------
"""
    
    # Call the OpenAI API with tool calling ability
    try:
        # Get API key from environment or use the hardcoded one as fallback
        api_key = os.environ.get("OPENAI_API_KEY", OpenAI_API_KEY)
        client = OpenAI(api_key=api_key)
        
        # Define tools
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
        
        communication_services_tool = {
            "type": "function",
            "function": {
                "name": "communication_services_analyst",
                "description": "Generate a comprehensive equity research report that provides actionable insights into the global equity market. The report covers market trends, sector performance, geopolitical events, investor sentiment, emerging opportunities, key risks, market valuation, and investment styles.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        commodities_research_tool = {
            "type": "function",
            "function": {
                "name": "commodities_analyst",
                "description": "Generate a comprehensive commodities market analysis covering energy, metals, and agricultural markets. The report includes supply-demand fundamentals, price trends, physical market dynamics, inventory levels, forward curves, and geopolitical factors affecting commodity prices.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        etf_research_tool = {
            "type": "function",
            "function": {
                "name": "etf_analyst",
                "description": "Generate a comprehensive ETF market analysis covering equity, fixed income, commodity, and specialty ETFs. The report includes performance analysis, structural considerations, liquidity conditions, and specific ETF recommendations with rationale.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        treasuries_tool = {
            "type": "function",
            "function": {
                "name": "treasuries_analyst",
                "description": "Generate a comprehensive US Treasury market analysis covering yield curves, interest rate trends, and macroeconomic factors. The report includes analysis of recent economic data's impact on government bonds, behavior of the 2s10s yield curve, and upcoming factors likely to influence Treasury rates.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        foreign_exchange_tool = {
            "type": "function",
            "function": {
                "name": "foreign_exchange_analyst",
                "description": "Generate a comprehensive foreign exchange market analysis covering currency valuation methodologies and key drivers of the U.S. Dollar. The report includes analysis of parity conditions, fundamental analysis, market-based valuation, and how these models interact over different time horizons.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        ig_credit_tool = {
            "type": "function",
            "function": {
                "name": "ig_credit_analyst",
                "description": "Generate a comprehensive analysis of U.S. Investment Grade (IG) credit markets covering corporate fundamentals, interest rates, credit spreads, economic conditions, and sector-specific trends. The report examines key drivers affecting IG bond performance and provides outlook for credit markets.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        high_yield_tool = {
            "type": "function",
            "function": {
                "name": "high_yield_analyst",
                "description": "Generate a comprehensive analysis of high yield bonds and emerging market debt, comparing U.S. high yield factors with emerging market considerations. The report covers credit spreads, default risks, liquidity conditions, and macroeconomic influences affecting these higher-yielding fixed income assets.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        emerging_markets_tool = {
            "type": "function",
            "function": {
                "name": "emerging_market_analyst",
                "description": "Generate a comprehensive analysis of emerging markets (EM) equities and bonds, examining both global macro drivers and domestic fundamentals. The report covers the interplay between U.S. rates, risk sentiment, commodity prices, local economic conditions, and political factors that influence EM asset performance.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        consumer_staples_tool = {
            "type": "function",
            "function": {
                "name": "consumer_staples_analyst",
                "description": "Generate a comprehensive analysis of the consumer staples sector, examining market trends, consumer behavior, pricing dynamics, and competition. The report covers defensive characteristics, inflation impacts, global exposure, and growth opportunities within this essential sector.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        consumer_discretionary_tool = {
            "type": "function",
            "function": {
                "name": "consumer_discretionary_analyst",
                "description": "Generate a comprehensive analysis of the consumer discretionary sector, examining consumer spending trends, e-commerce developments, luxury vs. mass market dynamics, and cyclical factors. The report covers how economic conditions, interest rates, and consumer confidence affect discretionary spending patterns.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        energy_tool = {
            "type": "function",
            "function": {
                "name": "energy_analyst",
                "description": "Generate a comprehensive analysis of the energy sector, examining global supply-demand dynamics, price trends, regulatory influences, and the energy transition. The report covers both traditional fossil fuels and renewable energy sources, with analysis of key industry drivers and future outlooks.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        financials_tool = {
            "type": "function",
            "function": {
                "name": "financials_analyst",
                "description": "Generate a comprehensive analysis of the financial sector, examining banking, insurance, asset management, and fintech trends. The report covers interest rate sensitivities, credit conditions, regulatory developments, and technological disruption in financial services.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        healthcare_tool = {
            "type": "function",
            "function": {
                "name": "healthcare_analyst",
                "description": "Generate a comprehensive analysis of the healthcare sector, examining pharmaceutical, biotechnology, medical devices, and healthcare services trends. The report covers regulatory developments, innovation pipelines, pricing pressures, demographic trends, and competitive dynamics in healthcare.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        industrials_tool = {
            "type": "function",
            "function": {
                "name": "industrials_analyst",
                "description": "Generate a comprehensive analysis of the industrials sector, examining manufacturing, transportation, aerospace, defense, and construction trends. The report covers global supply chains, automation, infrastructure spending, and industrial production cycles.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        information_technology_tool = {
            "type": "function",
            "function": {
                "name": "information_technology_analyst",
                "description": "Generate a comprehensive analysis of the information technology sector, examining software, hardware, semiconductors, and IT services trends. The report covers digital transformation, cloud computing, AI/ML developments, cybersecurity, and competitive dynamics in tech.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        materials_tool = {
            "type": "function",
            "function": {
                "name": "materials_analyst",
                "description": "Generate a comprehensive analysis of the materials sector, examining chemicals, mining, metals, and construction materials trends. The report covers commodity prices, supply-demand dynamics, sustainability initiatives, and global trade patterns affecting materials companies.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        real_estate_tool = {
            "type": "function",
            "function": {
                "name": "real_estate_analyst",
                "description": "Generate a comprehensive analysis of the real estate sector, examining residential, commercial, industrial, and specialized property trends. The report covers interest rate impacts, occupancy rates, rent growth, development pipelines, and sector-specific dynamics within real estate.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        utilities_tool = {
            "type": "function",
            "function": {
                "name": "utilities_analyst",
                "description": "Generate a comprehensive analysis of the utilities sector, examining electric, gas, water, and renewable energy utilities. The report covers regulatory frameworks, interest rate sensitivity, environmental policies, infrastructure investments, and the energy transition's impact on utilities.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # Helper function to process tool responses
        def process_tool_call(tool_call):
            function_name = tool_call.function.name
            
            # Get the appropriate response based on the tool called
            tool_response = ""
            if function_name == "free_search":
                function_args = json.loads(tool_call.function.arguments)
                query = function_args.get("query")
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m for query: '{query}'\033[0m")
                
                # Use the search function to get information from the web
                system_prompt = """You are a financial research analyst with 20+ years of experience who provides comprehensive, data-rich investment analysis. 
                Your responses should include specific numbers, trends, metrics, and expert insights. 
                Include relevant data points like P/E ratios, growth rates, market caps, dividend yields, sector-specific metrics, and comparative statistics whenever available. 
                Structure your response with clear sections and emphasize actionable insights that would help with portfolio construction. Be thorough, precise, and quantitative."""
                
                # Call the search function (it will print the full response internally)
                try:
                    search_response = free_search(system_prompt, query)
                except Exception as e:
                    print(f"Error during web search: {e}")
                    search_response = f"I attempted to search for information about '{query}' but encountered an error. Please try a different search query or continue with the available information."
                
                # Format the response appropriately
                tool_response = f"Web Search Results for: '{query}'\n\n{search_response}\n\nNOTE: This information should be incorporated into your portfolio analysis. You should conduct additional searches on other topics to build a comprehensive view before making final recommendations."
            
            elif function_name == "communication_services_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the equity research analyst function
                try:
                    research_report = communication_services_analyst()
                except Exception as e:
                    print(f"Error generating communication services research report: {e}")
                    research_report = "I attempted to generate a comprehensive communication services research report but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Equity Research Report:\n\n{research_report}\n\nNOTE: This comprehensive market analysis should form the foundation of your portfolio optimization strategy. Consider how these trends, opportunities, and risks impact your investment decisions."
            
            elif function_name == "commodities_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the commodities analyst function
                try:
                    research_report = commodities_analyst()
                except Exception as e:
                    print(f"Error generating commodities research report: {e}")
                    research_report = "I attempted to generate a comprehensive commodities market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Commodities Market Analysis:\n\n{research_report}\n\nNOTE: Use this commodities market analysis to inform your allocation to energy, metals, agriculture, and other commodity-related assets. Consider both direct commodity exposure and indirect exposure through equities in commodity-producing companies."
            
            elif function_name == "etf_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the ETF analyst function
                try:
                    research_report = etf_analyst()
                except Exception as e:
                    print(f"Error generating ETF research report: {e}")
                    research_report = "I attempted to generate a comprehensive ETF market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"ETF Market Analysis:\n\n{research_report}\n\nNOTE: Use this ETF analysis to identify optimal vehicles for implementing your asset allocation and tactical views. Consider both the underlying exposures and structural characteristics of recommended ETFs."
            
            elif function_name == "treasuries_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the treasuries analyst function
                try:
                    research_report = treasuries_analyst()
                except Exception as e:
                    print(f"Error generating treasuries research report: {e}")
                    research_report = "I attempted to generate a comprehensive US Treasury market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"US Treasury Market Analysis:\n\n{research_report}\n\nNOTE: Use this US Treasury market analysis to inform your allocation to government bonds and Treasury securities. Consider how the current interest rate environment affects both your fixed income holdings and other asset classes."
            
            elif function_name == "foreign_exchange_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the foreign exchange analyst function
                try:
                    research_report = foreign_exchange_analyst()
                except Exception as e:
                    print(f"Error generating foreign exchange research report: {e}")
                    research_report = "I attempted to generate a comprehensive foreign exchange market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Foreign Exchange Market Analysis:\n\n{research_report}\n\nNOTE: Use this foreign exchange analysis to inform your allocation to foreign currencies and currency-hedged assets. Consider how the current exchange rate environment affects both your foreign currency holdings and other asset classes."
            
            elif function_name == "ig_credit_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[97m\033[0m")
                
                # Call the IG credit analyst function
                try:
                    research_report = ig_credit_analyst()
                except Exception as e:
                    print(f"Error generating IG credit research report: {e}")
                    research_report = "I attempted to generate a comprehensive Investment Grade (IG) credit market analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Investment Grade Credit Market Analysis:\n\n{research_report}\n\nNOTE: Use this IG credit analysis to inform your allocation to investment grade corporate bonds. Consider how credit fundamentals, interest rates, and market technicals affect both your fixed income holdings and other asset classes."
            
            elif function_name == "high_yield_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the high yield analyst function
                try:
                    research_report = high_yield_analyst()
                except Exception as e:
                    print(f"Error generating high yield research report: {e}")
                    research_report = "I attempted to generate a comprehensive high yield and emerging markets debt analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"High Yield & Emerging Markets Debt Analysis:\n\n{research_report}\n\nNOTE: Use this high yield and emerging markets analysis to inform your allocation to higher yielding fixed income assets. Consider how credit risk, liquidity conditions, and macroeconomic factors differ between U.S. high yield and emerging market debt."
            
            elif function_name == "emerging_market_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the emerging market analyst function
                try:
                    research_report = emerging_market_analyst()
                except Exception as e:
                    print(f"Error generating emerging markets research report: {e}")
                    research_report = "I attempted to generate a comprehensive emerging markets analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Emerging Markets Analysis:\n\n{research_report}\n\nNOTE: Use this emerging markets analysis to inform your allocation to both EM equities and fixed income. Consider how global macro factors and domestic fundamentals influence different EM assets, and how they might perform in various economic scenarios."
            
            elif function_name == "consumer_staples_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the consumer staples analyst function
                try:
                    research_report = consumer_staples_analyst()
                except Exception as e:
                    print(f"Error generating consumer staples research report: {e}")
                    research_report = "I attempted to generate a comprehensive consumer staples analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Consumer Staples Analysis:\n\n{research_report}\n\nNOTE: Use this consumer staples analysis to inform your allocation to consumer staples stocks. Consider how these stocks are defensive in nature and how they might perform in various economic scenarios."
            
            elif function_name == "consumer_discretionary_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the consumer discretionary analyst function
                try:
                    research_report = consumer_discretionary_analyst()
                except Exception as e:
                    print(f"Error generating consumer discretionary research report: {e}")
                    research_report = "I attempted to generate a comprehensive consumer discretionary analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Consumer Discretionary Analysis:\n\n{research_report}\n\nNOTE: Use this consumer discretionary analysis to inform your allocation to consumer discretionary stocks. Consider how these stocks are cyclical in nature and how they might perform in various economic scenarios."
            
            elif function_name == "energy_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the energy analyst function
                try:
                    research_report = energy_analyst()
                except Exception as e:
                    print(f"Error generating energy research report: {e}")
                    research_report = "I attempted to generate a comprehensive energy analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Energy Analysis:\n\n{research_report}\n\nNOTE: Use this energy analysis to inform your allocation to energy stocks. Consider how the current energy market dynamics and the energy transition affect different energy companies."
            
            elif function_name == "financials_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the financials analyst function
                try:
                    research_report = financials_analyst()
                except Exception as e:
                    print(f"Error generating financials research report: {e}")
                    research_report = "I attempted to generate a comprehensive financials analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Financials Analysis:\n\n{research_report}\n\nNOTE: Use this financials analysis to inform your allocation to financial stocks. Consider how the current financial market dynamics and regulatory changes affect different financial companies."
            
            elif function_name == "healthcare_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the healthcare analyst function
                try:
                    research_report = healthcare_analyst()
                except Exception as e:
                    print(f"Error generating healthcare research report: {e}")
                    research_report = "I attempted to generate a comprehensive healthcare analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Healthcare Analysis:\n\n{research_report}\n\nNOTE: Use this healthcare analysis to inform your allocation to healthcare stocks. Consider how the current healthcare market dynamics and regulatory changes affect different healthcare companies."
            
            elif function_name == "industrials_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the industrials analyst function
                try:
                    research_report = industrials_analyst()
                except Exception as e:
                    print(f"Error generating industrials research report: {e}")
                    research_report = "I attempted to generate a comprehensive industrials analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Industrials Analysis:\n\n{research_report}\n\nNOTE: Use this industrials analysis to inform your allocation to industrial stocks. Consider how the current industrial market dynamics and supply chains affect different industrial companies."
            
            elif function_name == "information_technology_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the information technology analyst function
                try:
                    research_report = information_technology_analyst()
                except Exception as e:
                    print(f"Error generating information technology research report: {e}")
                    research_report = "I attempted to generate a comprehensive information technology analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Information Technology Analysis:\n\n{research_report}\n\nNOTE: Use this information technology analysis to inform your allocation to technology stocks. Consider how the current technology trends and competitive landscape affect different technology companies."
            
            elif function_name == "materials_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the materials analyst function
                try:
                    research_report = materials_analyst()
                except Exception as e:
                    print(f"Error generating materials research report: {e}")
                    research_report = "I attempted to generate a comprehensive materials analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Materials Analysis:\n\n{research_report}\n\nNOTE: Use this materials analysis to inform your allocation to materials stocks. Consider how commodity prices and global trade patterns affect different materials companies."
            
            elif function_name == "real_estate_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the real estate analyst function
                try:
                    research_report = real_estate_analyst()
                except Exception as e:
                    print(f"Error generating real estate research report: {e}")
                    research_report = "I attempted to generate a comprehensive real estate analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Real Estate Analysis:\n\n{research_report}\n\nNOTE: Use this real estate analysis to inform your allocation to real estate stocks and REITs. Consider how interest rates and property market dynamics affect different real estate companies."
            
            elif function_name == "utilities_analyst":
                print(f"\033[97m 🛠️ TOOL USED: \033[92m{function_name}\033[0m")
                
                # Call the utilities analyst function
                try:
                    research_report = utilities_analyst()
                except Exception as e:
                    print(f"Error generating utilities research report: {e}")
                    research_report = "I attempted to generate a comprehensive utilities analysis but encountered an error. Please continue with the available information or try using other research tools."
                
                # Format the response appropriately
                tool_response = f"Utilities Analysis:\n\n{research_report}\n\nNOTE: Use this utilities analysis to inform your allocation to utilities stocks. Consider how regulatory frameworks and the energy transition affect different utility companies."
            
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": tool_response
            }
        
        # Recursive function to handle multiple rounds of tool calls
        def handle_conversation(messages, tools, round_num=1, max_rounds=25):
            print(f"\nStarting conversation round {round_num}...")
            
            if round_num > max_rounds:
                print(f"Reached maximum rounds ({max_rounds}). Stopping to prevent infinite loop.")
                return messages[-1].content if hasattr(messages[-1], 'content') else "Maximum conversation rounds reached without final response."
            
            # Call the API
            response = client.chat.completions.create(
                model="gpt-4o",
                top_p=1.0,
                messages=messages,
                tools=tools if round_num < max_rounds else None  # Stop offering tools in final round
            )
            
            # Get the response message
            response_message = response.choices[0].message
            
            # Check for tool calls
            tool_calls = response_message.tool_calls
            
            if tool_calls:
                print(f"Round {round_num}: Found {len(tool_calls)} tool call(s)")
                
                # Add the assistant's message to the conversation
                messages.append(response_message)
                
                # Process each tool call
                for tool_call in tool_calls:
                    tool_response = process_tool_call(tool_call)
                    messages.append(tool_response)
                
                # Recursive call to handle next round
                return handle_conversation(messages, tools, round_num + 1, max_rounds)
            else:
                # No more tool calls, we have our final response
                print(f"Round {round_num}: No tool calls, received final response")
                return response_message.content
                
        print("Calling OpenAI API with tools...")
        
        # Initialize the conversation
        system_message = {
            "role": "system",
            "content": "You are an elite portfolio manager who builds sophisticated investment strategies based on deep market research. Your exceptional track record comes from conducting EXTENSIVE RESEARCH before making any recommendation.\n\nRESEARCH METHODOLOGY REQUIREMENTS:\n1. Conduct AT LEAST 5-7 detailed searches on different aspects of the market before making recommendations\n2. For each search query, construct DETAILED and SPECIFIC prompts (30-50 words) that will yield high-quality information\n3. Research multiple sectors, market caps, geographies, and asset classes\n4. Analyze macroeconomic trends, sector rotations, valuation metrics, and risk factors\n5. Investigate both tactical (1-6 month) and strategic (1-3 year) opportunities\n\nWHEN CONSTRUCTING SEARCH QUERIES:\n* Include specific timeframes (e.g., 'Q3 2025 outlook')\n* Request numerical data ('P/E ratios for mid-cap industrial stocks')\n* Target precise sectors or sub-sectors ('semiconductor equipment manufacturers' not just 'tech')\n* Ask for comparisons ('small cap vs large cap performance during rate cuts')\n* Seek expert consensus ('analyst expectations for healthcare sector 2025-2026')\n\nEXAMPLE HIGH-QUALITY SEARCH QUERIES:\n- 'US small cap industrial stocks with P/E under 15 and positive earnings revisions for 2025, focus on aerospace suppliers and automation'\n- 'Healthcare sector rotation analysis: which subsectors outperform when inflation moderates and Fed cuts rates, historical data 2000-2024'\n- 'Top performing dividend aristocrats with international revenue exposure, valuation metrics and 2025 earnings projections'\n\nONLY after conducting this comprehensive research should you formulate your final recommendation."
        }
        
        user_message = {
            "role": "user",
            "content": content + "\n\nBefore making recommendations, conduct thorough market research in this sequence:\n\n" + \
            "1. MARKET ANALYSIS (REQUIRED, MUST CONDUCT ALL TOOLS)\n" + \
            "IMPORTANT: You must conduct all the tools in the order they are listed below before conducting any targeted research.\n" + \
            "   - Use communication_services_analyst for comprehensive equity communication services market insights\n" + \
            "   - Use consumer_staples_analyst for consumer staples sector analysis\n" + \
            "   - Use consumer_discretionary_analyst for consumer discretionary sector analysis\n" + \
            "   - Use energy_analyst for comprehensive energy sector analysis\n" + \
            "   - Use financials_analyst for financial sector analysis\n" + \
            "   - Use commodities_analyst if the portfolio includes or should include commodities\n" + \
            "   - Use treasuries_analyst for detailed US Treasury market analysis\n" + \
            "   - Use foreign_exchange_analyst for currency valuation and FX market insights\n" + \
            "   - Use ig_credit_analyst for Investment Grade corporate bond analysis\n" + \
            "   - Use high_yield_analyst for High Yield and Emerging Market debt analysis\n" + \
            "   - Use emerging_market_analyst for detailed Emerging Markets equity and fixed income analysis\n" + \
            "   - Use etf_analyst to identify optimal ETF vehicles for implementation\n\n" + \
            "2. TARGETED RESEARCH (AS NEEDED, DO AS MANY SEARCHES AS YOU NEED TO MAKE THE BEST RECOMMENDATIONS)\n" + \
            "   - Use free_search to investigate specific opportunities or concerns \n" + \
            "   - Use free_search to search any information you need to make the best portfolio recommendations\n\n"    
        }
        
        initial_messages = [system_message, user_message]
        
        # Define the required tools in order
        required_tools = [
            "communication_services_analyst", 
            "consumer_staples_analyst",
            "consumer_discretionary_analyst",
            "energy_analyst",
            "financials_analyst",
            "healthcare_analyst",
            "industrials_analyst",
            "information_technology_analyst",
            "materials_analyst",
            "real_estate_analyst",
            "utilities_analyst",
            "treasuries_analyst", 
            "ig_credit_analyst", 
            "high_yield_analyst", 
            "foreign_exchange_analyst", 
            "emerging_market_analyst", 
            "commodities_analyst", 
            "etf_analyst"
        ]
        
        # Create tool mapping for easy access
        tool_map = {
            "communication_services_analyst": communication_services_tool,
            "treasuries_analyst": treasuries_tool,
            "ig_credit_analyst": ig_credit_tool,
            "high_yield_analyst": high_yield_tool,
            "foreign_exchange_analyst": foreign_exchange_tool,
            "emerging_market_analyst": emerging_markets_tool,
            "commodities_analyst": commodities_research_tool,
            "etf_analyst": etf_research_tool,
            "search_tool": search_tool,
            "consumer_staples_analyst": consumer_staples_tool,
            "consumer_discretionary_analyst": consumer_discretionary_tool,
            "energy_analyst": energy_tool,
            "financials_analyst": financials_tool,
            "healthcare_analyst": healthcare_tool,
            "industrials_analyst": industrials_tool,
            "information_technology_analyst": information_technology_tool,
            "materials_analyst": materials_tool,
            "real_estate_analyst": real_estate_tool,
            "utilities_analyst": utilities_tool
        }
        
        # Track the conversation
        current_messages = initial_messages.copy()
        used_required_tools = []
        
        # Phase 1: Force the use of each required tool in sequence
        print("\n=== Phase 1: Required Market Analysis Tools ===")
        for tool_name in required_tools:
            tool = tool_map.get(tool_name)
            if not tool:
                print(f"Warning: Tool {tool_name} not found in available tools, skipping")
                continue
                
            print(f"Forcing usage of {tool_name}...")
            
            # Add a message to force the tool use
            force_message = {
                "role": "user",
                "content": f"Please use the {tool_name} now to conduct the required analysis before proceeding. Do not skip this step."
            }
            current_messages.append(force_message)
            
            # Use only this specific tool for this round
            phase1_result = handle_conversation(current_messages, [tool], max_rounds=2)
            
            # Update the conversation messages
            # We need to preserve the conversation history but remove the last response
            # since handle_conversation returns the content, not the full message object
            if len(current_messages) > 0 and current_messages[-1]["role"] == "user":
                # If the last message is from the user, we append the assistant's response
                current_messages.append({"role": "assistant", "content": phase1_result})
            
            used_required_tools.append(tool_name)
            print(f"Successfully used {tool_name}")
        
        # Phase 2: Allow free search and other targeted research
        print("\n=== Phase 2: Targeted Research with Free Search ===")
        
        # Add a transition message
        transition_message = {
            "role": "user",
            "content": "Now that you've completed all required market analyses, you can proceed with targeted research using free_search to investigate specific opportunities or gather additional information needed for your portfolio recommendations."
        }
        current_messages.append(transition_message)
        
        # Allow a few rounds of free search
        available_search_tools = [tool_map.get("search_tool")]
            
        # Run a few rounds of free search
        for i in range(1, 5):
            print(f"Free search round {i}...")
            search_result = handle_conversation(current_messages, available_search_tools, max_rounds=2)
            current_messages.append({"role": "assistant", "content": search_result})
        
        # Phase 3: Generate final recommendation
        print("\n=== Phase 3: Final Portfolio Recommendation ===")
        final_message = {
            "role": "user",
            "content": "Based on all the market analyses and targeted research you've conducted, please provide your final portfolio recommendation."
        }
        current_messages.append(final_message)
        
        # Use all tools for the final recommendation
        all_tools = [tool for tool in tool_map.values() if tool]
        final_content = handle_conversation(current_messages, all_tools)
        
        print("\n=== Final Portfolio Recommendation ===")
        
        if final_content:
            print(final_content)
            return final_content
        else:
            print("No content in final response, returning what's available.")
            return "No recommendation was generated."
            
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred while calling the OpenAI API: {str(e)}"


optimize()
