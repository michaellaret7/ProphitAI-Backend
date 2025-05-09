"""Prompt templates specifically for Phase One LLM interactions."""

from datetime import datetime
from .phase_one_formatting import format_to_json

min_asset_classes = 8
max_asset_classes = 16

SYSTEM_PROMPT = (
    "You are an elite portfolio manager who creates optimized investment "
    "portfolios. Your exceptional track record comes from conducting "
    "EXTENSIVE RESEARCH before making any recommendation.\n\n"
    "RESEARCH METHODOLOGY REQUIREMENTS:\n"
    "1. Conduct AT LEAST 5-7 detailed searches on different aspects of the market before making recommendations.\n"
    "2. For each search query, construct DETAILED and SPECIFIC prompts that will yield high-quality information.\n"
    "3. Research multiple sectors, market caps, geographies, and asset classes.\n"
    "4. Analyze macroeconomic trends, sector rotations, valuation metrics, and risk factors.\n"
    "5. Investigate both tactical (1-6 month) and strategic (1-3 year) opportunities.\n"
    "6. IMPORTANT: You MUST use the get_equity_universe and get_etf_universe tools first to understand available investment options before making recommendations.\n"
    "7. ALWAYS use SPECIFIC names of sectors, industries, ETFs, and other assets exactly as they appear in the data from get_equity_universe and get_etf_universe.\n\n"
    f"CRITICAL CONSTRAINT: Your final portfolio MUST contain between {min_asset_classes} and {max_asset_classes} asset classes - NO MORE, NO LESS. This is a hard requirement that cannot be violated.\n\n"
    "ONLY after conducting all required research using the specified tools and any additional free searches should you formulate your final recommendation."
)

USER_TEMPLATE = """
GOALS:
- Optimize the user's portfolio to outperform the S&P 500.
- Minimize risk while maximizing returns.
- Properly diversify the portfolio across multiple asset classes.
- Tailor the portfolio to the user's risk tolerance, investment goals, and other investment information that is retrieved from the get_user_information tool.
- Come up with a portfolio Thesis that explains why the portfolio is optimized for the user's profile. Make sure the portfolio allocations are aligned with the portfolio thesis.

REMEMBER THE CURRENT DATE IS {current_date}

------------------------------------------------------------------------------------------------------

### COMPREHENSIVE PORTFOLIO DATA (JSON):
```json
{comprehensive_portfolio_data_json}
```

------------------------------------------------------------------------------------------------------

### RULES (YOU MUST FOLLOW THESE RULES):
1. KEEP 5-7% OF THE PORTFOLIO IN CASH.
2. MAKE SURE ALL OF THE ALLOCATION PERCENTAGES ADD UP TO 100% OF THE PORTFOLIO
3. MINIMUM ASSET CLASSES ALLOWED: {min_asset_classes}
4. MAXIMUM ASSET CLASSES ALLOWED: {max_asset_classes}

### Directions:
1. Analyze the COMPREHENSIVE PORTFOLIO DATA (JSON provided above) which includes current portfolio positions, account information (if available within positions or user info tool), portfolio metrics, asset class metrics, monthly performance, diversification, and correlation matrix.
2. Identify the most significant issues affecting portfolio performance, focusing on asset class exposures.
3. IMPORTANT: You MUST use the data from the get_equity_universe and get_etf_universe tools to make specific recommendations for:
   - Specific equity sectors, industries, and sub-industries using ONLY the final category names from get_equity_universe
   - Specific ETFs using ONLY the final category names from get_etf_universe
   - Specific bond categories (Treasuries, Investment Grade, High Yield)
   - Specific commodities
   - Real Estate segments
   - Foreign Exchange exposures
   - Alternative Investments
4. DO NOT recommend generic ETF categories - use the specific sector/industry/ETF names exactly as they appear in the data tools.
5. Explain how each recommendation will improve the portfolio's return potential and risk profile.
6. Construct the portfolio of asset classes based on your thesis. The maximum number of asset classes you can choose in your portfolio is {max_asset_classes} and the minimum is {min_asset_classes}. If you go over or under this number, you will be penalized.
7. Write extensive and detailed reasoning for each allocation. Explain in depth why you chose the asset class you did and how it fits into the portfolio. This explanation will be returned in the JSON output.
8. Return portfolio in JSON format.

IMPORTANT:
- Be as granular and specific as possible with your recommendations.
- The Goal is to create a portfolio that will outperform the S&P 500. 
- YOU CAN ONLY CHOOSE FROM THE ASSET CLASSES AND SECTORS/INDUSTRIES/SUBINDUSTRIES THAT ARE IN THE get_equity_universe and get_etf_universe tools.
- USE ONLY THE FINAL/LEAF NODE NAME AS THE ASSET_CLASS VALUE, NOT THE FULL HIERARCHICAL PATH.
    - For example, use "multi_utilities" NOT "equity_sector_utilities_multi_utilities"
- IN ADDITION to providing a human-readable recommendation, you MUST also output the same recommendation in a machine-readable JSON format for automated processing.

Clear Example of Correct Asset Class Format:
- ✓ CORRECT: "asset_class": "multi_utilities"  
- ✗ INCORRECT: "asset_class": "equity_sector_utilities_multi_utilities"

Your response should have two parts:
1. Human-readable portfolio recommendation
2. JSON-formatted recommendation with the following structure:

**How to Write the `portfolio_thesis`:**
- For the `portfolio_thesis` field in the final JSON output, you must provide a concise (2-4 sentence) justification explaining *why* this specific portfolio recommendation is suitable for the user.

To construct this thesis:
1.  **Reference the User:** Start by explicitly mentioning key aspects of the user's profile gathered from the `get_user_information` tool (e.g., their risk tolerance, investment goals, time horizon).
2.  **Connect to Strategy:** Explain how the overall portfolio structure (the mix of asset classes, risk level, specific tilts) directly aligns with the user profile you just mentioned.
3.  **Incorporate Market View:** Briefly link the strategy to the key findings or outlook from your market research (analyst reports, free searches). Why do these allocations make sense *now*?
4.  **Justify Key Choices:** You might highlight one or two significant allocation decisions (e.g., overweighting a specific sector, including alternatives) and briefly state how they support the user's objectives or capitalize on market opportunities identified in your research.
5.  **Be Specific and Concise:** Ensure the thesis directly answers "Why this portfolio for this user?" clearly and succinctly.

===JSON OUTPUT===
```json
{{
    "portfolio": [
    {{
      "asset_class": "ONLY USE THE FINAL NODE NAME from get_equity_universe or get_etf_universe (Example: Use 'multi_utilities' NOT 'equity_sector_utilities_multi_utilities')",
      "allocation": "percentage of the portfolio allocated to this asset class",
      "reason": "Reason for the allocation. I want this to be a detailed and specific explanation for why you chose this asset class and how it fits into the portfolio."
    }}
  ],
  "portfolio_thesis": "portfolio thesis goes here"
}}
```

EXAMPLE JSON OUTPUT:
```json
{{
    "portfolio": [
        {{
            "asset_class": "multi_utilities",
            "allocation": 25,
            "reason": "The user has a medium risk tolerance and wants to maximize returns. The portfolio will be tilted towards growth sectors."
        }},
        {{ THIS IS AN EXAMPLE, THERE ARE MANY MORE ASSET CLASSES THAN THIS IN THE ACTUAL JSON OUTPUT }}
    ],
    "portfolio_thesis": (
        "The investor, a middle-aged individual with a net worth of approximately $2 million, presents a financial profile that calls for a meticulously balanced investment strategy. "
        "With a stated medium risk tolerance, the primary objective is to achieve substantial long-term capital appreciation while diligently managing downside risk to preserve the accumulated wealth. A secondary, yet increasingly important, goal is the generation of a reliable and growing stream of income, which will become more critical as the investor approaches and enters retirement. The typical investment horizon for this stage of life is considered to be 10-20 years, allowing for strategic allocations to growth-oriented assets while systematically de-risking as future liquidity needs draw closer. A 5-year specific goal for 'high growth' will be pursued with a dedicated portion of the growth allocation, understanding the higher volatility this might entail.\\n\\n"
        "Asset Allocation Philosophy:\\n"
        "The core of the strategy will be a globally diversified portfolio across multiple asset classes, including equities (domestic and international, covering large, mid, and small-cap), fixed income (government and corporate bonds, varying durations, and credit quality), real assets (e.g., real estate via REITs, infrastructure, commodities for inflation hedging), and potentially a smaller allocation to alternative investments (e.g., private credit, opportunistic strategies) to enhance diversification and risk-adjusted returns, where appropriate for the investor's accredited status and liquidity profile.\\n"
        "Given the medium risk tolerance, the portfolio will aim for a strategic asset allocation that might approximate 50-60% in growth-oriented assets (primarily equities) and 40-50% in capital preservation and income-generating assets (primarily fixed income and real assets). This allocation will be dynamically managed based on market conditions and the evolving investor's needs.\\n\\n"
        "Equity Strategy:\\n"
        "The equity portion will focus on high-quality companies with strong fundamentals, sustainable competitive advantages, and proven management teams. Emphasis will be placed on a blend of growth and value stocks. Geographic diversification will be achieved through investments in developed markets (e.g., US, Europe, Japan) and a strategic allocation to emerging markets to capture higher growth potential, commensurate with the investor's risk tolerance. Sector allocation will be actively managed, overweighting sectors with strong secular growth tailwinds (e.g., technology, healthcare, sustainable energy) while maintaining exposure to defensive sectors for stability.\\n\\n"
        "Fixed Income Strategy:\\n"
        "The fixed income component will serve to reduce overall portfolio volatility and generate consistent income. The allocation will include a mix of government bonds for safety, investment-grade corporate bonds for yield enhancement, and potentially inflation-protected securities (TIPS) to mitigate purchasing power erosion. Duration management will be key, adjusting based on interest rate outlooks. A portion may be allocated to high-yield bonds or emerging market debt for enhanced income, but this will be carefully sized to align with the medium risk profile.\\n\\n"
        "Real Assets and Alternatives:\\n"
        "Real estate (primarily through liquid REITs) will provide inflation hedging, income, and diversification benefits. Commodities exposure, if included, would be modest and aimed at hedging against unexpected inflation spikes. Alternative investments will be considered opportunistically, focusing on strategies that offer low correlation to traditional markets and can improve the portfolio's risk-adjusted return profile, subject to due diligence and liquidity considerations.\\n\\n"
        "Risk Management and Review:\\n"
        "Risk management is paramount. This will involve continuous monitoring of market conditions, geopolitical events, and macroeconomic trends. The portfolio will be regularly rebalanced to its strategic asset allocation targets. Stress testing will be performed to understand potential impacts of adverse market scenarios. A formal review of the portfolio's performance, alignment with goals, and the investor's circumstances will occur at least annually, or more frequently if significant market events or changes in the investor's situation warrant it. The strategy will also incorporate tax efficiency considerations in investment selection and withdrawal planning (when applicable).\\n\\n"
        "Addressing the 5-Year High Growth Goal:\\n"
        "A specific sub-portfolio, carved out from the overall growth allocation, will target higher growth opportunities over a 5-year timeframe. This may involve more concentrated positions in innovative sectors or companies, potentially including thematic ETFs or actively managed funds focused on disruptive technologies or high-growth industries. The performance and risk of this sub-portfolio will be monitored closely, with clear an understanding that this segment carries higher volatility than the core portfolio. Success in this segment will contribute to overall wealth accumulation, while any underperformance will be contained and not jeopardize the broader long-term financial security of the investor due to its defined allocation within the overall risk budget."
    )
}}
```
"""

def build_user_message() -> str:
    """Render USER_TEMPLATE with runtime data, including comprehensive portfolio JSON."""
    
    # Call format_to_json to get the comprehensive data
    # This function will handle connecting to IB, fetching all data, and formatting it.
    comprehensive_json_data = format_to_json()
    
    return USER_TEMPLATE.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        comprehensive_portfolio_data_json=comprehensive_json_data,
        min_asset_classes=min_asset_classes,
        max_asset_classes=max_asset_classes,
    ) 