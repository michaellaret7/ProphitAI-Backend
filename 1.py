from openai import OpenAI
import re

def search(system_prompt, user_prompt):
   API_KEY = "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"
   messages = [
      {
         "role": "system",
         "content": (
               system_prompt
         ),
      },
      {   
         "role": "user",
         "content": (
               user_prompt
         ),
      },
   ]

   client = OpenAI(api_key=API_KEY, base_url="https://api.perplexity.ai")

   # chat completion without streaming
   response = client.chat.completions.create(
      model="sonar-deep-research",
      messages=messages,
      stream=True
   )

   # Store full response in a variable
   # full_response = response.choices[0].message.content
   # print("Complete response:")
   # print(full_response)

   # Collect the streaming content
   collected_chunks = []
   collected_content = ""
   # Process each chunk
   print("\nStreaming response:")
   for chunk in response:
      collected_chunks.append(chunk)  # Store the raw chunk
      content = chunk.choices[0].delta.content or ""
      collected_content += content  # Concatenate the content
      # Print each new piece as it arrives
      print(content, end="", flush=True)

   # Now collected_content has the full response text
   print("\n\nFull collected response:")

   # Remove the thinking process using regex
   cleaned_content = re.sub(r'<think>.*?</think>', '', collected_content, flags=re.DOTALL)
   print("Cleaned content:")
   print("=" * 100)
   print(cleaned_content)

   return cleaned_content  



fixed_income_system_prompt = """
You are a professional financial analyst specializing in fixed income markets. Provide comprehensive, data-driven analysis of the bond market with the following characteristics:
1. Use reliable financial sources including Federal Reserve data, Treasury reports, financial news, market indices, and expert commentary
2. Include relevant quantitative data such as yields, spreads, trading volumes, and price movements
3. Analyze market trends across different bond categories (Treasury, corporate, municipal, high-yield)
4. Explain technical concepts clearly but maintain sophisticated financial analysis
5. Discuss monetary policy implications and macroeconomic factors affecting bond markets
6. Structure your response with clear sections covering different timeframes and market segments
7. Include diverse perspectives on market outlook from leading institutions
"""

fixed_income_user_prompt = """
Conduct a detailed analysis of the current state of the bond market with specific focus on:

1. RECENT DEVELOPMENTS (PAST WEEK):
   - Major price movements and yield changes in Treasury bonds, corporate bonds, and municipal bonds
   - Significant trading activity or market disruptions
   - Key announcements that impacted fixed income markets
   - Changes in the yield curve and what they indicate

2. MONTH-LONG TRENDS (PAST 30 DAYS):
   - Performance of major bond indexes and ETFs
   - Credit spread evolution between investment grade and high-yield bonds
   - Shifts in investor sentiment and capital flows
   - Corporate bond issuance activity and notable deals
   - Changes in international bond markets and their influence on US markets

3. QUARTERLY PERSPECTIVE (PAST 3 MONTHS):
   - Monetary policy developments and Federal Reserve actions/communications
   - Inflation data impact on fixed income investments
   - Structural changes in market dynamics or regulations
   - Performance comparison across different bond sectors and maturities
   - Institutional investor positioning and strategy shifts

4. OUTLOOK AND STRATEGIC CONSIDERATIONS:
   - Key factors to watch in the coming weeks
        - Upside catalysts
        - Downside risks
   - Potential risks and opportunities in different bond market segments
   - Expert consensus on interest rate trajectory

Please include specific data points, charts when relevant, and cite your sources. Prioritize accuracy and depth of analysis over general commentary.
"""


# Equity Market Research Prompts
equity_system_prompt = """
You are a professional financial analyst specializing in equity markets. Provide comprehensive, data-driven analysis of the stock market with the following characteristics:
1. Use reliable financial sources including market data providers, SEC filings, earnings reports, analyst research, and expert commentary
2. Include relevant quantitative data such as index levels, trading volumes, market breadth, sector performance, and valuation metrics
3. Analyze market trends across different market caps, sectors, investment styles, and geographic regions
4. Explain technical concepts clearly but maintain sophisticated financial analysis
5. Discuss macroeconomic factors affecting equity markets including monetary policy, inflation, employment, and economic growth
6. Structure your response with clear sections covering different timeframes and market segments
7. Include diverse perspectives on market outlook from leading institutions and strategists
"""

equity_user_prompt = """
Conduct a detailed analysis of the current state of the equity market with specific focus on:

1. RECENT DEVELOPMENTS (PAST WEEK):
   - Major price movements and trading patterns in major indices (S&P 500, Nasdaq, Dow Jones, Russell 2000)
   - Sector rotation and leadership changes
   - Key earnings reports, economic data releases, or news that impacted markets
   - Notable changes in market sentiment indicators (VIX, put/call ratios, sentiment surveys)

2. MONTH-LONG TRENDS (PAST 30 DAYS):
   - Performance comparison across sectors, market caps, and investment styles (growth vs. value)
   - Fund flows into different market segments and ETFs
   - Changes in market breadth and participation
   - Shifts in institutional positioning and retail investor activity
   - International market performance and correlation with US markets

3. QUARTERLY PERSPECTIVE (PAST 3 MONTHS):
   - Earnings season results and guidance trends
   - Valuation changes and comparison to historical averages
   - Monetary policy impacts on equity markets
   - Market technical indicators and their signals
   - Significant corporate actions (M&A, buybacks, dividends)
   - Performance of thematic and factor-based investments

4. OUTLOOK AND STRATEGIC CONSIDERATIONS:
   - Key catalysts and risk factors for the equity market in coming weeks
   - Sector and industry opportunities
   - Consensus earnings expectations and their implications
   - Technical levels to watch across major indices

Please include specific data points, charts when relevant, and cite your sources. Prioritize accuracy and depth of analysis over general commentary.
"""

# Commodity Market Research Prompts
commodity_system_prompt = """
You are a professional financial analyst specializing in commodity markets. Provide comprehensive, data-driven analysis of the commodity market with the following characteristics:
1. Use reliable financial sources including commodity exchanges, government reports, industry publications, and expert commentary
2. Include relevant quantitative data such as price movements, trading volumes, inventory levels, and futures curves
3. Analyze market trends across different commodity categories (energy, precious metals, industrial metals, agriculture)
4. Explain technical concepts clearly but maintain sophisticated market analysis
5. Discuss supply/demand dynamics, geopolitical factors, and macroeconomic influences on commodity markets
6. Structure your response with clear sections covering different timeframes and commodity segments
7. Include diverse perspectives on market outlook from leading commodity research institutions
"""

commodity_user_prompt = """
Conduct a detailed analysis of the current state of the commodity market with specific focus on:

1. RECENT DEVELOPMENTS (PAST WEEK):
   - Major price movements across key commodities (oil, natural gas, gold, copper, agricultural products)
   - Significant supply disruptions or demand shocks
   - Key announcements or data releases that impacted commodity markets
   - Changes in futures curves and what they indicate
   - Notable geopolitical events affecting commodity pricing

2. MONTH-LONG TRENDS (PAST 30 DAYS):
   - Performance comparison across different commodity sectors
   - Changes in inventory levels and storage trends
   - Shifts in positioning by speculative vs. commercial traders
   - Production and export/import data from major markets
   - Currency movements and their impact on commodity prices
   - Physical market premiums/discounts and their evolution

3. QUARTERLY PERSPECTIVE (PAST 3 MONTHS):
   - Seasonal factors affecting various commodity markets
   - Changes in production capacity and infrastructure
   - Regulatory developments impacting commodity trading or production
   - Performance of commodity indices and ETFs
   - Correlation with other asset classes (equities, bonds, currencies)
   - Long-term supply/demand balance shifts

4. OUTLOOK AND STRATEGIC CONSIDERATIONS:
   - Key drivers to watch for each major commodity sector
   - Potential supply constraints or demand catalysts
   - Price forecasts from major institutions
   - Upcoming events that could impact commodity markets
   - Backwardation/contango structures and their implications

Please include specific data points, charts when relevant, and cite your sources. Prioritize accuracy and depth of analysis over general commentary.
"""

