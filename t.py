from app.repositories.transcripts_data import get_earnings_transcripts
from app.core.foundry.pipeline import Pipeline
from app.core.atlas.agents.chat_agent import ChatAgent
from app.core.atlas.agents.deep_agent import DeepAgent
from app.core.atlas.tools.foundry import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.tools.ticker.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL, get_ticker_performance_and_risk
from app.core.atlas.tools.data import GET_TICKER_FUNDAMENTAL_DATA_TOOL, get_fundamental_data
from app.core.atlas.models import PrintMode
from app.core.atlas.tools.base.search_engine import AgentSearchEngine, LLM_WEB_SEARCH_DESCRIPTION, LLM_WEB_SEARCH_PARAMETERS
from app.core.atlas.tools.foundry.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.deep.write_notes import write_note, WRITE_NOTE_DESCRIPTION, WRITE_NOTE_PARAMETERS
from app.core.atlas.tools.deep.retrieve_notes import retrieve_notes, RETRIEVE_NOTES_DESCRIPTION, RETRIEVE_NOTES_PARAMETERS

system_prompt = """
Your task is to do extensive research on a given company and provide a rating and an investment suggestion (BUY/HOLD/SELL).

You will use the following tools to do your research:
- get_ticker_fundamental_data: Get the fundamental data of the company
- get_ticker_performance_and_risk: Get the performance and risk of the company
- earnings_call_search: Search for earnings calls of the company
- llm_web_search: Search the web for information about the company
- macro_research_search: Search for macroeconomic data and news to get maximum market context

1. You should first run the macro_research_search tool to get the overall market context to set the backdrop for your research.
2. Youy should then pull the fundamental data of the company using and the performance and risk data.
3. Then run through the most recent earnings calls from the past few years (make sure to filter with the fiscal quarter arg) 
    a. Find any trends or insights from the earnings calls
    b. Find patterns within the company's earnings calls
    c. Find any other insights from the earnings calls
4. Extensively use the think tool to synthesize your findings and return a research piece on the stock.

Suggestion: Use the think tool as much as possible and write detailed notes on your findings.
"""
user_prompt = """
Review Intel Corporation (INTC) and provide a rating and research piece.

Important informatio: The date is January 29, 2026.
Most Recent Earnings Call: Q4 2025
"""

max_iterations = 50

deep_agent = DeepAgent(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    print_mode=PrintMode.VERBOSE,
    provider="grok",
    model="grok-4-1-fast-non-reasoning",
    max_iterations=150
)

deep_agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
deep_agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
deep_agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
deep_agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

result = deep_agent.run()
print(result)

# def upload_ticker_transcripts(ticker: str) -> int:
#     """
#     Upload all earnings transcripts for a ticker to Pinecone.

#     Args:
#         ticker: Stock ticker symbol (e.g., "AAPL")

#     Returns:
#         Number of vectors upserted
#     """
#     result = get_earnings_transcripts(ticker)
#     print(len(result["items"]))
#     transcripts = result["items"]

#     if not transcripts:
#         print(f"No transcripts found for {ticker}")
#         return 0

#     texts = [
#         {
#             "content": t["content"],
#             "metadata": {
#                 "ticker": ticker.upper(),
#                 "period": t["period"],
#                 "year": t["year"],
#                 "date": t["date"],
#             },
#         }
#         for t in transcripts
#     ]

#     pipeline = Pipeline(
#         namespace="earnings_calls",
#         doc_type="earnings_call",
#         chunker_type="earnings_call",
#     )

#     count = pipeline.run(texts=texts)
#     print(f"Uploaded {count} vectors for {ticker} from {len(transcripts)} transcripts")
#     return count





