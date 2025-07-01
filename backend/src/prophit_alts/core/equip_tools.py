from backend.src.prophit_alts.core.tools import ProphitAltsDataWrapper
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