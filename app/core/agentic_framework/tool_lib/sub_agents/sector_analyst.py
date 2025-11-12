from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from datetime import datetime
import yaml
import random

# Import tool definitions from tool_lib
from app.core.agentic_framework.tool_lib.data_tools.stock_screener.tool import STOCK_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.industry_factors import GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sub_industry_factors import GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sector_info import GET_SECTOR_TICKERS_TOOL, GET_SECTOR_INDUSTRIES_TOOL

class SectorAnalyst(SubAgent):
    def __init__(self, user_prompt: str):
        super().__init__(
            user_prompt=user_prompt,
            provider="anthropic",  
            model="claude-haiku-4-5-20251001",
            max_iterations=50,
            plan_first=True,
            temperature=0.7
        )

        tools = [
            GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL,
            GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL,
            STOCK_SCREENER_TOOL,
            GET_SECTOR_TICKERS_TOOL,
            GET_SECTOR_INDUSTRIES_TOOL
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )

def run_sector_analyst(
    task: str,
    *,
    _simulation_date: datetime | None = None
) -> str:
    """
    Run the SectorAnalyst sub-agent on a narrowly scoped sector/industry task.
    Returns a YAML string with final answer and run metadata.
    """
    try:
        agent = SectorAnalyst(user_prompt=task)
        agent.simulation_date = _simulation_date
        result = agent.run()
        return yaml.dump({"success": True, "data": result}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

# Tool schema for invoking the SectorAnalyst as a tool
RUN_SECTOR_ANALYST_DESCRIPTION = (
    "Delegate a narrowly-scoped sector/industry analysis task to a specialized sub-agent. "
    "This sub-agent is optimized for fast, rigorous execution with micro-planning (2-5 steps). "
    "\n\n"
    "PROMPT CONSTRUCTION GUIDELINES:\n"
    "1. SPECIFICITY: Define a single, concrete objective (not multiple goals)\n"
    "   - Good: 'Compare the 3M drawdown in Semiconductors vs SPY and identify key drivers'\n"
    "   - Bad: 'Analyze semiconductors and provide investment recommendations'\n"
    "\n"
    "2. CONTEXT: Include essential parameters (time periods, benchmarks, specific metrics)\n"
    "   - Good: 'Calculate Technology sector beta vs SPY over the last 6 months'\n"
    "   - Bad: 'Tell me about tech sector performance'\n"
    "\n"
    "3. SCOPE: Focus on diagnostic/analytical tasks, not broad research\n"
    "   - Good: 'Identify top 5 underperforming stocks in Consumer Staples vs sector benchmark'\n"
    "   - Bad: 'Research everything about consumer staples'\n"
    "\n"
    "4. OUTPUT: Specify the desired format if critical\n"
    "   - Good: 'List top 3 growth stocks in Healthcare with their 1Y momentum scores'\n"
    "   - Bad: 'Give me some healthcare stocks'\n"
    "\n"
    "The sub-agent has access to: industry/sub-industry benchmarks, stock screeners, and sector fundamentals. "
    "Keep prompts concise but informative—clarity beats verbosity."
)

RUN_SECTOR_ANALYST_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": (
                "A clear, single-objective task prompt for the sector analyst. "
                "Must be specific and narrowly scoped with explicit parameters (time periods, metrics, benchmarks). "
                "Example: 'Diagnose why Energy sector underperformed SPY by 15% in Q1 2024 using factor analysis'"
            )
        }
    },
    "required": ["task"],
    "additionalProperties": False
}

SECTOR_ANALYST_TOOL = {
    "name": "run_sector_analyst",
    "description": RUN_SECTOR_ANALYST_DESCRIPTION,
    "parameters": RUN_SECTOR_ANALYST_PARAMETERS,
    "function": run_sector_analyst,
}

if __name__ == "__main__":
    user_prompt = """
    You are a sector analyst specializing in the technology sector. Your task is to perform a comprehensive, high-level analysis of the current state of the technology sector, focusing on recent trends, risk factors, growth opportunities, and notable industry developments. 
    """
    result = run_sector_analyst(user_prompt)
    print(result)