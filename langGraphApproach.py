from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Literal, List, Dict, Any
from openai import OpenAI
import json
import os
import time
from datetime import datetime
import re

# Import all analysts from optimizerAnalysts
from optimizerAnalysts import (
    free_search, communication_services_analyst, consumer_staples_analyst, 
    consumer_discretionary_analyst, energy_analyst, financials_analyst, 
    commodities_analyst, etf_analyst, treasuries_analyst, foreign_exchange_analyst, 
    ig_credit_analyst, high_yield_analyst, emerging_market_analyst,
    healthcare_analyst, industrials_analyst, information_technology_analyst, 
    materials_analyst, real_estate_analyst, utilities_analyst
)
from optimizerFormatting import format

# API keys - use environment variables or fallback to hardcoded
OpenAI_API_KEY = "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"
DeepSeek_API_KEY = "sk-384b07e8f612439ebb4c7bda149d40af"

DeepSeek_API_KEY = os.environ.get("DEEPSEEK_API_KEY", DeepSeek_API_KEY)  
OpenAI_API_KEY = os.environ.get("OPENAI_API_KEY", OpenAI_API_KEY)

openai_model = "gpt-4o"
deepseek_model = "deepseek-reasoner"

# Initialize OpenAI client
client = OpenAI(api_key=OpenAI_API_KEY)
client_deepseek = OpenAI(api_key=DeepSeek_API_KEY, base_url="https://api.deepseek.com")

def database_schema_reader():
    """
    Read the entire database_schemas.json file and return its contents.
    This provides a comprehensive overview of all available tickers 
    organized by sector, industry, and sub-industry.
    """
    try:
        print("Reading database schema file...")
        with open("database_schemas.json", "r") as file:
            schemas = json.load(file)
        print("Database schema loaded successfully.")
        return schemas
    except Exception as e:
        print(f"Error reading database schema: {e}")
        return {"error": str(e)}

# Define the graph state
class PortfolioState(TypedDict):
    portfolio_data: Dict[str, Any]
    research_results: Dict[str, str]
    free_search_results: List[Dict[str, str]]
    required_tools_completed: List[str]
    current_phase: Literal["required_analysis", "targeted_research", "final_recommendation"]
    required_tools_order: List[str]
    next_required_tool_index: int
    free_search_count: int
    final_recommendation: str
    database_schemas: Dict[str, Any]

# Define nodes (functions) for the graph
def initialize_state(state: dict = None) -> PortfolioState:
    """Prepare the initial portfolio data"""
    print("Initializing portfolio state...")
    account_info, positions_table, formatted_diversification, portfolio_metrics, stock_metrics, monthly_performance, correlations = format()
    
    # Load database schemas
    database_schemas = database_schema_reader()
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Define the required tools order matching optimizerRun.py
    required_tools_order = [
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
        "etf_analyst",
        "database_schema_reader"
    ]
    
    return {
        "portfolio_data": {
            "current_date": current_date,
            "account_info": account_info,
            "positions_table": positions_table,
            "formatted_diversification": formatted_diversification,
            "portfolio_metrics": portfolio_metrics,
            "stock_metrics": stock_metrics,
            "monthly_performance": monthly_performance,
            "correlations": correlations
        },
        "research_results": {},
        "free_search_results": [],
        "required_tools_completed": [],
        "current_phase": "required_analysis",
        "required_tools_order": required_tools_order,
        "next_required_tool_index": 0,
        "free_search_count": 0,
        "final_recommendation": "",
        "database_schemas": database_schemas
    }

# Required Analysis Phase - Tool Execution Functions

def run_communication_services_analysis(state: PortfolioState) -> PortfolioState:
    """Run the communication services analyst tool"""
    print("Running communication services analysis...")
    
    try:
        research_report = communication_services_analyst()
        if research_report is not None:
            state["research_results"]["communication_services"] = research_report
            state["required_tools_completed"].append("communication_services_analyst")
        else:
            state["research_results"]["communication_services"] = "Communication services analysis failed to produce results."
    except Exception as e:
        print(f"Error in communication services analysis: {e}")
        state["research_results"]["communication_services"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_consumer_staples_analysis(state: PortfolioState) -> PortfolioState:
    """Run the consumer staples analyst tool"""
    print("Running consumer staples analysis...")
    
    try:
        research_report = consumer_staples_analyst()
        if research_report is not None:
            state["research_results"]["consumer_staples"] = research_report
            state["required_tools_completed"].append("consumer_staples_analyst")
        else:
            state["research_results"]["consumer_staples"] = "Consumer staples analysis failed to produce results."
    except Exception as e:
        print(f"Error in consumer staples analysis: {e}")
        state["research_results"]["consumer_staples"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_consumer_discretionary_analysis(state: PortfolioState) -> PortfolioState:
    """Run the consumer discretionary analyst tool"""
    print("Running consumer discretionary analysis...")
    
    try:
        research_report = consumer_discretionary_analyst()
        if research_report is not None:
            state["research_results"]["consumer_discretionary"] = research_report
            state["required_tools_completed"].append("consumer_discretionary_analyst")
        else:
            state["research_results"]["consumer_discretionary"] = "Consumer discretionary analysis failed to produce results."
    except Exception as e:
        print(f"Error in consumer discretionary analysis: {e}")
        state["research_results"]["consumer_discretionary"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_energy_analysis(state: PortfolioState) -> PortfolioState:
    """Run the energy analyst tool"""
    print("Running energy analysis...")
    
    try:
        research_report = energy_analyst()
        if research_report is not None:
            state["research_results"]["energy"] = research_report
            state["required_tools_completed"].append("energy_analyst")
        else:
            state["research_results"]["energy"] = "Energy analysis failed to produce results."
    except Exception as e:
        print(f"Error in energy analysis: {e}")
        state["research_results"]["energy"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_financials_analysis(state: PortfolioState) -> PortfolioState:
    """Run the financials analyst tool"""
    print("Running financials analysis...")
    
    try:
        research_report = financials_analyst()
        if research_report is not None:
            state["research_results"]["financials"] = research_report
            state["required_tools_completed"].append("financials_analyst")
        else:
            state["research_results"]["financials"] = "Financials analysis failed to produce results."
    except Exception as e:
        print(f"Error in financials analysis: {e}")
        state["research_results"]["financials"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_healthcare_analysis(state: PortfolioState) -> PortfolioState:
    """Run the healthcare analyst tool"""
    print("Running healthcare analysis...")
    
    try:
        research_report = healthcare_analyst()
        if research_report is not None:
            state["research_results"]["healthcare"] = research_report
            state["required_tools_completed"].append("healthcare_analyst")
        else:
            state["research_results"]["healthcare"] = "Healthcare analysis failed to produce results."
    except Exception as e:
        print(f"Error in healthcare analysis: {e}")
        state["research_results"]["healthcare"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_industrials_analysis(state: PortfolioState) -> PortfolioState:
    """Run the industrials analyst tool"""
    print("Running industrials analysis...")
    
    try:
        research_report = industrials_analyst()
        if research_report is not None:
            state["research_results"]["industrials"] = research_report
            state["required_tools_completed"].append("industrials_analyst")
        else:
            state["research_results"]["industrials"] = "Industrials analysis failed to produce results."
    except Exception as e:
        print(f"Error in industrials analysis: {e}")
        state["research_results"]["industrials"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_information_technology_analysis(state: PortfolioState) -> PortfolioState:
    """Run the information technology analyst tool"""
    print("Running information technology analysis...")
    
    try:
        research_report = information_technology_analyst()
        if research_report is not None:
            state["research_results"]["information_technology"] = research_report
            state["required_tools_completed"].append("information_technology_analyst")
        else:
            state["research_results"]["information_technology"] = "Information technology analysis failed to produce results."
    except Exception as e:
        print(f"Error in information technology analysis: {e}")
        state["research_results"]["information_technology"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_materials_analysis(state: PortfolioState) -> PortfolioState:
    """Run the materials analyst tool"""
    print("Running materials analysis...")
    
    try:
        research_report = materials_analyst()
        if research_report is not None:
            state["research_results"]["materials"] = research_report
            state["required_tools_completed"].append("materials_analyst")
        else:
            state["research_results"]["materials"] = "Materials analysis failed to produce results."
    except Exception as e:
        print(f"Error in materials analysis: {e}")
        state["research_results"]["materials"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_real_estate_analysis(state: PortfolioState) -> PortfolioState:
    """Run the real estate analyst tool"""
    print("Running real estate analysis...")
    
    try:
        research_report = real_estate_analyst()
        if research_report is not None:
            state["research_results"]["real_estate"] = research_report
            state["required_tools_completed"].append("real_estate_analyst")
        else:
            state["research_results"]["real_estate"] = "Real estate analysis failed to produce results."
    except Exception as e:
        print(f"Error in real estate analysis: {e}")
        state["research_results"]["real_estate"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_utilities_analysis(state: PortfolioState) -> PortfolioState:
    """Run the utilities analyst tool"""
    print("Running utilities analysis...")
    
    try:
        research_report = utilities_analyst()
        if research_report is not None:
            state["research_results"]["utilities"] = research_report
            state["required_tools_completed"].append("utilities_analyst")
        else:
            state["research_results"]["utilities"] = "Utilities analysis failed to produce results."
    except Exception as e:
        print(f"Error in utilities analysis: {e}")
        state["research_results"]["utilities"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_treasuries_analysis(state: PortfolioState) -> PortfolioState:
    """Run the treasuries analyst tool"""
    print("Running treasuries analysis...")
    
    try:
        research_report = treasuries_analyst()
        if research_report is not None:
            state["research_results"]["treasuries"] = research_report
            state["required_tools_completed"].append("treasuries_analyst")
        else:
            state["research_results"]["treasuries"] = "Treasuries analysis failed to produce results."
    except Exception as e:
        print(f"Error in treasuries analysis: {e}")
        state["research_results"]["treasuries"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_ig_credit_analysis(state: PortfolioState) -> PortfolioState:
    """Run the investment grade credit analyst tool"""
    print("Running investment grade credit analysis...")
    
    try:
        research_report = ig_credit_analyst()
        if research_report is not None:
            state["research_results"]["ig_credit"] = research_report
            state["required_tools_completed"].append("ig_credit_analyst")
        else:
            state["research_results"]["ig_credit"] = "Investment grade credit analysis failed to produce results."
    except Exception as e:
        print(f"Error in investment grade credit analysis: {e}")
        state["research_results"]["ig_credit"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_high_yield_analysis(state: PortfolioState) -> PortfolioState:
    """Run the high yield analyst tool"""
    print("Running high yield analysis...")
    
    try:
        research_report = high_yield_analyst()
        if research_report is not None:
            state["research_results"]["high_yield"] = research_report
            state["required_tools_completed"].append("high_yield_analyst")
        else:
            state["research_results"]["high_yield"] = "High yield analysis failed to produce results."
    except Exception as e:
        print(f"Error in high yield analysis: {e}")
        state["research_results"]["high_yield"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_foreign_exchange_analysis(state: PortfolioState) -> PortfolioState:
    """Run the foreign exchange analyst tool"""
    print("Running foreign exchange analysis...")
    
    try:
        research_report = foreign_exchange_analyst()
        if research_report is not None:
            state["research_results"]["foreign_exchange"] = research_report
            state["required_tools_completed"].append("foreign_exchange_analyst")
        else:
            state["research_results"]["foreign_exchange"] = "Foreign exchange analysis failed to produce results."
    except Exception as e:
        print(f"Error in foreign exchange analysis: {e}")
        state["research_results"]["foreign_exchange"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_emerging_market_analysis(state: PortfolioState) -> PortfolioState:
    """Run the emerging market analyst tool"""
    print("Running emerging market analysis...")
    
    try:
        research_report = emerging_market_analyst()
        if research_report is not None:
            state["research_results"]["emerging_market"] = research_report
            state["required_tools_completed"].append("emerging_market_analyst")
        else:
            state["research_results"]["emerging_market"] = "Emerging market analysis failed to produce results."
    except Exception as e:
        print(f"Error in emerging market analysis: {e}")
        state["research_results"]["emerging_market"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_commodities_analysis(state: PortfolioState) -> PortfolioState:
    """Run the commodities analyst tool"""
    print("Running commodities analysis...")
    
    try:
        research_report = commodities_analyst()
        if research_report is not None:
            state["research_results"]["commodities"] = research_report
            state["required_tools_completed"].append("commodities_analyst")
        else:
            state["research_results"]["commodities"] = "Commodities analysis failed to produce results."
    except Exception as e:
        print(f"Error in commodities analysis: {e}")
        state["research_results"]["commodities"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    return state

def run_etf_analysis(state: PortfolioState) -> PortfolioState:
    """Run the ETF analyst tool"""
    print("Running ETF analysis...")
    
    try:
        research_report = etf_analyst()
        if research_report is not None:
            state["research_results"]["etf"] = research_report
            state["required_tools_completed"].append("etf_analyst")
        else:
            state["research_results"]["etf"] = "ETF analysis failed to produce results."
    except Exception as e:
        print(f"Error in ETF analysis: {e}")
        state["research_results"]["etf"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    print(f"DEBUG: ETF analysis completed, next_required_tool_index = {state['next_required_tool_index']}")
    
    return state

def run_database_schema_analysis(state: PortfolioState) -> PortfolioState:
    """Process the database schemas to make them available for research phase"""
    print("Processing database schemas...")
    
    # The schemas are already loaded in the state during initialization,
    # but we'll create a summary to add to the research results for reference
    
    try:
        schemas = state["database_schemas"]
        
        # Create a summary of the database schemas
        summary = "# Database Schema Analysis\n\n"
        summary += "## Available Investment Universe\n\n"
        
        # Count total tickers and sectors
        total_tickers = 0
        sector_counts = {}
        
        for sector_key, sector_data in schemas.items():
            sector_name = sector_key.replace("equity_sector_", "").replace("_", " ").title()
            sector_counts[sector_name] = 0
            
            # Count tickers in this sector
            for schema in sector_data.get("schemas", {}).values():
                for table in schema.get("tables", {}).values():
                    tickers = table.get("tickers", [])
                    sector_counts[sector_name] += len(tickers)
                    total_tickers += len(tickers)
        
        # Add summary statistics
        summary += f"Total available tickers: {total_tickers}\n"
        summary += f"Total sectors: {len(sector_counts)}\n\n"
        summary += "### Sector Breakdown:\n"
        
        for sector, count in sector_counts.items():
            summary += f"- {sector}: {count} tickers ({(count/total_tickers*100):.1f}%)\n"
        
        # Store summary in research results
        state["research_results"]["database_schemas"] = summary
        state["required_tools_completed"].append("database_schema_reader")
        
        print("Database schema processing completed.")
    except Exception as e:
        print(f"Error in database schema processing: {e}")
        state["research_results"]["database_schemas"] = f"Error: {str(e)}"
    
    # Update the next tool index
    state["next_required_tool_index"] += 1
    
    # After completing all required tools including this one, transition to targeted research phase
    if state["next_required_tool_index"] >= len(state["required_tools_order"]):
        print("DEBUG: All required tools completed, transitioning to targeted_research phase")
        state["current_phase"] = "targeted_research"
    
    return state

# Targeted Research Phase
def run_free_research(state: PortfolioState) -> PortfolioState:
    """Conduct free research based on insights from previous analyst reports"""
    # System prompt for query generation
    system_prompt = """You are a financial research analyst requesting specific information.
    Based on the completed research analyses so far, generate 3 specific search queries
    that would help optimize this portfolio. 
    
    Identify gaps in the existing research or areas that need deeper investigation.
    Focus specifically on the insights from the research reports, not the portfolio data.
    Make your queries specific, detailed, and actionable. Each query should target a different aspect of 
    portfolio optimization based on the insights from the research reports."""
    
    # Create a summary of completed research to inform search queries
    research_summary = "COMPLETED RESEARCH INSIGHTS:\n\n"
    
    # Add research results
    for area, analysis in state["research_results"].items():
        research_summary += f"\n{area.upper()} ANALYSIS:\n"
        # Include an excerpt of each analysis
        excerpt = analysis
        research_summary += f"{excerpt}\n"
    
    # Generate search queries using LLM
    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": research_summary}
            ]
        )
        
        queries_text = response.choices[0].message.content
        
        # Extract queries using a simple approach
        queries = [line.strip() for line in queries_text.split("\n") 
                  if line.strip() and not line.startswith("#") and not line.startswith("-")]
        
        # If we didn't extract meaningful queries, use some defaults
        if len(queries) < 2:
            queries = [
                "Impact of current Federal Reserve policy on asset allocation strategy",
                "Emerging investment opportunities based on global macro trends",
                "Sector rotation strategies given current market conditions and treasury outlook"
            ]
        
        print(f"Generated {len(queries)} search queries:")
        for i, query in enumerate(queries):
            print(f"  Query {i+1}: {query}")
        
        # Execute the queries (limit to 3 to avoid excessive API calls)
        # Process multiple queries for more comprehensive research
        for i, query in enumerate(queries[:3]):  
            print(f"Running free search #{i+1}: {query}")
            try:
                research_system_prompt = """You are a financial research analyst with 20+ years of experience who provides comprehensive, data-rich investment analysis. 
                Your responses should include specific numbers, trends, metrics, and expert insights. 
                Include relevant data points like P/E ratios, growth rates, market caps, dividend yields, sector-specific metrics, and comparative statistics whenever available. 
                Structure your response with clear sections and emphasize actionable insights that would help with portfolio construction. Be thorough, precise, and quantitative."""
                
                search_result = free_search(research_system_prompt, query)
                
                if search_result is not None:
                    state["free_search_results"].append({
                        "query": query,
                        "result": search_result
                    })
                else:
                    state["free_search_results"].append({
                        "query": query,
                        "result": "Free search failed to produce results."
                    })
                
                # Brief pause to avoid rate limits
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error in free search for query '{query}': {e}")
                state["free_search_results"].append({
                    "query": query,
                    "result": f"Error: {str(e)}"
                })
    
    except Exception as e:
        print(f"Error generating search queries: {e}")
        # Fall back to a default query if query generation fails
        default_query = "Investment strategies based on current treasury and foreign exchange market conditions"
        print(f"Falling back to default query: {default_query}")
        
        try:
            research_system_prompt = """You are a financial research analyst with 20+ years of experience who provides comprehensive, data-rich investment analysis."""
            search_result = free_search(research_system_prompt, default_query)
            
            if search_result is not None:
                state["free_search_results"].append({
                    "query": default_query,
                    "result": search_result
                })
            else:
                state["free_search_results"].append({
                    "query": default_query,
                    "result": "Free search failed to produce results."
                })
                
        except Exception as e:
            print(f"Error in fallback free search: {e}")
            state["free_search_results"].append({
                "query": default_query,
                "result": f"Error: {str(e)}"
            })
    
    # Increment free search count
    state["free_search_count"] += 1
    print(f"DEBUG: free_search_count increased to {state['free_search_count']}")
    
    # Check if we should move to final recommendation phase
    if state["free_search_count"] >= 2:  # Changed from 5 to 3 free searches
        print("DEBUG: free_search_count reached 3, transitioning to final_recommendation phase")
        state["current_phase"] = "final_recommendation"
    
    return state

# Phase transition routing
def route_based_on_phase(state: PortfolioState) -> PortfolioState:
    """Determine next step based on current phase"""
    # Add debugging output
    print(f"DEBUG: route_based_on_phase called with phase: {state['current_phase']}")
    print(f"DEBUG: next_required_tool_index: {state['next_required_tool_index']}")
    print(f"DEBUG: required_tools_completed: {len(state['required_tools_completed'])}")
    print(f"DEBUG: free_search_count: {state['free_search_count']}")
    
    # This is the key function that was causing the error.
    # Instead of just returning the routing value, we return the state
    # and the conditional edge will extract the current_phase for routing
    return state

# Route to specific required tool
def route_to_specific_tool(state: PortfolioState) -> PortfolioState:
    """Route to the next required tool based on the index"""
    # Add debugging output
    print(f"DEBUG: route_to_specific_tool called with index: {state['next_required_tool_index']}")
    print(f"DEBUG: total required tools: {len(state['required_tools_order'])}")
    
    # Check if we've completed all required tools
    if state["next_required_tool_index"] >= len(state["required_tools_order"]):
        # Transition to next phase if all required tools completed
        print("DEBUG: All required tools completed, transitioning to targeted_research phase")
        state["current_phase"] = "targeted_research"
    
    return state

# Final Recommendation Phase
def generate_portfolio_recommendation(state: PortfolioState) -> PortfolioState:
    """Generate final portfolio recommendations based on all research"""
    print("Generating final portfolio recommendation...")
    
    # Prepare the portfolio data
    portfolio_data = state["portfolio_data"]
    
    # Create the content string for the recommendation prompt
    content = f"""
Analyze the provided portfolio data and recommend specific actions to improve returns and reduce risk. 
REMEMBER THE CURRENT DATE IS {portfolio_data['current_date']} 

------------------------------------------------------------------------------------------------------

### Portfolio Positions:

{portfolio_data['positions_table']}

### Account Information:

{portfolio_data['account_info']}

### Portfolio Metrics:

{portfolio_data['portfolio_metrics']}

### Stock Metrics:

{portfolio_data['stock_metrics']}

### Monthly Performance:

{portfolio_data['monthly_performance']}

### Diversification:

{portfolio_data['formatted_diversification']}

### Correlation Matrix:

{portfolio_data['correlations']}

------------------------------------------------------------------------------------------------------

### RULES (YOU MUST FOLLOW THESE RULES):
1. NO HALLUCINATIONS, IF THERE IS SOMETHING YOU DO NOT KNOW OR IF THERE IS DATA MISSING, SAY YOU DO NOT KNOW, AND PROCEED LOGICALLY.
2. BE VERY SPECIFIC AND EXACT WITH YOUR RECOMMENDATIONS.
3. BE SUCCUINCT AND CONCISE, BUT MAKE SURE TO EXPLAIN YOUR REASONING.
4. BE SUCCESSFUL AND MAKE MONEY.
5. BE CREATIVE IN YOUR STRATEGIES AND THINK OUTSIDE THE BOX.
6. KEEP 10% OF THE PORTFOLIO IN CASH.
7. NONE OF THE POSITIONS SHOULD BE LESS THAN $10,000.
8. THE SUM OF ALL POSITIONS SHOULD BE EQUAL TO 85% OF THE ORIGINAL CASH VALUE OF THE PORTFOLIO.
9. THE PORTFOLIO MUST CONSIST OF 15-20 ASSET POSITIONS.
10. USE TICKERS FROM THE INVESTMENT UNIVERSE FOUND IN THE DATABASE SCHEMAS ANALYSIS WHENEVER POSSIBLE.

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
6. Quantify the expected improvement in key metrics (volatility, returns, diversification, drawdown ratio, sharpe ratio, sortino ratio, max drawdown, etc.)
7. Provide the final portfolio in a neatly organzied table

### ACTIONS YOU ARE ALLOWED TO TAKE:
1. BUY NEW ASSETS
2. SHORT NEW ASSETS
3. REDUCE EXISTING POSITIONS
4. INCREASE EXISTING POSITIONS
5. HOLD POSITIONS (DO NOT CHANGE)

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
      "allocation": "percentage",
      "market_value": "dollar amount"
    }},
    ...
  ]
}}
```

Place the JSON output at the end of your response after your human-readable recommendation, clearly separated by "===JSON OUTPUT===".
"""

    # Add the research insights to the prompt
    content += "\n\n### RESEARCH INSIGHTS (USE THIS INFORMATION TO INFORM YOUR RECOMMENDATIONS):\n"
    
    # Add research results
    for area, analysis in state["research_results"].items():
        content += f"\n#### {area.upper()} ANALYSIS:\n"
        # Truncate if needed to keep the prompt size manageable
        summary = analysis
        content += f"{summary}\n"
    
    # Add free search results
    content += "\n#### TARGETED RESEARCH:\n"
    for i, search in enumerate(state["free_search_results"]):
        content += f"\nRESEARCH QUERY {i+1}: {search['query']}\n"
        summary = search['result']
        content += f"{summary}\n"
    
    # Add database schema information
    if "database_schemas" in state:
        # Extract some key information about available tickers by sector
        content += "\n#### INVESTMENT UNIVERSE (AVAILABLE TICKERS BY SECTOR):\n"
        schemas = state["database_schemas"]
        
        for sector_key, sector_data in schemas.items():
            sector_name = sector_key.replace("equity_sector_", "").replace("_", " ").title()
            content += f"\n##### {sector_name}:\n"
            
            # List a sample of industries and tickers for each sector
            for i, (schema_name, schema_data) in enumerate(sector_data.get("schemas", {}).items()):
                if i < 5:  # Limit to first 5 industries to keep prompt size manageable
                    industry_name = schema_name.replace("_", " ").title()
                    content += f"- {industry_name}: "
                    
                    # Sample tickers from this industry
                    tickers = []
                    for table in schema_data.get("tables", {}).values():
                        tickers.extend(table.get("tickers", [])[:5])  # Just take first 5 tickers
                    
                    if tickers:
                        content += f"{', '.join(tickers[:10])}\n"
                    else:
                        content += "No tickers available\n"
            
            # Indicate if more industries exist
            if len(sector_data.get("schemas", {})) > 5:
                content += f"- Plus {len(sector_data.get('schemas', {})) - 5} more industries...\n"
    
    # System prompt for the portfolio optimization
    system_prompt = """You are an elite portfolio manager with exceptional skills in building sophisticated 
    investment strategies based on thorough market research. You provide precise, specific recommendations 
    with clear justifications. Your recommendations are tailored to the client's current portfolio and 
    market conditions, following all provided rules and guidelines exactly."""
    
    # Generate the recommendation
    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
        )
        
        recommendation = response.choices[0].message.content
        state["final_recommendation"] = recommendation
        
        # Extract JSON part from the recommendation if it exists
        json_data = None
        if "===JSON OUTPUT===" in recommendation:
            parts = recommendation.split("===JSON OUTPUT===")
            if len(parts) > 1:
                json_text = parts[1].strip()
                # Try to extract JSON if it's wrapped in markdown code blocks
                if json_text.startswith("```json") and json_text.endswith("```"):
                    json_text = json_text[7:-3].strip()
                elif json_text.startswith("```") and json_text.endswith("```"):
                    json_text = json_text[3:-3].strip()
                
                try:
                    json_data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from recommendation: {e}")
        
        # If we have JSON data, save it to a file
        # if json_data:
        #     # Generate timestamp for the filename
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #     filename = f"portfolio_recommendation_{timestamp}.json"
            
        #     # Save to file
        #     with open(filename, 'w') as f:
        #         json.dump(json_data, f, indent=2)
                
        #     print(f"Saved trade actions and portfolio data to {filename}")
            
        #     # Print a summary of the trades
        #     trade_actions = json_data.get("trade_actions", [])
        #     print("\n=== Trade Actions Summary ===")
        #     for action in trade_actions:
        #         print(f"• {action.get('action_type', 'ACTION')} {action.get('ticker', 'TICKER')} ({action.get('quantity', 'QUANTITY')})")
        
    except Exception as e:
        print(f"Error generating portfolio recommendation: {e}")
        state["final_recommendation"] = f"Error generating recommendation: {str(e)}"
    
    return state

def optimize():
    """Main function to run the portfolio optimization process using LangGraph"""
    # Increase Python's recursion limit to avoid RecursionError
    import sys
    sys.setrecursionlimit(10000)  # Default is usually 1000
    
    # Define the workflow
    workflow = StateGraph(PortfolioState)
    
    # Add nodes for initialization and phase routing
    workflow.add_node("initialize", initialize_state)
    workflow.add_node("route_based_on_phase", route_based_on_phase)
    workflow.add_node("route_to_specific_tool", route_to_specific_tool)
    
    # Add nodes for all analyst tools
    workflow.add_node("communication_services_analysis", run_communication_services_analysis)
    workflow.add_node("consumer_staples_analysis", run_consumer_staples_analysis)
    workflow.add_node("consumer_discretionary_analysis", run_consumer_discretionary_analysis)
    workflow.add_node("energy_analysis", run_energy_analysis)
    workflow.add_node("financials_analysis", run_financials_analysis)
    workflow.add_node("healthcare_analysis", run_healthcare_analysis)
    workflow.add_node("industrials_analysis", run_industrials_analysis)
    workflow.add_node("information_technology_analysis", run_information_technology_analysis)
    workflow.add_node("materials_analysis", run_materials_analysis)
    workflow.add_node("real_estate_analysis", run_real_estate_analysis)
    workflow.add_node("utilities_analysis", run_utilities_analysis)
    workflow.add_node("treasuries_analysis", run_treasuries_analysis)
    workflow.add_node("ig_credit_analysis", run_ig_credit_analysis)
    workflow.add_node("high_yield_analysis", run_high_yield_analysis)
    workflow.add_node("foreign_exchange_analysis", run_foreign_exchange_analysis)
    workflow.add_node("emerging_market_analysis", run_emerging_market_analysis)
    workflow.add_node("commodities_analysis", run_commodities_analysis)
    workflow.add_node("etf_analysis", run_etf_analysis)
    workflow.add_node("database_schema_analysis", run_database_schema_analysis)
    
    # Add nodes for free research and recommendation generation
    workflow.add_node("free_research", run_free_research)
    workflow.add_node("generate_recommendation", generate_portfolio_recommendation)
    
    # Add edges for the flow
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "route_based_on_phase")
    
    # Route based on current phase
    workflow.add_conditional_edges(
        "route_based_on_phase",
        lambda state: state["current_phase"],  # Extract the phase from state
        {
            "required_analysis": "route_to_specific_tool",
            "targeted_research": "free_research",
            "final_recommendation": "generate_recommendation"
        }
    )
    
    # Route to specific required tool
    workflow.add_conditional_edges(
        "route_to_specific_tool",
        lambda state: state["required_tools_order"][state["next_required_tool_index"]] 
                    if state["next_required_tool_index"] < len(state["required_tools_order"]) 
                    else "free_research",  # Extract the tool name from state
        {
            "communication_services_analyst": "communication_services_analysis",
            "consumer_staples_analyst": "consumer_staples_analysis",
            "consumer_discretionary_analyst": "consumer_discretionary_analysis",
            "energy_analyst": "energy_analysis",
            "financials_analyst": "financials_analysis",
            "healthcare_analyst": "healthcare_analysis",
            "industrials_analyst": "industrials_analysis",
            "information_technology_analyst": "information_technology_analysis",
            "materials_analyst": "materials_analysis", 
            "real_estate_analyst": "real_estate_analysis",
            "utilities_analyst": "utilities_analysis",
            "treasuries_analyst": "treasuries_analysis",
            "ig_credit_analyst": "ig_credit_analysis",
            "high_yield_analyst": "high_yield_analysis",
            "foreign_exchange_analyst": "foreign_exchange_analysis",
            "emerging_market_analyst": "emerging_market_analysis",
            "commodities_analyst": "commodities_analysis",
            "etf_analyst": "etf_analysis",
            "database_schema_reader": "database_schema_analysis",
            "free_research": "free_research"
        }
    )
    
    # After any required tool or free research, go back to the phase router
    for node_name in [
        "communication_services_analysis", "consumer_staples_analysis", "consumer_discretionary_analysis",
        "energy_analysis", "financials_analysis", "healthcare_analysis", "industrials_analysis",
        "information_technology_analysis", "materials_analysis", "real_estate_analysis", "utilities_analysis",
        "treasuries_analysis", "ig_credit_analysis", "high_yield_analysis", "foreign_exchange_analysis",
        "emerging_market_analysis", "commodities_analysis", "etf_analysis", "database_schema_analysis", "free_research"
    ]:
        workflow.add_edge(node_name, "route_based_on_phase")
    
    # Final recommendation generation
    workflow.add_edge("generate_recommendation", END)
    
    # Compile the workflow
    chain = workflow.compile()
    
    # Run the workflow and time it
    start_time = time.time()
    print("Starting portfolio optimization workflow...")
    
    try:
        # Pass config dictionary with recursion_limit to invoke
        # Config with recursion_limit must be at the top level, not inside configurable
        result = chain.invoke({}, {"recursion_limit": 100})
        end_time = time.time()
        
        print(f"\nPortfolio optimization completed in {end_time - start_time:.2f} seconds")
        
        # Print the final recommendation
        if result.get("final_recommendation"):
            print("\n=== Final Portfolio Recommendation ===")
            print(result["final_recommendation"])
        
        return result.get("final_recommendation", "No recommendation generated")
        
    except Exception as e:
        print(f"Error in portfolio optimization workflow: {e}")
        import traceback
        traceback.print_exc()
        return f"An error occurred during portfolio optimization: {str(e)}"

if __name__ == "__main__":
    recommendation = optimize()
    print(recommendation)