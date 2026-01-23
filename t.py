from app.core.agentic_framework.tool_lib.foundry_tools import (
    MACRO_RESEARCH_SEARCH_TOOL,
    EARNINGS_CALL_SEARCH_TOOL,
)
from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode


# agent = BaseAgent(
#     system_prompt="You are a helpful assistant that can search the Foundry knowledge base. Run many macro_research_searches as you go through the workflow. You are a RAG agent so the point it to do heavy research and analysis on the provided data from the macro_research_searches.",
#     user_prompt="What is the average sentiment of interest rates in the United States, what is the research saying about interest rates in the United States, and where do you think interest rates are going in the next 6 months? Your output should be a well formatted research piece with cited sources.",
#     model="Kimi-K2-instruct",
#     provider="fireworks",
#     max_iterations=50,
#     print_mode=PrintMode.VERBOSE,
# )
# agent.add_tool(
#     MACRO_RESEARCH_SEARCH_TOOL["name"],
#     MACRO_RESEARCH_SEARCH_TOOL["description"],
#     MACRO_RESEARCH_SEARCH_TOOL["parameters"],
#     MACRO_RESEARCH_SEARCH_TOOL["function"],
# )
# agent.run()

agent = BaseAgent(
    system_prompt="You are an analyst for Apple. You're goal is to read their earnings call from 2025Q4 and provide any insights, signals, and potential risks.",
    user_prompt="What are the key insights or signals from the earnings call? Your output should be a concise well formatted research piece with cited sources.",
    model="Qwen3-235B-instruct",
    provider="fireworks",
    max_iterations=50,
    print_mode=PrintMode.VERBOSE,
)
agent.add_tool(
    EARNINGS_CALL_SEARCH_TOOL["name"],
    EARNINGS_CALL_SEARCH_TOOL["description"],
    EARNINGS_CALL_SEARCH_TOOL["parameters"],
    EARNINGS_CALL_SEARCH_TOOL["function"],
)
agent.run()