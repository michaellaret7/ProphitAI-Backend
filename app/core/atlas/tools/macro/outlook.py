"""
In the future this will be a tool that will pull the latest outlook from our macro analyst agent. But tonight we will just return a static outlook.
"""

def get_outlook() -> dict:
    """Retrieve the current global macroeconomic outlook.

    Returns:
        dict: Structured response with success status and outlook data.
    """
    outlook = """
    Global Macroeconomic Outlook – Next 12 Months

    ### Executive Summary
    The global economy is entering a period of gradual normalization characterized by slower but positive growth. Following a resilient 2025 driven by consumer spending and a technology investment boom, world GDP growth is projected to ease toward the 3% range in 2026.

    The landscape is defined by divergence: the United States remains an outlier with resilient growth and sticky inflation, while the Eurozone faces muted recovery with stabilized prices, and China combats structural deceleration and deflationary pressures. Central banks are transitioning from synchronized tightening to a nuanced phase where policies will differ significantly by region.

    ---

    ### Regional Outlooks

    United States: Resilience Meets Sticky Inflation
    * Growth: The U.S. economy continues to defy recession expectations. After growing an estimated 2.8% in 2024, GDP is projected to expand roughly 2.0% in 2025 and cool toward 1.7–2.1% in 2026. Consumer spending remains the backbone of this expansion, supported by a tight labor market and fiscal stimulus.
    * Inflation: Unlike other advanced economies, U.S. inflation remains above the Federal Reserve's 2% target, hovering near 3%. High wage growth and new import tariffs (highest since the 1930s) are keeping price pressures elevated. Inflation is expected to peak in mid-2026 as tariff effects materialize before drifting lower.
    * Policy: The Federal Reserve is expected to hold rates at current restrictive levels in the near term. A gradual easing cycle may begin late in 2025 or 2026, bringing the fed funds rate to the mid-3% range by the end of 2026.

    Eurozone: Stability with Sluggishness
    * Growth: The recovery remains muted. GDP is forecast at 1.2–1.4% in 2025 and ~1.1–1.2% in 2026. While high energy costs and weak external demand weigh on manufacturing (particularly in Germany), the region is avoiding stagnation.
    * Inflation: Price stability has effectively been achieved. Inflation has fallen to near 2% and may dip below target in 2026 due to normalized energy prices.
    * Policy: The European Central Bank (ECB) has shifted to a "long pause," likely holding rates steady near 2% through 2026. Unlike the U.S., the ECB faces no immediate pressure to hike further, with a bias toward cuts if growth falters.

    China: Structural Deceleration & Policy Easing
    * Growth: The economy is decelerating, projected to grow 4.8–5.0% in 2025 before slowing to ~4.4% in 2026. A "two-speed" economy has emerged: high-tech and consumer services are gaining momentum, while the property sector and traditional industries remain in deep recession.
    * Inflation: China is verging on deflation, with CPI near 0%. Authorities are concerned about "too little" inflation, giving them ample room to stimulate.
    * Policy: The People's Bank of China (PBOC) is in easing mode, cutting rates and injecting liquidity. Fiscal policy is proactive, utilizing infrastructure spending and consumption incentives to offset the property market drag.

    Emerging Markets (EM): Leading the Cycle
    * Growth: EM economies are expanding at a moderate pace (~4.0–4.2%), with India and Southeast Asia leading due to supply chain diversification.
    * Policy: Many EM central banks (e.g., Brazil, Chile) are ahead of the curve, having already begun rate-cutting cycles as their inflation normalizes.

    ---

    ### Key Macro Themes

    1. Inflation & Monetary Policy Divergence
    Global inflation is generally receding, but the synchronized tightening cycle is over.
    * The Fed remains hawkish due to tariff-induced inflation.
    * The ECB is neutral/dovish as inflation hits targets.
    * The PBOC is actively dovish to fight deflation.
    * EM Central Banks are cutting rates to support growth.
    Investors face a mixed landscape where interest rate differentials may shift currency trends, particularly eroding the dollar's yield advantage as U.S. rates eventually plateau.

    2. Labor Markets
    Labor markets remain historically tight but are cooling.
    * U.S.: Unemployment is slowly drifting upward toward the mid-4% range. Wage growth remains sticky (~4%), complicating the Fed's inflation fight.
    * Eurozone: Unemployment is at record lows (~6.5%), supporting real incomes as inflation falls.
    * China: Youth unemployment remains a severe structural issue despite stable aggregate numbers.

    3. Global Trade & Supply Chains
    Global trade is slowing (~2.3% growth in 2026) due to protectionism. Supply chains are aggressively reconfiguring via "friend-shoring" and "China+1" strategies. While this increases resilience, it introduces inefficiencies and costs. Mexico, Vietnam, and India are emerging as primary beneficiaries of manufacturing relocation away from China.

    4. Fiscal Policy
    * U.S.: Remains expansionary with large deficits, acting as a short-term growth driver but raising long-term debt sustainability concerns.
    * Europe: Neutral to tightening as governments attempt to rebuild fiscal buffers.
    * China: Expansionary, heavily relying on state spending to prop up demand.

    ---

    ### Sector Performance

    * Technology & AI: The clear winner. Massive capital expenditure on AI, cloud computing, and semiconductors is fueling growth and equity market sentiment.
    * Services: continues to outpace manufacturing. Travel, hospitality, and business services remain robust.
    * Manufacturing: Remains in a soft patch globally, burdened by high interest rates and tariffs, though defense and renewable energy equipment are bright spots.
    * Real Estate: The weakest link. China's property crisis remains a systemic drag. In the West, commercial real estate (office) faces valuation risks from high rates and remote work trends.

    ### Major Risks

    * Geopolitics: Ongoing conflicts in Ukraine and the Middle East, along with U.S.-China tensions (Taiwan, trade wars), remain the primary downside risks. An escalation could spike energy prices or disrupt supply chains.
    * Trade War Escalation: Further tariff hikes or technology export bans could severely hamper global growth.
    * Financial Stability: Risks linger in the shadow banking sector and commercial real estate. A "hard landing" caused by policy error (rates kept too high for too long) remains a possibility.
    * Fiscal Debt: Sustainable debt trajectories in the U.S. and some European nations pose medium-term risks to bond markets.
    """

    return {
        "success": True,
        "data": {
            "outlook": outlook
        }
    }


# Tool Schema Constants
MACRO_OUTLOOK_DESCRIPTION = (
    "Retrieve the current global macroeconomic outlook for the next 12 months. "
    "Returns a comprehensive analysis covering regional economic conditions, key macro themes, and investment implications. "
    "\n\n**REPORT SECTIONS:**"
    "\n\n1. EXECUTIVE SUMMARY"
    "\n  - Global GDP growth projections"
    "\n  - Key regional divergences"
    "\n  - Central bank policy outlook"
    "\n\n2. REGIONAL OUTLOOKS"
    "\n  - United States: Growth, inflation, Fed policy"
    "\n  - Eurozone: Recovery trajectory, ECB stance"
    "\n  - China: Structural trends, PBOC policy"
    "\n  - Emerging Markets: Growth drivers, rate cycles"
    "\n\n3. KEY MACRO THEMES"
    "\n  - Inflation & monetary policy divergence"
    "\n  - Labor market dynamics"
    "\n  - Global trade & supply chains"
    "\n  - Fiscal policy trends"
    "\n\n4. SECTOR PERFORMANCE"
    "\n  - Technology & AI outlook"
    "\n  - Services vs manufacturing"
    "\n  - Real estate conditions"
    "\n\n5. MAJOR RISKS"
    "\n  - Geopolitical risks"
    "\n  - Trade war scenarios"
    "\n  - Financial stability concerns"
    "\n  - Fiscal debt trajectories"
    "\n\n**USE CASES:**"
    "\n  - Top-down portfolio positioning"
    "\n  - Sector rotation decisions"
    "\n  - Regional allocation strategy"
    "\n  - Risk assessment and scenario planning"
    "\n\n**NOTE:**"
    "\n  This tool takes no parameters. Call it directly to receive the latest outlook."
)

MACRO_OUTLOOK_PARAMETERS = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

MACRO_OUTLOOK_TOOL = {
    "name": "macro_outlook",
    "description": MACRO_OUTLOOK_DESCRIPTION,
    "parameters": MACRO_OUTLOOK_PARAMETERS,
    "function": get_outlook,
}
