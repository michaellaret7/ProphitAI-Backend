"""
Author: @Michael Laret
=====================================================================
This file contains the functions for the macro research analysts.
It is used to get the research reports for the different sectors.
Perplexity is used to get the research reports.
"""


import json
from openai import OpenAI
import numpy as np
import os
from datetime import datetime
import psycopg2
import pandas as pd
import re
import time 
import random
import itertools
import threading
import math
import curses
from dotenv import load_dotenv
from src.phaseOne.phaseOneAnimation import start_animation, Colors
from src.utils.file_utils import load_schema_data

# Load environment variables from .env file
load_dotenv()

Sonar_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
perplexity_model = 'sonar-deep-research'

def commodities_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    # Define custom analysis steps for commodities research
    commodities_steps = [
        "Analyzing supply and demand fundamentals",
        "Evaluating weather impact on agricultural markets",
        "Examining inventory levels across commodities",
        "Calculating futures curve contango/backwardation",
        "Processing geopolitical risk factors",
        "Analyzing currency impacts on commodity prices",
        "Assessing industrial demand metrics",
        "Evaluating energy sector correlations",
        "Processing seasonal consumption patterns",
        "Examining production capacity constraints",
        "Calculating cross-commodity correlations",
        "Analyzing global trade flow disruptions",
        "Evaluating commodity ETF fund flows",
        "Processing inflation impacts on raw materials",
        "Examining speculative positioning data"
    ]
    
    # Start animation before API setup
    animation = start_animation(commodities_steps, "Commodities Market Analysis")

    system_prompt = """
    You are an expert commodities analyst with deep knowledge of global markets. You prioritize clarity, detail, and data-backed reasoning in your explanations. Always ground your conclusions in the provided context. If needed information is absent, acknowledge the gap rather than guessing.
    """

    user_prompt = f"""
    GOAL / OBJECTIVE:
    Provide a structured, data-driven analysis of how commodities are influenced by fundamental supply and demand factors, weather events, economic indicators, geopolitical risks, currency movements, policy changes, and technological shifts.

    IMPORTANT:
    THIS IS THE DATE TODAY: {date}
    
    USER MESSAGE (PROMPT):
    Please read the following reference on commodity market drivers and produce a well-organized, multi-paragraph report that covers:
    1. An overview of the key categories affecting commodities (supply/demand fundamentals, weather impacts, economic data, geopolitical risks, currency/financial factors, policy/regulatory influences, and technological trends).
    2. How these factors interact and reinforce or offset each other across different commodity classes (energy, metals, agriculture, etc.).
    3. Real or hypothetical scenarios illustrating potential market responses (e.g., how a strong dollar might affect oil prices, or how a drought impacts grain supplies).
    4. A brief forward-looking perspective on which factors appear most significant for the near-term commodity outlook.

    CONTEXT (REFERENCE MATERIAL):
    ----------------------------------------------------------------
    Commodities are influenced by a complex mix of fundamental supply and demand dynamics, weather
    conditions, economic data, geopolitical events, and policy decisions. The importance of each factor
    depends on the specific commodity (e.g., oil, natural gas, agricultural products, metals). Below is a
    breakdown of the most critical drivers:

    1. Supply and Demand Fundamentals
        • Production Levels - Changes in mining, drilling, or agricultural output affect supply.
        • Global Consumption Trends - Industrial activity, energy demand, and consumer behavior impact prices.
        • Inventory Levels (EIA, DOE, USDA, LME, COMEX Reports) - Storage and stockpile levels provide insight into current supply/demand balances.

    2. Weather and Natural Events
        • Agricultural Commodities (Corn, Wheat, Soybeans, Coffee, Cocoa, Sugar)
            --> Droughts, floods, frosts, and hurricanes can drastically impact crop yields.
            --> El Niño and La Niña influence rainfall and temperatures globally.
            --> Disease outbreaks (e.g., African Swine Fever affecting soybean demand in China).
        • Energy Markets (Oil, Natural Gas, Coal)
            --> Hurricanes affecting Gulf of Mexico oil and gas production.
            --> Cold winters increase natural gas demand (heating), while hot summers boost electricity use.
            --> Water shortages can impact hydropower generation and mining.
        • Metals & Mining
            --> Natural disasters or labor strikes can shut down mines (copper, iron ore, gold, etc.).
            --> Geological constraints impact long-term supply.

    3. Economic Data & Growth Indicators
        • GDP Growth (China, U.S., EU) - Higher economic activity increases demand for industrial metals, energy, and agricultural commodities.
        • Manufacturing and Industrial Production (PMIs, ISM, Durable Goods Orders) - A strong manufacturing sector signals increased raw material consumption.
        • Employment & Consumer Spending - Affects fuel demand (gasoline, diesel) and consumption of food/agriculture commodities.

    4. Geopolitical & Supply Chain Risks
        • OPEC+ Decisions (Oil) - Production quotas set by OPEC+ impact crude oil supply and prices.
        • Sanctions and Trade Restrictions - U.S. sanctions on Russian oil, metals, or agricultural products shift trade flows.
        • Tariffs and Trade Wars - U.S.-China trade tensions affecting soybean exports/imports.
        • Shipping & Logistics Disruptions
            - Red Sea/Suez Canal disruptions impacting energy and metals.
            - Panama Canal drought slowing commodity shipments.
            - Port strikes and supply chain bottlenecks.

    5. Currency & Financial Market Movements
        • U.S. Dollar Strength - Since most commodities are priced in USD, a stronger dollar makes them more expensive for foreign buyers.
        • Interest Rates & Inflation - Higher rates increase the cost of holding non-yielding assets like gold, while inflationary pressures often support commodity prices.
        • Speculative Positioning (COT Reports, Hedge Fund Flows) - Large spec positions in futures markets drive volatility.

    6. Policy & Regulation
        • Environmental Regulations (Carbon Taxes, Emissions Caps) - Restrictions on fossil fuel emissions impact coal, oil, and natural gas demand.
        • Biofuel Mandates (Ethanol, Biodiesel) - Policies requiring biofuel blending affect corn and soybean demand.
        • Mining & Drilling Restrictions - ESG-driven constraints on mining (lithium, cobalt) and fossil fuel production.
        • Government Stockpiling & Strategic Reserves (SPR Releases, China's Grain Reserves) - Governments manage strategic commodity reserves, impacting market balance.

    7. Alternative Energy & Technological Shifts
        • EV and Battery Metals Demand (Lithium, Cobalt, Nickel, Copper) - Growth in electric vehicle adoption increases demand for critical minerals.
        • Green Energy Transition (Solar, Wind, Hydrogen) - Shifts in energy consumption patterns impact fossil fuel demand.
        • AI & Semiconductor Boom (Rare Earths, Silver, Copper) - Increased tech sector demand drives specific commodity markets.

    8. War, Conflict & Cybersecurity Risks
        • Russia-Ukraine War (Wheat, Corn, Oil, Natural Gas, Palladium) - Major disruptions in global grain and energy markets.
        • Middle East Tensions (Oil, Gold, Safe Haven Demand) - Conflicts in the region can lead to oil price spikes.
        • Cyberattacks on Infrastructure (Pipelines, Power Grids) - Potential for disruptions to oil, gas, and power markets.
    ----------------------------------------------------------------

    INSTRUCTIONS:
    1. Provide an in depth overview of the main categories driving commodity markets.
    2. Summarize how these factors intersect (e.g., how weather events affect supply, how currency movements alter global trade flows, etc.).
    3. Give at least one example scenario (hypothetical or based on known patterns) illustrating how a particular driver might affect prices.
    4. Offer a forward-looking perspective on which factors are likely to be especially influential in the near term.
    5. Organize your response clearly, with headings or bullet points where appropriate.
    6. If any detail is missing from the context, note that explicitly rather than fabricating information.

    IMPORTANT
    - Use clear headings, subheadings, and bullet points to ensure readability and structure.
    - Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
    - Do not guess anything, if there is no data just say there is no data or do further research to find the data.

    END OF PROMPT
    """

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

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def etf_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    etf_steps = [
        "Analyzing ETF market conditions",
        "Evaluating ETF performance metrics",
        "Examining ETF tracking efficiency",
        "Processing ETF factor analysis",
        "Analyzing ETF sector performance",
        "Evaluating ETF portfolio construction techniques", 
        "Processing ETF total cost analysis",
        "Examining ETF market conditions",
        "Evaluating ETF liquidity profiles",
        "Analyzing ETF asset flows",
        "Examining ETF tracking efficiency",
        "Processing ETF factor analysis",
        "Analyzing ETF sector performance",
        "Evaluating ETF risk metrics",
        "Examining ETF tax efficiency",
        "Processing ETF yield analysis",
        "Analyzing ETF momentum signals",
        "Evaluating ETF volatility patterns",
        "Examining ETF correlation matrices",
        "Processing ETF rebalancing data"
    ]

    animation = start_animation(etf_steps, "ETF Market Analysis")

    system_prompt = """
You are an ETF analyst tool designed to provide a comprehensive, data-driven analysis of Exchange-Traded Funds (ETFs) for a portfolio optimizer with agentic AI. Your role is to evaluate how various factors—such as underlying asset performance, market trends, economic indicators, geopolitical events, regulatory changes, technological advancements, currency movements, and fund-specific attributes—affect ETF performance, risks, and opportunities.

Your task is to generate a detailed, multi-paragraph report that includes:
1. **Overview of Key Drivers**: Analyze the primary categories influencing ETFs, using specific examples to illustrate their impact.
2. **Interactions Between Factors**: Explore how these drivers interact to amplify or mitigate effects on different ETF types.
3. **Real and Hypothetical Scenarios**: Provide at least two detailed scenarios showing how specific factors could influence ETF performance.
4. **Forward-Looking Perspective**: Offer a concise outlook on the most significant factors likely to shape ETF performance over the next 3-12 months, based on general market principles or hypothetical trends.

**Important Instructions**:
- Base your analysis on general market dynamics 
- Maintain a professional, analytical tone throughout the report.
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.

Your output should be thorough, actionable, and tailored to support portfolio optimization decisions.
"""

    user_prompt = f"""
GOAL / OBJECTIVE:
Generate a detailed, structured, and data-informed analysis of Exchange-Traded Funds (ETFs) to support a portfolio optimizer with agentic AI. The analysis should evaluate how various factors—such as underlying asset performance, market trends, economic indicators, geopolitical events, regulatory shifts, technological advancements, currency fluctuations, and fund-specific attributes—drive ETF performance, risks, and opportunities. The output should enable actionable insights for portfolio optimization, including risk assessment, return potential, and strategic allocation decisions.

IMPORTANT:
THIS IS THE DATE TODAY: {date}

USER MESSAGE (PROMPT):
Produce a comprehensive, multi-paragraph report analyzing the factors influencing ETF performance. The report should include the following sections:
1. **Detailed Overview of Key Drivers:**
   - Analyze the primary categories affecting ETFs, including:
     - Underlying assets (e.g., equities, bonds, commodities, currencies)
     - Market trends (e.g., bull/bear markets, sector rotations, investor risk appetite)
     - Economic indicators (e.g., GDP growth, inflation rates, interest rates, unemployment)
     - Geopolitical events (e.g., conflicts, trade policies, political transitions)
     - Regulatory changes (e.g., financial oversight laws, tax reforms, sector-specific regulations)
     - Technological advancements (e.g., innovations in tech, healthcare, renewable energy)
     - Currency movements (e.g., exchange rate volatility impacting international ETFs)
     - Fund-specific factors (e.g., expense ratios, liquidity levels, tracking accuracy, yield distributions)
   - Provide specific examples for each category to illustrate their impact.
2. **Interactions Between Factors:**
   - Explore how these drivers interact to amplify or mitigate effects on different ETF types (e.g., equity ETFs, bond ETFs, commodity ETFs, currency ETFs).
   - Highlight reinforcing and offsetting dynamics with concrete examples.
3. **Real and Hypothetical Scenarios:**
   - Present at least two detailed scenarios (real-world or hypothetical) showing how specific factors could influence ETF performance.
   - Include potential market responses, risks, and opportunities.
4. **Forward-Looking Perspective:**
   - Offer a concise outlook on the most significant factors likely to shape ETF performance over the next 3-12 months, based on current trends or general market principles.
   - Support the outlook with logical reasoning.

CONTEXT (REFERENCE MATERIAL):
----------------------------------------------------------------
ETFs are publicly traded investment vehicles that track baskets of assets such as stocks, bonds, commodities, or currencies. Their performance hinges on a dynamic interplay of external and internal factors, which differ based on the ETF's focus (e.g., equity, fixed income, sector-specific, global). Below is a detailed framework of the key drivers:

1. **Underlying Assets**
   - **Equity ETFs**: Influenced by corporate earnings, stock valuations, and sector performance (e.g., technology growth driven by AI innovations impacting QQQ).
   - **Fixed Income ETFs**: Sensitive to interest rate changes, credit spreads, and bond yields (e.g., TLT affected by Federal Reserve policy shifts).
   - **Commodity ETFs**: Tied to supply/demand cycles, weather events, or production shocks (e.g., GLD rising with gold prices during economic uncertainty).
   - **Currency ETFs**: Driven by exchange rate movements and central bank actions (e.g., UUP gaining as the U.S. dollar strengthens).

2. **Market Trends**
   - Conditions like bull markets (rising asset prices), bear markets (declining prices), sector rotations (e.g., shift from tech to utilities), and investor sentiment (e.g., risk-on favoring growth ETFs like ARKK).

3. **Economic Indicators**
   - Metrics such as GDP growth (boosting equity ETFs), inflation (eroding fixed income ETF returns), interest rates (e.g., rate hikes pressuring BND), and employment data (influencing consumer-driven ETFs).

4. **Geopolitical Events**
   - Examples include wars (e.g., Russia-Ukraine conflict spiking oil ETFs like USO), trade tensions (e.g., U.S.-China tariffs affecting EEM), or elections (market volatility impacting broad ETFs like SPY).

5. **Regulatory Changes**
   - New financial rules (e.g., SEC restrictions on leveraged ETFs), tax policy shifts (e.g., capital gains changes), or environmental regulations (e.g., carbon taxes boosting clean energy ETFs like ICLN).

6. **Technological Advancements**
   - Breakthroughs like AI development (lifting tech ETFs such as XLK), biotech innovations (e.g., mRNA vaccines boosting XBI), or renewable energy progress (e.g., solar advancements aiding TAN).

7. **Currency Movements**
   - Exchange rate fluctuations impacting international ETFs (e.g., a stronger USD reducing EFA returns for U.S. investors) or currency-specific ETFs (e.g., FXY tied to yen performance).

8. **Fund-Specific Factors**
   - Expense ratios (e.g., low-cost VTI vs. higher-cost thematic ETFs), liquidity (e.g., daily trading volume), tracking error (deviation from index), and dividend yields (e.g., high-yield DIV vs. growth-focused VUG).
----------------------------------------------------------------

INSTRUCTIONS:
1. **Provide a Comprehensive Overview:**
   - For each category listed in the USER MESSAGE, explain its relevance to ETF performance and provide at least one specific example:
     - E.g., "Rising interest rates typically reduce bond ETF values (e.g., BND) due to inverse yield-price relationships."
     - E.g., "A tech sector rally driven by AI advancements could propel equity ETFs like XLK."
   - Tailor explanations to different ETF types where applicable (e.g., equity vs. commodity ETFs).

2. **Analyze Factor Interactions:**
   - Detail how the listed factors intersect to influence ETF performance, covering at least two examples:
     - E.g., "Rising inflation (economic indicator) and tightening monetary policy (regulatory change) could jointly depress fixed income ETFs like AGG while boosting commodity ETFs like DBC."
     - E.g., "A geopolitical crisis (e.g., Middle East unrest) paired with a strong USD (currency movement) might elevate oil ETFs (e.g., USO) but pressure emerging market ETFs (e.g., EEM)."
   - Discuss both synergistic (reinforcing) and counteracting (offsetting) effects.

3. **Develop Detailed Scenarios:**
   - Include at least two scenarios with specific ETF examples, detailing causes, effects, and potential outcomes:
     - **Scenario 1**: "The Federal Reserve raises interest rates by 50 basis points unexpectedly. Equity ETFs like SPY may face short-term selling pressure due to higher borrowing costs, while bond ETFs like HYG (high-yield) could see amplified declines from credit risk fears."
     - **Scenario 2**: "A major lithium battery breakthrough is announced. Clean energy ETFs like QCLN could surge due to increased demand for electric vehicle materials, while traditional energy ETFs like XLE might lag as investor focus shifts."
   - Quantify impacts where possible (e.g., percentage price shifts) or describe directional trends if data is limited.

4. **Offer a Forward-Looking Perspective:**
   - Identify 1-2 factors likely to dominate ETF performance in the next 3-12 months (e.g., interest rates, technological innovation).
   - Provide reasoning tied to general market dynamics or hypothetical trends:
     - E.g., "If inflation persists above 3%, fixed income ETFs like TLT may underperform, while inflation-hedge ETFs like TIP could gain traction."
     - E.g., "Continued AI advancements could favor tech-heavy ETFs like VGT over value-focused ETFs like VYM."
   - Acknowledge uncertainties (e.g., "Without specific geopolitical data, risks remain unpredictable").

5. **Ensure Structure and Readability:**
   - Organize the output with clear headings (e.g., "Overview of Drivers," "Factor Interactions") and subheadings or bullet points for each category or scenario.
   - Follow a logical sequence: overview, interactions, scenarios, then outlook.

6. **Handle Limited Data:**
   - If current data (e.g., today's interest rates, recent events) is unavailable, note this explicitly and rely on general principles or hypothetical assumptions. Avoid inventing specifics.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.

END OF PROMPT
"""

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

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def treasuries_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    treasuries_steps = [
        "Analyzing U.S. Treasury market conditions",
        "Evaluating Treasury performance",
        "Examining Treasury tracking efficiency",
        "Processing Treasury factor analysis",
        "Analyzing Treasury sector performance",
    ]

    animation = start_animation(treasuries_steps, "Treasury Market Analysis")
    
    system_prompt = """
You are an expert macroeconomic analyst with a specialization in U.S. Treasury markets and yield curves. You have deep knowledge of factors affecting Treasury yields—such as inflation, Federal Reserve policy, geopolitical risks, and market positioning. You prioritize clarity, detail, and data-driven reasoning in your analysis. Always cite relevant points from the provided context to ground your conclusions in facts. 
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how treasuries are influenced by economic indicators, geopolitical risks, currency movements, policy changes, and technological shifts.

Please analyze the following text and produce a well-structured, data-driven report on the behavior of U.S. Treasuries and rates, focusing on:
1. How recent economic data (inflation, employment, wages, growth) has influenced government bond performance.  
2. Specific behavior of the 2s10s yield curve (the yield differential between 2-year and 10-year Treasury notes) during these periods.  
3. Historical tendencies versus current data and outlook for the 2s10s curve.  
4. Upcoming factors that may impact Treasury rates, including but not limited to:
   - Tariffs
   - Inflation data
   - "Flight to quality" (potential equity sell-off)
   - Bond issuance
   - Passive flows (central bank and mutual fund activity, rebalancing)
   - CTA/technical drivers

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

CONTEXT:
----------------------------------------------------------------
US Treasuries/rates
Government bond performance as it relates to the recent economic data, especially inflation, wages in 
employment and growth. How did the 2s10s curve (yield differential between the 2 year and 10 year 
treasury yield) behave during these periods. How should the curve behave given historical tendencies and 
given the current data and outlook?

Upcoming factors potentially impacting rates:
- Tariffs
- Inflation data
- "flight to quality" - Further Equity selloff
- Bond issuance
- Passive flows (central bank purchases/sales, mutual fund purchases/sales, fund rebalancing)
- CTA/technical.

The U.S. Treasury market is influenced by a range of factors, broadly categorized into economic data,
Federal Reserve policy, geopolitical risks, fiscal policy and supply dynamics, and global demand for safe-
haven assets. Here are the key drivers:

1. Economic Data and Inflation
    • Inflation (CPI, PCE Deflator) - Higher inflation typically leads to higher yields as investors demand greater compensation for eroded purchasing power.
    • Employment Data (Non-Farm Payrolls, Unemployment Rate, JOLTS, Initial Jobless Claims) - Strong job growth suggests economic strength and potential inflationary pressures, impacting Fed policy expectations.
    • GDP Growth - Faster economic growth can lead to higher Treasury yields, while weak growth supports lower yields.
    • Consumer and Business Confidence (Consumer Confidence, ISM, PMIs) - These indicators gauge economic sentiment and can signal future growth trends.

2. Federal Reserve Policy
    • FOMC Rate Decisions & Forward Guidance - Changes in the Fed Funds rate directly influence short-term Treasury yields, while guidance on future policy impacts the yield curve.
    • Quantitative Easing (QE) / Quantitative Tightening (QT) - The Fed's balance sheet policy affects supply and demand for Treasuries.
    • Dot Plot & Summary of Economic Projections - Provides insights into policymakers' expectations for future rates.

3. Treasury Issuance and Fiscal Policy
    • U.S. Budget Deficit & Debt Issuance - Larger deficits often require more Treasury issuance, potentially pushing yields higher.
    • Treasury Refunding Announcements - The quarterly refunding schedule provides insight into future issuance and market absorption capacity.
    • Spending Bills & Stimulus Programs - Government spending plans impact future supply and inflation expectations.

4. Geopolitical Risks & Global Uncertainty
    • War and International Conflicts - Events like Russia-Ukraine, Middle East tensions, or China-Taiwan concerns can trigger flight-to-quality moves into Treasuries.
    • Trade Wars & Tariffs - U.S.-China tensions, for example, can impact global growth and Treasury demand.
    • Energy Prices & Commodity Shocks - Rising oil prices can fuel inflation, affecting yields.

5. Foreign Demand and Currency Movements
    • Demand from Foreign Central Banks (China, Japan, Europe, Middle East) - Key buyers of Treasuries can influence yields by increasing or decreasing their purchases.
    • U.S. Dollar Strength & Treasury Demand - A strong dollar can reduce foreign demand for Treasuries, while a weaker dollar may attract buyers.
    • Sovereign Debt Market Comparisons - Relative yields vs. German Bunds or JGBs influence foreign investor appetite.

6. Market Liquidity & Positioning
    • Hedge Fund and Dealer Positioning - Large speculative positioning in futures or options markets can drive short-term volatility.
    • Liquidity Conditions - If market depth declines, small shifts in supply/demand can cause outsized moves.
    • Repo Market Stress - Disruptions in funding markets can spill over into Treasury yields.

7. Credit & Risk Sentiment
    • Corporate Bond Spreads - Wider credit spreads often lead to a bid for Treasuries as investors seek safety.
    • Equity Market Volatility (VIX, Risk-Off Moves) - Stock selloffs usually drive Treasury rallies (lower yields).
    • Banking Sector Stress (e.g., SVB, Credit Suisse Issues) - Concerns about financial stability often trigger Treasury buying.
    • Equity Market Volatility (VIX, Risk-Off Moves) - Stock selloffs usually drive Treasury rallies (lower yields).
    • Banking Sector Stress (e.g., SVB, Credit Suisse Issues) - Concerns about financial stability often trigger Treasury buying.
----------------------------------------------------------------

INSTRUCTIONS:
1. Provide an in depth and detailed overview of the overall context (recent economic data, inflation, employment, etc.).
2. Discuss how these data points have influenced the 2s10s yield curve historically and in the current environment.
3. Cite and connect the relevant points from the context above to explain the underlying drivers (Fed policy, geopolitical risk, etc.).
4. Identify and evaluate the upcoming factors (tariffs, inflation data, etc.) that could impact rates.
5. Conclude with a forward-looking perspective, highlighting future market positioning and risk sentiment.
6. Present your answer in an organized, multi-paragraph format. Where appropriate, use bullet points or brief subheadings for clarity.
7. If any information is unclear or not provided in the context, acknowledge the gap rather than guessing or fabricating data.
8. Be as detailed as possible in your analysis.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.
    """

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

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def foreign_exchange_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    fx_steps = [
        "Analyzing FX market conditions",
        "Evaluating FX performance",
        "Examining FX tracking efficiency",
        "Processing FX factor analysis",
        "Analyzing FX sector performance",
    ]

    animation = start_animation(fx_steps, "Foreign Exchange Market Analysis")
    
    system_prompt = """
You are an expert FX strategist with deep knowledge of currency valuation models and global monetary dynamics. You prioritize clarity, detail, and factual grounding in your analyses. If information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how foreign exchange (FX) rates—particularly the U.S. Dollar (USD)—are influenced by various valuation methodologies (PPP, IRP, fundamental analysis, technical approaches) and key market drivers such as Federal Reserve policy, macroeconomic data, global risk sentiment, and geopolitical events.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please analyze the following reference materials on currency valuation and the drivers of the U.S. Dollar, then produce a well-structured report that addresses:
1. A concise overview of the main FX valuation methods (e.g., PPP, IRP, fundamental, technical/sentiment).
2. Key drivers specifically influencing the U.S. Dollar (Fed policy, inflation data, interest rate differentials, geopolitical risk, etc.).
3. How these valuation models and drivers might interplay in the short, medium, and long term.
4. An outlook on which factors may be most significant for USD performance in the near future.

CONTEXT (REFERENCE MATERIAL):
-----------------------------------------------------------------------------------------------
FX/Currencies:
The U.S. Dollar Index (DXY), which measures the USD against a basket of major currencies (EUR, JPY, GBP, CAD, SEK, CHF), is influenced by a combination of economic data, Federal Reserve policy, global risk sentiment, and geopolitical events. Here are the main valuation methodologies:

1. Parity Conditions-Based Valuation
   - Purchasing Power Parity (PPP)
     --> Based on the "law of one price," stating that identical goods should have the same price across countries when converted into a common currency.
     --> The exchange rate should adjust so that a basket of goods costs the same in different countries.
     --> Used as a long-term valuation tool.

   - Interest Rate Parity (IRP)
     --> Links exchange rate movements to interest rate differentials.
     --> The forward exchange rate should be set to prevent arbitrage between interest rate differences across countries.
     --> Used to explain forward rate premiums/discounts.

   - Real Exchange Rate (RER) Approach
     --> Adjusts the nominal exchange rate for inflation differentials.
     --> If a country's real exchange rate is overvalued, its currency might depreciate in the future.

   - Monetary Model
     --> Relates exchange rates to differences in money supply growth, inflation, and output between countries.
     --> More relevant for long-term FX valuation.

2. Fundamental Analysis-Based Valuation
   - Balance of Payments (BoP) Model
     --> Examines trade balances, capital flows, and foreign reserves.
     --> Persistent trade surpluses lead to currency appreciation, while deficits lead to depreciation.

   - Asset Market Approach
     --> Considers interest rates, bond yields, and equity markets.
     --> Capital inflows into a country's bonds and equities support currency appreciation.

   - Behavioral Equilibrium Exchange Rate (BEER)
     --> Uses econometric models to determine whether a currency is overvalued or undervalued.
     --> Includes factors like productivity, terms of trade, and net foreign assets.

   - Debt Sustainability Approach
     --> Evaluates a country's external debt levels.
     --> Countries with unsustainable debt levels often face currency depreciation.

3. Market-Based (Technical & Sentiment) Valuation
   - Real Effective Exchange Rate (REER)
     --> A trade-weighted index that measures a currency's relative strength against a basket of currencies, adjusted for inflation.

   - FX Forward and Options Market Pricing
     --> Forward rates incorporate market expectations of future exchange rate movements.
     --> Options pricing (e.g., risk reversals) can signal expected volatility and directional bias.
   - Technical Analysis
     --> Uses price charts, historical trends, and momentum indicators to forecast FX movements.
     --> Common tools: moving averages, Fibonacci retracements, Bollinger bands.
   - Market Sentiment Indicators
     --> CFTC Commitment of Traders (COT) report tracks speculative positioning.
     --> Carry trade flows indicate risk appetite and currency demand.

Which Model Is Best?
   - Long-term: PPP, balance of payments, monetary models.
   - Medium-term: BEER, REER, asset market approach.
   - Short-term: Market-based (technical, sentiment, and positioning).

Below are the key drivers of the U.S. dollar's movements:

1. Federal Reserve Policy & Interest Rates
   - Fed Funds Rate & Forward Guidance - Higher interest rates increase the appeal of the dollar by offering better returns.
   - FOMC Meetings & Dot Plot - Market expectations for future rate hikes/cuts impact the dollar.
   - Quantitative Tightening (QT) & Liquidity - Reducing the Fed's balance sheet strengthens the USD by tightening money supply.
   - Key Reports: FOMC Meeting Minutes, Fed Chair Speeches, Inflation & Employment Data

2. Inflation & Economic Data
   - Inflation (CPI, PCE Deflator) - Higher inflation can push the Fed to tighten policy, boosting the dollar.
   - Employment Reports (Non-Farm Payrolls, Unemployment Rate, Jobless Claims) - A strong labor market supports Fed rate hikes.
   - GDP Growth - Stronger economic growth attracts capital inflows into the U.S.
   - Retail Sales & Consumer Confidence - Consumer spending strength signals economic health, affecting USD demand.
   - ISM Manufacturing & Services PMI - Indicators of expansion/contraction influencing USD sentiment.
   - Key Reports: CPI, Core PCE Price Index, Non-Farm Payrolls, GDP Reports

3. Global Interest Rate Differentials
   - U.S. vs. Global Rate Spreads - If the Fed keeps rates higher than other central banks (ECB, BoJ, BoE), USD appreciates.
   - Central Bank Divergence - A hawkish Fed vs. a dovish ECB/BoJ strengthens the USD.
   - Key Reports: ECB, BoE, BoJ, RBA, PBoC Policy Statements; U.S. Treasury Yields vs. Global Bonds

4. Geopolitical & Risk Sentiment
   - Safe-Haven Flows - Global uncertainty (wars, banking crises) boosts demand for the U.S. dollar.
   - Conflict & War (Russia-Ukraine, Middle East, China-Taiwan) - Geopolitical risks drive investors into USD as a safe haven.
   - Sanctions & Trade Wars (U.S.-China, Tariffs, Export Bans) - Disruptions impact global trade flows and USD demand.
   - Debt Ceiling & U.S. Fiscal Policy - Government shutdowns or deficit concerns influence USD stability.
   - Key Events: War & Political Instability, U.S.-China Trade Relations, U.S. Debt Ceiling & Government Shutdowns

5. Global Liquidity & Financial Market Conditions
   - Equity Market Volatility (VIX Index, Stock Market Selloffs) - When risk-off sentiment rises, USD strengthens.
   - Banking System Stress (Credit Crunch, Dollar Shortages) - A shortage of USD liquidity increases demand for the greenback.
   - Commodity Prices & Inflation Expectations - Rising oil/gas prices can either boost or weaken USD, depending on the inflation impact.
   - Key Reports: VIX Index, LIBOR/SOFR, Dollar Funding Costs

6. U.S. Trade & Current Account Balance
   - Trade Balance (Exports vs. Imports) - A wider U.S. trade deficit can weaken the USD.
   - U.S. Current Account Deficit - A large deficit suggests more dollars flowing out, potentially weakening the USD.
   - Foreign Exchange Reserves & Central Bank USD Holdings - China, Japan, and others adjusting their FX reserves can impact USD demand.
   - Key Reports: U.S. Trade Balance, Treasury International Capital (TIC) Data

7. Emerging Market & Global Currency Trends
   - China's Yuan (CNY) & Emerging Market Currencies - Weakness in EM currencies often strengthens the dollar.
   - Capital Flight & De-Dollarization Trends - Global shifts away from USD reliance can impact demand over time.
   - BRICS & Alternative Reserve Currencies - Any effort to reduce USD's dominance in global trade could weaken demand.
   - Key Reports: BRICS Currency Initiatives, IMF SDR Allocation
-----------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Summarize the primary valuation approaches (PPP, IRP, fundamental, and technical/sentiment) used for FX.
2. Highlight the main macro drivers of the U.S. Dollar, referencing Fed policy, inflation, global rates, geopolitical risk, etc.
3. Illustrate how these valuation models and drivers interact over different time horizons (short, medium, long term).
4. Conclude with a short forward-looking assessment on which factors may be most impactful in the near-term USD outlook.
5. If any detail is missing or unclear, note it explicitly rather than fabricating information.
6. Organize your response clearly with headings or bullet points.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.
    """

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

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def ig_credit_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    ig_credit_steps = [
        "Analyzing IG credit market conditions",
        "Evaluating IG credit performance",
        "Examining IG credit tracking efficiency",
        "Processing IG credit factor analysis",
        "Analyzing IG credit sector performance",
    ]

    animation = start_animation(ig_credit_steps, "IG Credit Market Analysis")
    
    system_prompt = """
You are an expert credit analyst specializing in U.S. Investment Grade (IG) corporate bonds. You have deep knowledge of credit fundamentals, spread analysis, interest rate dynamics, and market technicals. You prioritize clarity, detail, and factual grounding in your analyses. If information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of U.S. Investment Grade (IG) Credit Bonds, focusing on the key drivers that influence their performance, pricing, and spread dynamics.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please analyze the following reference materials on IG credit markets and produce a well-structured report that addresses:
1. A comprehensive overview of the main factors influencing IG corporate bond performance.
2. Current market conditions and trends in the IG credit space.
3. How various factors (company fundamentals, interest rates, economic data, etc.) interplay to affect IG bond valuations.
4. An outlook on which factors may be most significant for IG credit performance in the near future.

CONTEXT (REFERENCE MATERIAL):
-----------------------------------------------------------------------------------------------
CORPORATE CREDIT
U.S. Investment Grade (IG) Credit Bonds are influenced by a mix of macro factors, credit-specific metrics,
market liquidity, and global risk sentiment. Here are the most important drivers:

1. Company credit ratings
    Individual company spreads are first and foremost influenced by a company's rating which is influenced
    and determined by rating agencies' reviews of a company's financials after every earnings release with
    ongoing monitoring.

Corporate Fundamentals & Credit Metrics
    • Earnings Reports (Revenue, EBITDA, Free Cash Flow) - Strong corporate earnings support credit quality and reduce default risk.
    • Debt-to-EBITDA & Leverage Ratios - Higher leverage raises concerns over creditworthiness.
    • Interest Coverage Ratios - Indicates a company's ability to service debt.
    • Ratings Agency Actions (Moody's, S&P, Fitch) - Downgrades or upgrades impact bond pricing and spreads.

Key Reports:
    • Corporate Earnings Releases
    • Ratings Agency Announcements

2. Interest Rates & Federal Reserve Policy
    • Fed Funds Rate & Forward Guidance - IG credit spreads tighten when the Fed signals stability or cuts rates, while hikes increase borrowing costs.
    • Treasury Yield Curve (10Y, 2Y, 30Y Yields, Inversions) - IG bonds are priced off risk-free Treasury rates, with higher yields raising corporate borrowing costs.
    • Quantitative Tightening (QT) & Fed Balance Sheet Reduction - Fed selling Treasuries and MBS reduces market liquidity, which can widen credit spreads.

Key Reports:
    • FOMC Meeting Minutes
    • Fed Dot Plot & SEP (Summary of Economic Projections)
    • Treasury Yield Movements

3. Credit Spreads & Market Liquidity
    • Investment Grade Credit Spreads (OAS, CDX IG Index, BBB vs. A Spreads) - Widening spreads indicate risk-off sentiment.
    • Primary Market Issuance (New Bond Supply) - Large new issuance can temporarily widen spreads.
    • Bond Market Liquidity (Bid-Ask Spreads, Dealer Inventories) - Thin liquidity can exacerbate credit spread movements.

Key Indicators:
    • Bloomberg Barclays U.S. IG Corporate Bond Index
    • ICE BofA Investment Grade OAS

4. Economic Data & Growth Outlook
    • GDP Growth - A strong economy supports corporate revenues and IG bond demand.
    • Inflation (CPI, PCE Deflator) - High inflation leads to tighter monetary policy, pressuring IG bonds.
    • Employment & Wage Growth (Non-Farm Payrolls, JOLTS, Unemployment Rate) - Strong labor markets imply economic resilience but could lead to rate hikes.

Key Reports:
    • GDP Growth
    • CPI & PCE Inflation Reports
    • Non-Farm Payrolls (NFP)

5. Geopolitical & Market Risk Sentiment
    • Geopolitical Tensions (Russia-Ukraine, Middle East, China-Taiwan) - Flight-to-quality moves can impact IG spreads.
    • U.S. Fiscal Policy & Debt Ceiling Concerns - Increased Treasury issuance for deficit funding can crowd out corporate bond demand.
    • Banking Sector Stability (Financial Conditions, Credit Markets) - Stress in the banking sector can lead to wider IG spreads.

Key Indicators:
    • VIX (Market Volatility)
    • Treasury Issuance Announcements

6. Global Demand & Foreign Investment
    • Foreign Central Bank & Sovereign Wealth Fund Purchases - High demand from global investors (China, Japan, EU) tightens spreads.
    • Relative Yields (U.S. IG vs. Euro Credit, EM Bonds) - U.S. IG attracts capital if it offers better risk-adjusted returns.
    • Hedging Costs for Foreign Investors - FX hedging costs impact overseas demand for U.S. IG bonds.

Key Reports:
    • TIC Data (Foreign Holdings of U.S. Bonds)
    • Relative Yield Comparisons (U.S. vs. European IG Credit)

7. Sector-Specific Credit Risks
    • Financials (Bank & Insurance IG Bonds) - Heavily influenced by financial stability, regulations, and Fed policy.
    • Tech & High-Growth Names - Sensitive to rate hikes as they rely on low-cost funding.
    • Energy & Industrials - Commodity price fluctuations impact creditworthiness.

Key Reports:
    • Sector-Specific Earnings Reports
    • Industry Credit Spreads
-----------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Summarize the key drivers influencing U.S. Investment Grade corporate bond performance.
2. Analyze current market conditions for IG credit based on the most recent data.
3. Explain how company fundamentals, macroeconomic factors, and market technicals interact to affect IG bond valuations.
4. Discuss sector-specific trends and differences in the IG credit space.
5. Provide a forward-looking assessment on which factors may be most impactful for IG credit in the near term.
6. If any detail is missing or unclear, note it explicitly rather than fabricating information.
7. Organize your response clearly with headings or bullet points.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.
    """

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

    # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def high_yield_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    high_yield_steps = [
        "Analyzing high-yield bond market conditions",
        "Evaluating high-yield bond performance",
        "Examining high-yield bond tracking efficiency",
        "Processing high-yield bond factor analysis",
        "Analyzing high-yield bond sector performance",
    ]

    animation = start_animation(high_yield_steps, "High Yield Bond Market Analysis")
    
    system_prompt = """
You are an expert fixed-income strategist with deep knowledge of both U.S. high-yield bond markets and emerging market (EM) debt. You prioritize clarity, detail, and factual grounding in your analysis. If information is missing, acknowledge that rather than fabricating data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a structured, data-driven analysis of how the key drivers of U.S. high-yield (HY) bonds may apply to or differ within emerging markets (EM) high-yield debt, focusing on factors such as credit spreads, default risks, liquidity conditions, and macroeconomic influences.

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Please use the reference material below on U.S. high-yield (HY) bonds to analyze how these drivers and metrics might apply within emerging markets. Specifically:
1. Summarize the primary risk factors, credit metrics, and market conditions affecting HY bonds in the U.S.
2. Discuss which of these factors might behave differently or be of particular relevance when looking at EM high-yield debt.
3. Identify any additional considerations unique to emerging markets (e.g., sovereign risk, currency fluctuations, political instability).
4. Conclude with a brief outlook on EM high-yield markets, referencing both global and local influences.

CONTEXT (REFERENCE MATERIAL):
----------------------------------------------------------------
HIGH YIELD BONDS  
U.S. High Yield (HY) Bonds: Key Market Drivers  
High-yield (HY) bonds (junk bonds) are more sensitive to credit risk, liquidity, and economic growth
expectations than investment-grade bonds. Here are the most important factors impacting HY bonds:

1. Credit Spreads & Risk Premiums  
   - High Yield Spreads (OAS, CDX HY Index, B vs. CCC Spreads) - Wider spreads indicate higher credit risk and market stress.  
   - Credit Default Swap (CDS) Index for High Yield - Rising CDS prices suggest increasing default concerns.  
   - Yield Curve (10Y vs. 2Y, Treasury Rates) - Rising Treasury yields make HY bonds less attractive relative to safer alternatives.  

   Key Indicators:
   - ICE BofA U.S. High Yield OAS
   - CDX HY Index
   - Bloomberg Barclays U.S. HY Bond Index

2. Federal Reserve Policy & Interest Rates  
   - Fed Funds Rate & Forward Guidance - Higher rates increase borrowing costs, making it harder for weaker firms to refinance.
   - Liquidity & Quantitative Tightening (QT) - Fed balance sheet reductions drain liquidity, affecting HY funding.
   - Yield Differentials (HY vs. IG Bonds) - If HY yields rise significantly over IG, it signals market risk aversion.

   Key Reports:
   - FOMC Meeting Minutes
   - Treasury Yield Curves
   - Fed's Financial Stability Reports

3. Corporate Fundamentals & Default Risk  
   - Earnings & Revenue Growth - Weak earnings pressure debt repayment ability.
   - Debt Maturities & Refinancing Risks - Many HY firms rely on rolling over debt; rate hikes make refinancing harder.
   - Leverage Ratios (Debt-to-EBITDA, Interest Coverage) - Highly leveraged companies are more vulnerable in rising rate environments.
   - Ratings Downgrades (Moody's, S&P, Fitch) - Fallen angels (IG to HY downgrades) increase supply and widen spreads.

   Key Reports:
   - Moody's & S&P Default Rate Forecasts
   - Corporate Earnings & Guidance
   - Distressed Debt Ratios

4. Economic Growth & Recession Risk  
   - GDP Growth Trends - Slowdowns hurt lower-rated firms first, increasing default risks.
   - ISM Manufacturing & Services PMI - A contraction signals economic stress for leveraged firms.
   - Consumer Spending & Retail Sales - HY issuers in consumer sectors are sensitive to demand shifts.
   - Housing Market Strength (NAHB, New Home Sales) - Impacts homebuilders, a key HY sector.

   Key Reports:
   - GDP Growth Data
   - ISM Manufacturing & Services PMI
   - Retail Sales & Consumer Confidence

5. Market Liquidity & Fund Flows  
   - High-Yield ETF & Mutual Fund Flows (HYG, JNK) - Inflows support HY, while outflows indicate risk-off sentiment.
   - Dealer Market Liquidity (Bid-Ask Spreads) - A stressed HY market can see spreads widen due to lack of liquidity.
   - Leveraged Loan Market Trends - Rising defaults in leveraged loans can spill over to HY bonds.

   Key Indicators:
   - HYG & JNK ETF Flows
   - Leveraged Loan Default Rates
   - Bid-Ask Spreads in HY Market

6. Geopolitical & Market Risk Sentiment  
   - Risk-Off Events (War, Sanctions, Political Uncertainty) - Investors flee riskier HY assets in favor of Treasuries.
   - Banking System Stability (Credit Crunch, Financial Conditions Index) - HY bonds underperform in periods of financial instability.
   - Stock Market Correlation (S&P 500 & Russell 2000) - HY bonds tend to track equity markets closely.

   Key Events:
   - VIX Index (Market Volatility)
   - Global Geopolitical Tensions
   - U.S. Debt Ceiling & Fiscal Policy

7. Sector-Specific Risks  
   - Energy (Oil & Gas HY Bonds) - Dependent on oil prices and production levels.
   - Retail & Consumer Discretionary - Vulnerable to weak consumer demand and economic slowdowns.
   - Technology & Communications - Rate-sensitive due to high leverage in growth sectors.

   Key Reports:
   - Sector-Specific HY Spread Indices
   - Commodity Price Movements (Oil, Gas, Metals)
----------------------------------------------------------------

INSTRUCTIONS:
1. Organize your response clearly, using headings or bullet points to address the listed items (1-4).
2. Ground your analysis in the context of the U.S. HY bond drivers, then connect them to emerging markets where relevant.
3. If any EM-specific data or factors are missing from the reference, acknowledge the gap rather than guessing.
4. Provide a succinct conclusion with a near-term outlook for EM high-yield bonds.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.
    """

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

        # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

def emerging_market_research_analyst():
    from src.phaseOne.phaseOneAnimation import start_animation, Colors
    date = datetime.now().strftime("%Y-%m-%d")

    emerging_market_steps = [
        "Analyzing emerging market conditions",
        "Evaluating emerging market performance",
        "Examining emerging market tracking efficiency",
        "Processing emerging market factor analysis",
        "Analyzing emerging market sector performance",
    ]

    animation = start_animation(emerging_market_steps, "Emerging Market Analysis")
    
    system_prompt = """
You are an expert emerging markets analyst with deep knowledge of the intersection between global macro forces and local EM conditions. You prioritize clarity, detail, and factual grounding in your assessments. If any information is missing, acknowledge that rather than guessing or inventing data.
    """

    user_prompt = f"""
GOAL / OBJECTIVE:
Provide a well-structured, data-driven analysis of how emerging markets (EM) equities and bonds are influenced by both global macro drivers (e.g., U.S. rates, risk sentiment, commodity prices, currency strength) and domestic fundamentals (growth, inflation, policy, political stability).

IMPORTANT:
- The date is {date} (REMEMBER THIS WHEN DOING YOUR RESEARCH)

Using the reference material below on emerging markets drivers, please create a clear, structured report addressing the following:
1. Summarize the global macro factors impacting EM (U.S. interest rates, risk appetite, commodity prices, USD strength, global liquidity).
2. Explain how domestic fundamentals (growth, inflation, monetary/fiscal policy, political stability) shape EM equity and bond performance.
3. Compare the differing dynamics between EM equities and EM bonds (local vs. hard currency debt), citing key market indicators.
4. Conclude with a brief near-term outlook on EM assets, noting any potential risks or catalysts to watch.

CONTEXT (REFERENCE MATERIAL):
---------------------------------------------------------------------------------------------------
EMERGING MARKETS
Emerging markets (EM) equity and bond prices are driven by a combination of global and domestic
factors, including macroeconomic conditions, monetary policy, investor sentiment, and political risks.
Here's a breakdown of the key drivers:

1. Global Macro and External Factors
   - U.S. Interest Rates & Federal Reserve Policy
     • Higher U.S. rates attract capital to U.S. assets, strengthening the dollar and leading to EM capital outflows.
     • Lower rates push investors toward riskier EM assets in search of yield.
   - Global Risk Appetite & Market Sentiment
     • Risk-on environments (growth optimism, low volatility) lead to EM inflows.
     • Risk-off episodes (crises, geopolitical risks) trigger EM outflows.
   - Commodity Prices
     • Many EM economies are commodity exporters (Brazil, Russia, South Africa, Indonesia). Rising commodity prices support their economies and assets, while falling prices hurt them.
   - U.S. Dollar Strength
     • A strong dollar increases the burden of dollar-denominated EM debt, pressuring bond yields and equity valuations.
     • A weaker dollar generally boosts EM assets as financing conditions improve.
   - Global Liquidity & Capital Flows
     • Quantitative easing (QE) by major central banks fuels liquidity-driven rallies in EM.
     • Quantitative tightening (QT) reduces liquidity and puts pressure on EM asset prices.

2. Domestic Economic Fundamentals
   - Growth & Inflation
     • Strong GDP growth typically supports equities and bonds.
     • High inflation erodes bond returns and increases rate hike risks.
   - Monetary & Fiscal Policy
     • Central bank rate cuts boost equities and bonds; rate hikes can dampen asset prices.
     • Fiscal deficits and excessive government borrowing weaken currencies and raise bond yields.
   - Currency Stability & FX Reserves
     • A stable currency attracts investment; depreciation raises funding costs.
     • Higher FX reserves provide a buffer against capital flight.

3. Political & Structural Factors
   - Geopolitical Risks & Sovereign Stability
     • Political instability, policy unpredictability, and geopolitical tensions increase risk premia.
     • Strong institutions and reforms enhance investor confidence.
   - Credit Ratings & Default Risks
     • Downgrades increase borrowing costs and trigger bond outflows.
     • Improvements in fiscal discipline lead to yield compression.

4. EM Equities vs. Bonds - Key Distinctions
   - Equities
     • More sensitive to domestic economic growth and corporate earnings.
     • Benefit from currency depreciation if companies are export-oriented.
     • Higher beta to global risk sentiment than bonds.
     • Dividend yields provide some income buffer during market turbulence.
   - Local Currency Bonds
     • Most sensitive to domestic inflation, monetary policy, and currency stability.
     • Offer higher yields but carry currency risk for foreign investors.
     • Benefit from interest rate cuts and disinflation.
   - Hard Currency (USD) Bonds
     • Less sensitive to local currency volatility but highly impacted by U.S. rate movements.
     • Sovereign spreads reflect country-specific default risk perceptions.
     • Benefit from improving credit fundamentals and global risk appetite.

5. Key Market Indicators to Watch
   - EM Equity Indices: MSCI EM, MSCI EM ex-China
   - Bond Indices: JPM EMBI Global Diversified (hard currency), JPM GBI-EM (local currency)
   - Currency Index: JPM EM Currency Index
   - Fund Flows: EM equity and bond fund flows (IIF data)
   - Positioning: CFTC positioning data for EM currencies
   - Credit Default Swaps (CDS): 5-year sovereign CDS spreads
   - Implied Volatility: EM FX volatility and equity volatility (VXEEM)

---------------------------------------------------------------------------------------------------

INSTRUCTIONS:
1. Organize your response with clear sections addressing each of the requested four topics.
2. Back your analysis with references to the market drivers and indicators mentioned in the context material.
3. If any information is missing, acknowledge the gap rather than inventing data.
4. Include a balanced perspective on EM opportunities and risks, considering both bullish and bearish factors.
5. Present your answer in an organized, multi-paragraph format with appropriate headings and bullet points.

IMPORTANT
- Use clear headings, subheadings, and bullet points to ensure readability and structure.
- Prioritize accuracy and logical reasoning, especially in the forward-looking perspective.
- Do not guess anything, if there is no data just say there is no data or do further research to find the data.
    """

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

        # Initialize client once with Perplexity API
    client = OpenAI(api_key=Sonar_API_KEY, base_url="https://api.perplexity.ai")
    
    try:
        # chat completion with streaming
        response = client.chat.completions.create(
            model=perplexity_model,
            messages=messages,
            stream=True
        )

        # Stop the animation before printing any output
        animation.stop()
        
        # Give terminal a moment to complete cleanup
        time.sleep(0.1)
        
        # Ensure fresh line for output (without clearing entire screen)
        print("\nStreaming response:")
        
        # Collect the streaming content
        collected_chunks = []
        collected_content = ""
        # Process each chunk
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
        
        return cleaned_content
    
    except Exception as e:
        # Stop the animation if there's an error
        animation.stop()
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        return None

