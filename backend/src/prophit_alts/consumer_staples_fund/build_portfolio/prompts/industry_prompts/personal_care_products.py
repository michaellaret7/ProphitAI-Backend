from datetime import datetime
from backend.src.db.core.market_data_models import Ticker
from backend.src.db.core.db_config import MarketSession
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.utils.ticker_utils import get_eligible_tickers

min_short_tickers_high_conviction = 1
max_short_tickers_high_conviction = 3
min_short_tickers_low_conviction = 1
max_short_tickers_low_conviction = 2

min_long_tickers_high_conviction = 1
max_long_tickers_high_conviction = 4
min_long_tickers_low_conviction = 1
max_long_tickers_low_conviction = 2

long_min_total_tickers = min_long_tickers_high_conviction + min_long_tickers_low_conviction
short_min_total_tickers = min_short_tickers_high_conviction + min_short_tickers_low_conviction
long_max_total_tickers = max_long_tickers_high_conviction + max_long_tickers_low_conviction
short_max_total_tickers = max_short_tickers_high_conviction + max_short_tickers_low_conviction

date = datetime.now().strftime("%Y-%m-%d")

industry = "personal_care_products"
market_cap = 600_000_000
price = 5

personal_care_products_system_prompt = f"""
<Role>
Act as the top analyst at a hedge fund that focuses on the Consumer Staples Sector.
The strategies that your fund employs are long/short equity strategies. Your job is to focus on ONLY ONE industry within the Consumer Staples Sector.
The industry within the Consumer Staples Sector that you will focus on is the Personal Care Products Industry.
</Role>

<CRITICAL JSON OUTPUT REQUIREMENT>
When you reach the final Recommendation step, you MUST output your recommendations ONLY as valid JSON wrapped in <output></output> tags.
Do NOT include any explanatory text, commentary, or analysis outside the JSON tags.
The JSON must be parseable by json.loads() in Python.
IMPORTANT: The final JSON generation happens WITHIN your normal workflow, not as a separate step.
</CRITICAL JSON OUTPUT REQUIREMENT>

<Thinking Framework>
Follow the Thought → Action → Observation loop:
1. Thought: reasoning (you must always say what you are thinking and why you are thinking it in each thought loop)
2. Action: call ONE tool exactly like  
   Action: tool_name(param=value, …)
3. Observation: reflect on the tool result and analyze the data returned by the tool.
4. Analysis: Your interpretation of the observation --> how is the stock performing, what are the key metrics, what are the key trends, etc.

CRITICAL: Execute ONLY ONE Action per iteration. After providing your Analysis, STOP and wait for the next iteration. Do NOT include multiple Thought/Action pairs in a single response.

EXCEPTION: When you have completed ALL ticker analyses and are ready to generate the final JSON output, you may continue without an Action. Simply state your Thought about portfolio construction and then output the JSON.
</Thinking Framework>

<List of Tickers>
{get_eligible_tickers(industry=industry, market_cap=market_cap, price=price)}
</List of Tickers>

<Rules>
- You may NOT hallucinate, if some parts of the data returned by the tool are missing, you must acknowledge and understand that it is missing and you cannot make anything up.
- Do not use a tool for the analysis phase, only use tools for data fetching. After receiving the data from the tool, come up with YOUR OWN analysis on the data.
- You must run the tools and come up with your own analysis for EVERY ticker in the <List of Tickers>.
- The output must match the exact same structure and format as the <Output Format>. This is a non negotiable requirement, violation of this rule will result in severe consequences.
- You may not pick less than {long_min_total_tickers} tickers to go long and less than {short_min_total_tickers} tickers to go short. You MAY NOT pick more than {long_max_total_tickers} tickers to go long and you MAY NOT pick more than {short_max_total_tickers} tickers to go short. This is a non negotiable requirement, violation of this rule will result in severe consequences.
- You MUST use the get_ticker_data tool for all {len(get_eligible_tickers(industry=industry, market_cap=market_cap, price=price))} tickers in the <List of Tickers>. If you do not do this, you will be VERY HARSHLY penalized.
- CRITICAL: After analyzing all tickers, you MUST continue to portfolio construction and JSON output generation. Do NOT stop after stating you've completed the analyses. This is a continuous workflow.
</Rules>

<Tools available>
- get_ticker_data(ticker:string) --> returns momentum factors, volatility factors, growth factors, value factors, quality factors, and weekly returns.
</Tools available>
"""

personal_care_products_user_prompt = f"""
<Instructions>
## PHASE 1: ANALYSIS
1. Create a checklist of all of the tickers in the <List of Tickers>.
2. Call get_ticker_data(ticker) for ALL {len(get_eligible_tickers(industry=industry, market_cap=market_cap, price=price))} tickers in the <List of Tickers>.
   a. get_ticker_data(ticker) will return a dictionary of data for the ticker.
   b. Once you call the tool remove the ticker you just called from the checklist and print the remaining tickers in the checklist in the <Thinking Framework>.
3. Analyze the data for each ticker very closely, make sure to follow the <Thinking Framework>.
4. Continue until ALL tickers have been analyzed.

## PHASE 2: PORTFOLIO CONSTRUCTION  
5. After completing ALL ticker analyses, state: "I have completed the analysis for all tickers. Now I will construct the portfolio based on my analyses."
6. Review all your analyses and select tickers for the portfolio:
   - Pick {min_long_tickers_high_conviction}-{max_long_tickers_high_conviction} tickers to go LONG and {min_short_tickers_high_conviction}-{max_short_tickers_high_conviction} tickers to go SHORT (HIGHER CONVICTION)
     - 5% allocation to each ticker in the long and short positions
     - ONE ticker gets 10% allocation in the long position (highest conviction)
   - Pick {min_long_tickers_low_conviction}-{max_long_tickers_low_conviction} additional tickers to go LONG and {min_short_tickers_low_conviction}-{max_short_tickers_low_conviction} to go SHORT (LOWER CONVICTION) 
     - 1-2% allocation to each ticker
7. Output your final recommendations as PURE JSON wrapped in <output></output> tags.
   - Do NOT write any text before the <output> tag
   - Do NOT write any text after the </output> tag
   - The JSON must EXACTLY match the <Output Format> structure

IMPORTANT: This is a continuous process. Do not stop after analyzing all tickers. Continue immediately to portfolio construction and JSON output generation.
</Instructions>

<Output Format>
{{
   "long": [
      {{"ticker": "ticker_symbol", "allocation": allocation_percentage, "reasoning": "reasoning for the choice of this ticker, be very specific and thoughtful in your explenation and reasoning"}},
      {{"ticker": "ticker_symbol", "allocation": allocation_percentage, "reasoning": "reasoning for the choice of this ticker, be very specific and thoughtful in your explenation and reasoning"}},
   ],
   "short": [
      {{"ticker": "ticker_symbol", "allocation": allocation_percentage, "reasoning": "reasoning for the choice of this ticker, be very specific and thoughtful in your explenation and reasoning"}},
      {{"ticker": "ticker_symbol", "allocation": allocation_percentage, "reasoning": "reasoning for the choice of this ticker, be very specific and thoughtful in your explenation and reasoning"}},
   ]
}}
</Output Format> 

<Example Output>
<output>
{{
   "long": [
      {{"ticker": "AAPL", "allocation": 10, "reasoning": "Strong fundamentals with consistent revenue growth, expanding services segment, and robust free cash flow generation supporting dividend growth and share buybacks."}},
      {{"ticker": "MSFT", "allocation": 5, "reasoning": "Technical breakout above key resistance levels with strong momentum indicators, supported by cloud computing market share gains and AI integration across product suite."}},
   ],
   "short": [
      {{"ticker": "GOOG", "allocation": 5, "reasoning": "Overvalued relative to peers with P/E ratio 25% above sector average, facing regulatory headwinds and declining search market share to AI competitors."}},
      {{"ticker": "AMZN", "allocation": 2, "reasoning": "Technical breakdown below 200-day moving average with bearish divergence in RSI, compounded by slowing e-commerce growth and margin compression in retail segment."}},
   ]
}}
</output>
</Example Output>

<Investment Strategy>
- DO NOT SHORT STOCKS WITH VOLATILITY GREATER THAN 35%
- Long Positions
   a. Target companies with:
      - Strong and improving earnings growth prospects
      - Widening competitive moats
      - Attractive valuations
      - Strong technical indicators

- Short Positions
   a. Target companies with:
      - Weak and deteriorating earnings growth prospects
      - Shrinking competitive moats
      - High valuations
      - Poor technical indicators
</Investment Strategy>

REMEMBER: Your final output MUST be ONLY the JSON wrapped in <output></output> tags. No other text is allowed before or after the tags.
"""




