from backend.src.prophit_alts.core.tools.data_wrapper_tool import ProphitAltsDataWrapper
from backend.src.prophit_alts.core.tools.search_engine_tool import AgentSearchEngine
from typing import List, Dict, Any

ticker_data_description = """
The get_ticker_data tool returns a comprehensive dictionary of financial data for a given stock ticker. 
This includes performance metrics like weekly returns and style factors (Momentum, Volatility, etc.), fundamental data such as financial statements and analyst estimates, 
recent news, earnings transcript summaries, and stock grades.
"""

search_description = """
The free_search tool gives you the ability to search the web for information. 
You will create an indepth query that will be entered into the Perplexity search engine.
"""

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_ticker_data",
        "description": ticker_data_description,
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "The stock ticker symbol to get price for."},
            },
            "required": ["ticker"]
        },
        "function": lambda ticker: ProphitAltsDataWrapper(ticker).run_all()
    },
    {
        "name": "free_search",
        "description": search_description,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The query to search the web for. This query should be indepth and detailed, the more detailed the better the results wil be."},
            },
            "required": ["query"]
        },
        "function": lambda query: AgentSearchEngine().perplexity_free_search(query)
    }
]

def register_tools(agent_instance):
    """
    Register all defined tools with the given StressTestAgent instance.
    
    Args:
        agent_instance: StressTestAgent instance to register tools with
    """
    for tool_config in TOOLS:
        agent_instance.add_tool(
            name=tool_config["name"],
            description=tool_config["description"],
            parameters=tool_config["parameters"],
            function=tool_config["function"]
        )