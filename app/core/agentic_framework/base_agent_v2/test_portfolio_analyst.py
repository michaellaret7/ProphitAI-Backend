"""Portfolio Analysis Agent - Complex Multi-Tool Example

This agent analyzes a portfolio to identify strengths/weaknesses and proposes
evidence-backed trade ideas using portfolio and ticker tools.
"""

from app.core.agentic_framework.base_agent_v2.agent import BaseAgent
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode

# Import tool definitions from tool_lib
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL,
    INDUSTRY_CONCENTRATION_TOOL,
    VAR_CALCULATOR_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import (
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from app.core.agentic_framework.tool_lib.portfolio_tools.beta import (
    CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
)
from app.core.agentic_framework.tool_lib.risk_tools.pairwise_corr_analysis import (
    PAIRWISE_CORR_ANALYSIS_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.performance import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import (
    CALCULATE_TICKER_FACTORS_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import (
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.stock_screener.tool import STOCK_SCREENER_TOOL



def register_portfolio_analysis_tools(agent: BaseAgent) -> None:
    """Register all tools needed for portfolio analysis."""

    # Portfolio-level tools
    tools = [
        EXPOSURE_CALCULATOR_TOOL,
        INDUSTRY_CONCENTRATION_TOOL,
        VAR_CALCULATOR_TOOL,
        CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
        CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
        PAIRWISE_CORR_ANALYSIS_TOOL,

        # Ticker-level tools
        GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
        CALCULATE_TICKER_FACTORS_TOOL,
        GET_TICKER_FUNDAMENTAL_DATA_TOOL,
        STOCK_SCREENER_TOOL,
    ]

    for tool in tools:
        agent.add_tool(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"],
            function=tool["function"]
        )


def main():
    """Run portfolio analysis agent on a sample portfolio."""

    # Sample portfolio - Mix of strong performers and weak performers
    # This portfolio hasn't been rebalanced and shows both winners and losers
    sample_portfolio = {
        # Strong performers (AI/Tech winners)
        "NVDA": {"allocation": 0.15, "position": "long"},   # 15% Nvidia - AI chip leader
        "PLTR": {"allocation": 0.08, "position": "long"},   # 8% Palantir - AI/Data analytics
        "AVGO": {"allocation": 0.07, "position": "long"},   # 7% Broadcom - Semiconductors
        "HIMS": {"allocation": 0.06, "position": "long"},   # 6% Hims & Hers - Telehealth

        # Solid large caps (moderate performers)
        "AAPL": {"allocation": 0.12, "position": "long"},   # 12% Apple - Steady performer
        "MSFT": {"allocation": 0.12, "position": "long"},   # 12% Microsoft - AI exposure
        "JPM": {"allocation": 0.08, "position": "long"},    # 8% JPMorgan - Financials

        # Weak performers (losers needing review)
        "INTC": {"allocation": 0.10, "position": "long"},   # 10% Intel - Down 60% in 2024
        "KR": {"allocation": 0.09, "position": "long"},    # 9% Walgreens - Down 64% in 2024
        "MRNA": {"allocation": 0.07, "position": "long"},   # 7% Moderna - Down 60%, post-COVID decline
        "EL": {"allocation": 0.04, "position": "long"},     # 4% Estée Lauder - China exposure issues
        "GLOB": {"allocation": 0.02, "position": "long"},   # 2% Globant - Down 57% in 2025
    }

    # System prompt - defines the agent's role and capabilities
    system_prompt = """
Role: You are a senior portfolio analyst with expertise in quantitative analysis and fundamental research.
Task: Your task is to perform a comprehensive portfolio analysis and provide actionable insights.
Rules: You are never allowed to skip any main or sub tasks. (there will be severe consequences if you do)

Your capabilities include:
- Portfolio-level analysis: returns, volatility, exposures, concentrations, correlations, beta
- Ticker-level analysis: performance metrics, risk-adjusted returns, factor exposures, fundamentals
- Risk assessment: VaR, correlations, industry concentrations
- Trade idea generation: evidence-backed recommendations
- Use the stock screener tool to find other stocks to help with your trade idea.
"""

    # User prompt - specific task with the portfolio
    user_prompt = f"""Analyze the following portfolio and provide a comprehensive assessment:

Portfolio:
{sample_portfolio}

Please perform the following analysis:

1. **Portfolio Overview**:
   - Calculate key metrics (returns, volatility, Sharpe ratio)
   - Assess portfolio beta vs SPY
   - Check exposure types and concentration risks

2. **Risk Analysis**:
   - Industry concentration analysis
   - Correlation analysis between holdings
   - Value at Risk (VaR) assessment

3. **Strengths & Weaknesses**:
   - Summarize portfolio strengths (what's working well)
   - Summarize portfolio weaknesses (areas of concern)

4. **Trade Idea**:
   - Based on your analysis, propose ONE specific trade idea
   - The trade should address a weakness OR capitalize on a strength
   - Back your recommendation with specific evidence from your analysis
   - Be specific: What to buy/sell, how much, and why

Take your time and be thorough. Use the available tools to gather evidence before making conclusions. Be concise in your final answer.

Rules:
- You are never allowed to skip any main or sub tasks. (there will be severe consequences if you do)
- You are never allowed to list all of the subtasks in a main task as in progress, the most subtasks that can be in progress at once is 2.
- You must review the Insights section before you start the workflow.

# Portfolio Analysis Playbook
# Generated: 2025-10-30
# Source: Extracted from successful portfolio analysis execution

version: "1.0"
total_insights: 47
last_updated: "2025-10-30"

# ============================================================================
# DISTRESS SIGNAL DETECTION
# ============================================================================

distress_signals:
  
  - id: "distress_001"
    pattern: "Altman Z-Score <1.8 indicates financial distress"
    details: "When Z-Score falls below 1.8, immediately check current ratio, interest coverage, and debt/EBITDA ratios for confirmation. Below 1.0 is bankruptcy zone."
    evidence: "WBA showed Z-Score of 0.89 with current ratio 0.60 and interest coverage 0.42, confirming terminal financial distress"
    when_to_apply: "For any position with negative 1Y or 3Y returns"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.95
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_002"
    pattern: "Interest coverage <1.0 means company cannot service debt obligations"
    details: "Interest coverage = EBIT / Interest Expense. When <1.0, company is earning less than required to pay interest, indicating high default risk."
    evidence: "WBA interest coverage of 0.42 showed company earning only 42% of interest owed - unsustainable debt load"
    when_to_apply: "Always check for companies with Altman Z <1.8 or high debt/equity >3.0"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.92
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_003"
    pattern: "Current ratio <1.0 signals liquidity crisis"
    details: "Current ratio = Current Assets / Current Liabilities. Below 1.0 means company cannot pay short-term obligations. Quick ratio <0.5 is severe."
    evidence: "WBA current ratio 0.60, quick ratio 0.32 showed inability to meet short-term liabilities - immediate distress signal"
    when_to_apply: "Check alongside Altman Z for any distressed company"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.90
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_004"
    pattern: "Net Debt/EBITDA >10x is unsustainable for mature companies"
    details: "Shows how many years of EBITDA needed to pay off debt. Above 10x indicates overleveraged, above 20x is severe distress."
    evidence: "WBA showed 45.3x net debt/EBITDA - extreme outlier indicating debt load far exceeds earning power"
    when_to_apply: "For mature companies (not high-growth startups), check when debt/equity >2.0"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_005"
    pattern: "Negative or declining ROE over 2+ years indicates fundamental deterioration"
    details: "ROE declining from positive to negative, or staying negative for 2+ years, suggests structural problems not cyclical weakness."
    evidence: "WBA ROE declined from -40% to -2%, showing persistent inability to generate returns on equity"
    when_to_apply: "Always check ROE trend for underperforming positions"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.85
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_006"
    pattern: "Revenue decline >20% YoY without new product pipeline indicates business collapse"
    details: "Large revenue declines combined with negative margins and no clear turnaround path suggest terminal decline, not cyclical downturn."
    evidence: "MRNA showed -40% YoY revenue decline with -581% net margins and no visible path to profitability - post-COVID collapse"
    when_to_apply: "For companies with large negative returns, check revenue trends"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.87
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "distress_007"
    pattern: "Triple distress signal = immediate sell: Altman Z <1.8 AND ROE <-10% AND D/E >3.0"
    details: "When all three signals present simultaneously, indicates terminal decline with high bankruptcy risk. Not a turnaround candidate."
    evidence: "WBA showed all three: Z=0.89, ROE=-40% to -2%, D/E=4.04 - terminal financial distress"
    when_to_apply: "Use as final confirmation before recommending position elimination"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.93
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# CONCENTRATION RISK MANAGEMENT
# ============================================================================

concentration_risks:
  
  - id: "concentration_001"
    pattern: "Sector concentration >50% requires sector-specific risk analysis"
    details: "When single sector exceeds 50% of portfolio, calculate sector beta, sector VaR contribution, and intra-sector correlations. High concentration creates unsystematic risk."
    evidence: "64% technology concentration with portfolio beta 1.414 (41% higher than market), indicating excessive sector risk"
    when_to_apply: "Always check sector concentration in portfolio overview phase"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.91
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "concentration_002"
    pattern: "Industry VaR contribution >30% flags concentration risk"
    details: "When single industry's VaR contribution exceeds its portfolio weight by >5pp, indicates correlation-driven concentration risk."
    evidence: "Semiconductors represented 32% of portfolio but contributed 38.9% of total VaR - 6.9pp excess concentration"
    when_to_apply: "Calculate after determining portfolio-level VaR"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.89
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "concentration_003"
    pattern: "Separate semiconductors from general 'tech' in concentration analysis"
    details: "Semiconductors have distinct risk profile from software/hardware. Always break down tech sector into: semiconductors, software, hardware, services."
    evidence: "32% semiconductor exposure hidden within 64% tech allocation - granular view revealed concentration risk"
    when_to_apply: "In industry concentration analysis, use granular GICS sub-industry classifications"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.85
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "concentration_004"
    pattern: "Portfolio beta >1.3 with high sector concentration = double risk exposure"
    details: "High beta indicates market sensitivity; combined with sector concentration creates compounded risk in sector downturns."
    evidence: "Portfolio beta 1.414 with 64% tech concentration means portfolio moves 41% more than market AND lacks diversification"
    when_to_apply: "Always cross-reference beta with sector concentration"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "concentration_005"
    pattern: "Zero defensive sector exposure increases downside risk"
    details: "Portfolios with no allocation to defensive sectors (utilities, staples, REITs) lack downside protection. Consider adding when beta >1.2."
    evidence: "Portfolio had 0% defensive exposure, 100% long equities with no hedges - vulnerable to tech corrections"
    when_to_apply: "Check in portfolio overview, flag if 0% defensive with high beta"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.82
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# PERFORMANCE ANALYSIS
# ============================================================================

performance_analysis:
  
  - id: "performance_001"
    pattern: "Compare CAGR vs alpha to separate skill from beta exposure"
    details: "High CAGR alone doesn't indicate good stock selection. Must compare alpha (excess return vs beta-adjusted benchmark) to assess true outperformance."
    evidence: "PLTR showed 300% CAGR with 112% alpha; AAPL showed positive return but -5.5% alpha - PLTR is true winner, AAPL just rode market"
    when_to_apply: "For every position in ticker-level analysis"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.90
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "performance_002"
    pattern: "Sharpe ratio >1.5 indicates strong risk-adjusted performance"
    details: "Sharpe = (Return - RiskFree) / Volatility. Above 1.5 is excellent, 1.0-1.5 is good, <1.0 questions if risk worth taking."
    evidence: "PLTR Sharpe 2.29, JPM Sharpe 1.75, NVDA Sharpe 1.67 all showed strong risk-adjusted returns; WBA negative Sharpe confirmed poor risk/reward"
    when_to_apply: "Calculate for all positions, prioritize holdings with Sharpe >1.5"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "performance_003"
    pattern: "3-year CAGR <0% with negative alpha = value trap, not opportunity"
    details: "Positions with multi-year negative returns AND negative alpha are destroying value. These are not 'cheap' - they're deteriorating."
    evidence: "WBA: -23% CAGR, -24% alpha; MRNA: -40% CAGR, -64% alpha; GLOB: -42% CAGR, -77% alpha - all value traps"
    when_to_apply: "Flag any position with negative 3Y CAGR for immediate distress analysis"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.92
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "performance_004"
    pattern: "Max drawdown >60% indicates extreme volatility or structural decline"
    details: "Maximum peak-to-trough decline. Above 60% suggests either business deterioration or unsustainable volatility for most portfolios."
    evidence: "MRNA max drawdown -85.92% indicated not volatility but business collapse from COVID peak"
    when_to_apply: "Check max drawdown for all underperforming positions"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.84
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "performance_005"
    pattern: "Down-capture <0.9 with beta ~1.0 indicates defensive characteristics"
    details: "Down-capture = (Stock return in down periods) / (Market return in down periods). <1.0 means outperforms in corrections."
    evidence: "JPM showed beta 0.93 with down-capture 0.87 - captures only 87% of market downside while providing equity-like returns"
    when_to_apply: "Identify defensive holdings that provide downside protection"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.86
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# FUNDAMENTAL ANALYSIS
# ============================================================================

fundamental_analysis:
  
  - id: "fundamental_001"
    pattern: "Fortress balance sheet = Altman Z >10, D/E <0.5, Current Ratio >2.0"
    details: "Companies with all three characteristics have exceptional financial strength and can weather downturns. These are quality holdings."
    evidence: "NVDA showed Altman Z 67.76, minimal debt, strong liquidity - fortress balance sheet supporting continued growth"
    when_to_apply: "Check for top-performing positions to confirm quality"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "fundamental_002"
    pattern: "ROE >20% with ROIC >15% indicates exceptional profitability"
    details: "High ROE shows strong equity returns; high ROIC shows efficient capital deployment. Together indicate quality business with competitive advantages."
    evidence: "NVDA ROE 26.4%, strong margins, minimal debt = quality compounder; contrast with WBA negative ROE"
    when_to_apply: "Use to distinguish quality growth from speculative growth"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.85
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "fundamental_003"
    pattern: "Negative EPS growth with negative revenue growth = business deterioration"
    details: "When both top-line and bottom-line declining, indicates fundamental business problems not temporary headwinds."
    evidence: "AAPL showed -4.85% EPS growth, -1.39% revenue growth despite premium valuation (P/B 56.1) - growth stalling"
    when_to_apply: "Check growth metrics for all large-cap positions"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.82
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "fundamental_004"
    pattern: "Net margin <-100% indicates company losing more than it earns in revenue"
    details: "Gross margin can be negative temporarily, but net margin <-100% means losses exceed sales - unsustainable burn rate."
    evidence: "MRNA net margin -581% to -908% showed company burning $5-9 for every $1 in sales - catastrophic"
    when_to_apply: "Always check margin structure for companies with negative returns"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.90
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "fundamental_005"
    pattern: "Declining gross margin + declining revenue = pricing power lost"
    details: "When company can't maintain margins AND losing revenue, suggests competitive position deteriorating."
    evidence: "INTC negative gross margins while losing share to NVDA/AMD - structural competitive loss"
    when_to_apply: "Check for underperformers in competitive industries"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.83
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# FACTOR ANALYSIS
# ============================================================================

factor_analysis:
  
  - id: "factor_001"
    pattern: "Growth factor: High EPS growth + high revenue growth + expanding margins"
    details: "True growth companies show acceleration in earnings, revenue, and margin expansion simultaneously. Single metric insufficient."
    evidence: "PLTR showed strong growth factor characteristics supporting 300% CAGR performance"
    when_to_apply: "Use to identify genuine growth vs expensive hope"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.80
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "factor_002"
    pattern: "Quality factor: High ROE + high ROIC + low debt + stable margins"
    details: "Quality companies generate strong returns on capital with minimal leverage and consistent profitability. These compound over time."
    evidence: "NVDA quality factor supported sustained outperformance and lower risk than high-beta suggests"
    when_to_apply: "Screen for quality in portfolio construction to reduce risk"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.84
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "factor_003"
    pattern: "Avoid value traps: Low P/E or P/B alone doesn't mean 'cheap'"
    details: "Must confirm value with: positive ROE, positive free cash flow, manageable debt, and catalyst for rerating. Otherwise it's a trap."
    evidence: "WBA and INTC appeared 'cheap' on multiples but were value traps destroying value due to fundamental deterioration"
    when_to_apply: "Always check quality metrics before labeling something 'value'"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.89
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# PORTFOLIO CONSTRUCTION
# ============================================================================

portfolio_construction:
  
  - id: "construction_001"
    pattern: "Winners deserve higher allocation if fundamentals support performance"
    details: "Positions with strong alpha, good Sharpe, and solid fundamentals should be core holdings. Don't over-diversify away from winners."
    evidence: "JPM showed 53% CAGR, 22% alpha, 1.75 Sharpe, defensive beta - recommended increasing from 8% to 16%"
    when_to_apply: "When rebalancing, consider increasing best performers with strong fundamentals"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.81
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "construction_002"
    pattern: "Use sector ETFs for diversification, not more single stocks"
    details: "When lacking sector exposure, sector ETFs provide diversification without single-stock risk. Better than picking individual names in unfamiliar sectors."
    evidence: "Recommended XLV (healthcare ETF) to add defensive exposure rather than picking individual healthcare stocks"
    when_to_apply: "When portfolio lacks sector diversification and adding <10% allocation"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.77
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "construction_003"
    pattern: "Target portfolio beta 1.0-1.2 for growth portfolios, <1.0 for conservative"
    details: "Beta >1.3 indicates excessive market sensitivity. For most portfolios, 1.0-1.2 provides growth participation with manageable volatility."
    evidence: "Portfolio beta 1.414 identified as too high, recommended rebalancing toward 1.2 through defensive additions"
    when_to_apply: "Check portfolio beta in overview, adjust if outside target range"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.79
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "construction_004"
    pattern: "Eliminate positions destroying value before adding new positions"
    details: "Cutting losers provides better risk-adjusted returns than adding winners. Clear the portfolio of value traps first."
    evidence: "Recommended selling WBA (-24% alpha) and MRNA (-64% alpha) before adding - removes drag on portfolio"
    when_to_apply: "When multiple positions have negative 3Y alpha, prioritize eliminations"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.86
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# TRADE GENERATION
# ============================================================================

trade_generation:
  
  - id: "trade_001"
    pattern: "One specific trade addressing biggest weakness is better than multiple trades"
    details: "Focus trade recommendation on highest-impact change. Multiple simultaneous trades harder to execute and monitor."
    evidence: "Recommended single trade: sell WBA+MRNA (eliminate value traps), buy JPM+XLV (add quality + diversification)"
    when_to_apply: "Final trade recommendation should be singular, specific, actionable"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.84
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "trade_002"
    pattern: "Sell signal: Triple negative = negative return + negative alpha + fundamental deterioration"
    details: "When position shows all three, immediate sell. These are not 'turnaround candidates' - they're dying businesses."
    evidence: "WBA showed -43% return, -24% alpha, Altman Z 0.89; MRNA showed -63% return, -64% alpha, revenue -40% - both immediate sells"
    when_to_apply: "Use as final confirmation for position elimination recommendations"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.91
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "trade_003"
    pattern: "Buy signal: Positive alpha + strong Sharpe + solid fundamentals + defensive characteristics"
    details: "Best additions show they can generate alpha, manage risk well, have strong balance sheet, and provide downside protection."
    evidence: "JPM met all criteria: 22% alpha, 1.75 Sharpe, defensive beta 0.93, down-capture 0.87 - ideal addition"
    when_to_apply: "Screen potential additions against these criteria"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.87
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "trade_004"
    pattern: "Back every trade with specific quantitative evidence, not qualitative hopes"
    details: "Trade recommendations must cite specific metrics: alpha, Sharpe, Z-score, ROE, etc. No vague statements about 'potential' or 'turnaround'."
    evidence: "Trade recommendation backed by: WBA Z=0.89, MRNA margin -581%, JPM alpha 22%, concentration 64%→56% - all quantitative"
    when_to_apply: "Every trade recommendation must have 3+ specific metrics as evidence"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "trade_005"
    pattern: "Trade should address portfolio weakness AND play to strength"
    details: "Best trades simultaneously fix problems (eliminate value traps, reduce concentration) AND enhance strengths (add to winners, improve risk-adjusted returns)."
    evidence: "Recommended trade eliminated distressed positions (weakness) while adding to proven alpha generator (strength)"
    when_to_apply: "Structure trades to be both defensive (fix problem) and offensive (enhance strength)"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.82
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# ANALYTICAL WORKFLOW
# ============================================================================

workflow:
  
  - id: "workflow_001"
    pattern: "Start with portfolio-level metrics before diving into individual positions"
    details: "Calculate returns, volatility, beta, and concentration first. This identifies biggest risks to investigate at position level."
    evidence: "Analysis started with portfolio overview revealing 64% tech concentration and 1.414 beta - guided subsequent position analysis"
    when_to_apply: "Always begin analysis with portfolio-level view"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.90
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "workflow_002"
    pattern: "Prioritize deep-dive analysis on outliers: worst performers and concentration risks"
    details: "Don't analyze all positions equally. Focus detailed fundamental analysis on: positions with negative returns, positions >10% of portfolio, sectors >30% of portfolio."
    evidence: "Deep fundamental analysis conducted on WBA (worst performer), MRNA (large negative return), and tech concentration"
    when_to_apply: "After portfolio overview, identify outliers for detailed analysis"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.86
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "workflow_003"
    pattern: "Calculate VaR contribution by position, not just allocation"
    details: "VaR contribution shows actual risk impact. Positions can contribute more risk than their allocation suggests due to volatility and correlations."
    evidence: "Semiconductors were 32% of portfolio but 38.9% of VaR - disproportionate risk contribution"
    when_to_apply: "Always decompose VaR by position in risk analysis"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "workflow_004"
    pattern: "Synthesize findings before generating trade recommendations"
    details: "Don't jump to trades after analysis. First synthesize strengths/weaknesses, identify patterns, then propose trade addressing key issues."
    evidence: "Analysis synthesized: 49% in winners, 28% in losers, 64% tech concentration, 0% defensive - THEN proposed specific trade"
    when_to_apply: "Always include explicit synthesis step before trade recommendation"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.84
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "workflow_005"
    pattern: "Cross-reference multiple metrics before reaching conclusions"
    details: "Single metrics can mislead. Confirm conclusions with multiple supporting data points from different analytical frameworks."
    evidence: "WBA distress confirmed by: performance (-23% CAGR), balance sheet (Z 0.89, D/E 4.04), liquidity (current 0.60), profitability (ROE negative)"
    when_to_apply: "Require 3+ supporting metrics before strong conclusions"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.87
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# RISK MANAGEMENT
# ============================================================================

risk_management:
  
  - id: "risk_001"
    pattern: "Daily VaR >4% indicates high-risk portfolio"
    details: "95% VaR represents expected loss in worst 5% of days. Above 4% suggests excessive risk for most investors."
    evidence: "Portfolio daily VaR 4.94% combined with 100% long exposure indicated high risk without hedging"
    when_to_apply: "Calculate and interpret VaR in every portfolio overview"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.81
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "risk_002"
    pattern: "100% long equity with no hedges increases tail risk"
    details: "Portfolios with no cash, no shorts, no options have no downside protection. Consider hedges when beta >1.2 and VaR >4%."
    evidence: "Portfolio 100% long equities, 0% hedged, beta 1.414, VaR 4.94% - vulnerable to market corrections"
    when_to_apply: "Check exposure breakdown in portfolio overview"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.79
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "risk_003"
    pattern: "Correlation analysis must be paired with concentration analysis"
    details: "Low average pairwise correlation doesn't mean diversified if concentrated in one sector. Must check both."
    evidence: "Average correlation 0.275 seemed reasonable, but 64% tech concentration created undiversified risk"
    when_to_apply: "Never rely on correlation alone for diversification assessment"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.85
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# COMMON PITFALLS TO AVOID
# ============================================================================

pitfalls:
  
  - id: "pitfall_001"
    pattern: "Don't confuse 'cheap' with 'value'"
    details: "Low P/E, P/B, or P/S doesn't mean value opportunity. Must confirm with positive fundamentals and catalyst."
    evidence: "WBA and INTC looked cheap on multiples but were value traps destroying shareholder value"
    when_to_apply: "Always check when position appears 'cheap' - verify not value trap"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "pitfall_002"
    pattern: "Don't average down on deteriorating fundamentals"
    details: "If position declining due to structural business problems (not valuation), adding to position compounds losses."
    evidence: "Buying more WBA or MRNA would have increased exposure to terminal decline - fundamental issues unfixable"
    when_to_apply: "Before recommending 'buy more of underperformer', check if cyclical or structural decline"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.86
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "pitfall_003"
    pattern: "Don't over-weight large-caps just because they're 'safe'"
    details: "Large-cap doesn't mean good investment. Must generate alpha or provide specific portfolio benefit."
    evidence: "AAPL and MSFT large allocations (24% combined) but near-zero alpha - 'safety' didn't mean outperformance"
    when_to_apply: "Question large-cap positions that aren't generating alpha"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.80
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "pitfall_004"
    pattern: "Don't ignore position sizing when calculating risk metrics"
    details: "Small positions with high volatility may contribute less risk than large positions with moderate volatility. Always weight by allocation."
    evidence: "NVDA 15% allocation had more VaR impact than smaller high-volatility positions due to size"
    when_to_apply: "Weight all risk metrics by position size"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.83
      created: "2025-10-30"
      last_used: "2025-10-30"

# ============================================================================
# META-INSIGHTS (About the analytical process itself)
# ============================================================================

meta_insights:
  
  - id: "meta_001"
    pattern: "Task tracking prevents analysis from skipping important areas"
    details: "Structured task management with explicit completion tracking ensures comprehensive coverage. Don't skip tasks even when pattern seems obvious."
    evidence: "7-task structure ensured all areas covered: overview, risk, individual analysis, factors, fundamentals, synthesis, trade recommendation"
    when_to_apply: "Use task structure for every comprehensive portfolio analysis"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.92
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "meta_002"
    pattern: "Thinking step before tool calls improves tool selection"
    details: "Explicitly stating 'why this step' before calling tools reduces wasted tool calls and ensures purposeful analysis."
    evidence: "Per-turn thinking structure led to efficient progression through analysis without redundant calculations"
    when_to_apply: "Require thinking step before every tool call"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.85
      created: "2025-10-30"
      last_used: "2025-10-30"
  
  - id: "meta_003"
    pattern: "Final synthesis must connect analysis to specific recommendations"
    details: "Don't just list findings - synthesize into coherent narrative showing: problems identified → evidence gathered → specific solution proposed."
    evidence: "Final answer connected all analysis threads: distress signals → concentration risk → defensive needs → specific trade addressing all three"
    when_to_apply: "Structure final recommendations as problem-evidence-solution"
    metadata:
      helpful: 1
      harmful: 0
      confidence: 0.88
      created: "2025-10-30"
      last_used: "2025-10-30"
"""

    # Initialize agent
    agent = BaseAgent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider="anthropic",  # Use OpenAI
        model="claude-haiku-4-5-20251001",  # Use GPT-4o for complex analysis
        max_iterations=100,  # Allow many iterations for thorough analysis
        print_mode=PrintMode.VERBOSE,
        plan_first=True,  # Create a plan before executing
        reasoning_effort="high",
        temperature=0.5
    )

    # Register analysis tools
    print("\n" + "="*80)
    print("REGISTERING PORTFOLIO ANALYSIS TOOLS")
    print("="*80)
    register_portfolio_analysis_tools(agent)

    # Run the agent
    print("\n" + "="*80)
    print("STARTING PORTFOLIO ANALYSIS")
    print("="*80)
    result = agent.run()


    return result


if __name__ == "__main__":
    main()
