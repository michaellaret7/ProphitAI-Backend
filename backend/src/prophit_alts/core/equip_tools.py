from backend.src.prophit_alts.core.tools import ProphitAltsDataWrapper, AgentSearchEngine
from typing import List, Dict, Any

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_ticker_data",
        "description": "Get the daily total returns for a given ticker.",
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
        "description": "The free_search tool gives you the ability to search the web for information. You will create an indepth query that will be entered into the Perplexity search engine.",
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