"""Deep Research Agent — exhaustive multi-source research on any query.

Instantiates the Atlas Agent with a custom deep-research system prompt,
wires up all research/news/macro tools, and runs in plan-first mode so
the planner decomposes the query into parallel research streams that
worker agents execute independently.

Usage:
    python -m packages.atlas.tests.test_deep_research

    Or directly:
    python packages/atlas/tests/test_deep_research.py
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_shared.time_utils import get_utc_date_str

# ================================
# --> Research tool imports
# ================================
from prophitai_tools.research.macro_research import macro_research_search
from prophitai_tools.research.earnings_calls import earnings_call_search
from prophitai_tools.research.credit_research import credit_research_search
from prophitai_tools.research.economics_research import economics_research_search
from prophitai_tools.research.theory_research import theory_research
from prophitai_tools.research.tax_research import tax_research_search

# ================================
# --> News tool imports
# ================================
from prophitai_tools.news.general_news import general_news
from prophitai_tools.news.ticker_news import get_ticker_news
from prophitai_tools.news.press_releases import get_press_releases

# ================================
# --> Macro data tool imports
# ================================
from prophitai_tools.macro.commodity_prices import commodity_prices
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators

# ================================
# --> Ticker info tool imports
# ================================
from prophitai_tools.ticker.info.description import get_ticker_info, get_etf_info
from prophitai_tools.ticker.info.peers import get_ticker_peers
from prophitai_tools.ticker.info.ratings import get_stock_ratings
from prophitai_tools.ticker.info.institutional_holders import get_institutional_holders
from prophitai_tools.ticker.info.product_segmentation import get_product_segmentation

# ================================
# --> Ticker analytics tool imports
# ================================
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.technicals import ticker_technicals

# ================================
# --> Fundamentals tool imports
# ================================
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.estimates import get_analyst_estimates
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.fundamentals.price_target import get_price_target_data

# ================================
# --> Screener tool imports
# ================================
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.screener.etf_screener import etf_screener

# ================================
# --> Sector tool imports
# ================================
from prophitai_tools.ticker.info.sectors import get_sector_industries, get_group_tickers


# ==============================================================================
# --> All research-relevant tools
# ==============================================================================

DEEP_RESEARCH_TOOLS = [
    # Research (RAG-powered document search)
    macro_research_search,
    earnings_call_search,
    credit_research_search,
    economics_research_search,
    theory_research,
    tax_research_search,
    # News & market intelligence
    general_news,
    get_ticker_news,
    get_press_releases,
    # Macro data
    commodity_prices,
    us_treasury_rates,
    macro_indicators,
    # Ticker info
    get_ticker_info,
    get_etf_info,
    get_ticker_peers,
    get_stock_ratings,
    get_institutional_holders,
    get_product_segmentation,
    # Ticker analytics
    ticker_performance,
    ticker_risk,
    ticker_factors,
    ticker_technicals,
    # Fundamentals
    get_ticker_fundamental_data,
    get_analyst_estimates,
    get_ratios_ttm,
    get_price_target_data,
    # Screeners
    equity_screener,
    etf_screener,
    # Sectors
    get_sector_industries,
    get_group_tickers,
]


# ==============================================================================
# --> Deep research system prompt
# ==============================================================================

def build_deep_research_prompt() -> str:
    """Build the deep research agent system prompt.

    Deferred tool descriptions are appended separately by Agent.__init__.
    """

    date = get_utc_date_str()

    return f"""You are a senior research analyst at a top-tier institutional investment firm.
Your mandate is to produce exhaustive, publication-quality research on any query you receive.
You have the analytical rigor of a Goldman Sachs strategist, the intellectual curiosity of a
Renaissance Technologies quant, and the thoroughness of a Congressional Research Service report.

Today's date is {date}.

<research_philosophy>
## Research Philosophy

You do not skim. You do not summarize prematurely. You go DEEP.

Every claim must be grounded in data you retrieved through your tools. When you encounter
conflicting signals, you don't pick one — you present the tension and explain what it means.
When the data is ambiguous, you say so and explain the range of interpretations.

Your research is structured around the principle of **convergent evidence**: a thesis is only
as strong as the number of independent data sources that support it. One data point is an
observation. Two is a pattern. Three or more is a signal worth acting on.
</research_philosophy>

<execution_strategy>
## Execution Strategy

You operate in plan-first mode. This means:

1. **Decompose the query** into 4-8 independent research streams
2. **Deploy workers in parallel** — each stream gets its own focused worker(s)
3. **Cross-reference all findings** after workers complete
4. **Synthesize** a comprehensive research report

### Research Stream Design

For any research query, consider these dimensions and include ALL that are relevant:

**Quantitative Streams:**
- Performance & returns analysis (ticker_performance, ticker_risk)
- Fundamental analysis (financial statements, ratios, estimates, price targets)
- Technical analysis (momentum, trend, volatility, volume indicators)
- Factor exposure (value, growth, momentum, quality, size, volatility factors)
- Macro environment (rates, commodities, economic indicators)

**Qualitative Streams:**
- Management commentary (earnings call transcripts — ALWAYS search these)
- Analyst sentiment (ratings, price targets, estimate revisions)
- News & catalysts (general news, ticker-specific news, press releases)
- Institutional research (macro research, credit research, economics research)
- Competitive landscape (peers, sector composition, market positioning)
- Institutional ownership (who's buying, who's selling, concentration)

**Contextual Streams:**
- Sector & industry dynamics (sector performance, industry trends)
- Macro regime (rate environment, inflation trajectory, growth cycle phase)
- Investment theory (relevant frameworks from academic finance)

### Worker Deployment Rules

- Deploy 3-5 workers PER plan task to maximize parallelism
- Each worker gets a NARROW, SPECIFIC task — never combine unrelated research
- Workers that need ticker data should receive ALL relevant tickers in one call (batch)
- Workers that search documents should use DETAILED natural language queries, NOT keywords
- Every worker touching company analysis MUST search earnings calls
- Every worker touching macro MUST pull both institutional research AND raw indicator data
- Include today's date ({date}) in every worker task description for context

### Query Formulation for Document Search Tools

These tools use semantic search with embeddings. Good queries are detailed sentences:

GOOD: "What is Apple's management guidance on AI infrastructure spending and capital expenditure plans for fiscal year 2026?"
BAD: "AAPL capex AI"

GOOD: "Federal Reserve interest rate policy outlook and expected path of monetary tightening through 2026"
BAD: "Fed rates"

GOOD: "Impact of rising commodity prices on corporate profit margins in the consumer staples sector"
BAD: "commodity margins"
</execution_strategy>

<synthesis_protocol>
## Synthesis Protocol

After all workers complete, you MUST follow this exact sequence:

1. **Retrieve all notes** — call retrieve_notes with no filter to get the full table of contents
2. **Read every note** — call retrieve_notes with each title to read the full content
3. **Think deeply** — use the think tool to:
   a. Map out all key findings across streams
   b. Identify convergent signals (multiple sources agreeing)
   c. Flag divergent signals (sources contradicting each other)
   d. Identify gaps in the research that need addressing
   e. Build the narrative arc of your report
4. **Write the report** — comprehensive, structured, data-rich

### Report Structure

Your final output must include ALL of the following sections (adapt headers to fit the query):

**Executive Summary**
2-3 paragraphs covering the key thesis, supporting evidence, and primary risks.
This should be dense with specific numbers and findings.

**Quantitative Analysis**
All hard data: performance metrics, fundamental ratios, technical signals,
factor exposures, valuations. Use tables where appropriate.

**Qualitative Analysis**
Management commentary themes, analyst sentiment, news catalysts,
competitive positioning, institutional research insights.

**Macro Context**
Rate environment, economic cycle positioning, commodity trends,
and how they affect the subject of research.

**Risk Assessment**
Bear case scenarios, key risk factors, what could go wrong,
sensitivity to macro changes. Be specific about magnitudes.

**Conclusion & Outlook**
Synthesized view bringing together all streams. What does the
convergence of evidence suggest? What conviction level is warranted?

### Quality Standards

- Every claim backed by a specific data point from your tools
- All percentages, ratios, and metrics reported with precision (no rounding)
- Contradictions between sources explicitly addressed
- Time periods clearly stated for all data
- Comparison to benchmarks or peers where relevant
- Tables for any comparison of 3+ items
</synthesis_protocol>

<available_tools>
## Available Worker Tools

Workers have access to all available tools via deferred registration.
They will use `register_tools` to load the tools they need for their task.
</available_tools>

<orchestration_rules>
## Orchestration Rules

- ALWAYS use the think tool before deploying workers to plan your research streams
- Deploy independent workers in PARALLEL — never sequentially when tasks don't depend on each other
- After all workers finish, ALWAYS call retrieve_notes before synthesizing
- Use the think tool again after reading notes to cross-reference before writing
- If a worker fails, diagnose why and retry with adjusted parameters
- Never skip a research dimension just because it seems tangential — thoroughness is your edge
- When in doubt, deploy MORE workers rather than fewer
</orchestration_rules>
"""


# ==============================================================================
# --> Deep Research Agent class
# ==============================================================================

class DeepResearchAgent:
    """Exhaustive research agent that decomposes queries into parallel research streams.

    Uses plan-first mode to:
    1. Generate a structured research plan
    2. Deploy parallel worker agents for each stream
    3. Cross-reference all findings
    4. Produce a comprehensive research report
    """

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4.6",
        print_mode: PrintMode = PrintMode.VERBOSE,
        max_iterations: int = 150,
    ) -> None:
        system_prompt = build_deep_research_prompt()

        self._agent = Agent(
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            deferred_tools=DEEP_RESEARCH_TOOLS,
            system_prompt=system_prompt,
        )

    def run(self, query: str):
        """Execute deep research on the given query.

        Args:
            query: The research question or topic to investigate.

        Returns:
            AgentResponse with the full research report in .answer
        """
        return self._agent.run(
            user_message=query,
            plan_first=True,
        )


# ==============================================================================
# --> Test execution
# ==============================================================================

def test_deep_research():
    """Run a real deep research query through the agent."""

    agent = DeepResearchAgent(
        model="anthropic/claude-sonnet-4.6",
        print_mode=PrintMode.PRODUCTION,
        max_iterations=150,
    )

    query = (
        "I am a corporate strategist at GameStop (GME). We have significant cash reserves "
        "and the board is actively evaluating M&A acquisition targets to diversify revenue, "
        "accelerate digital transformation, and deploy capital strategically. "
        "\n\n"
        "Conduct an exhaustive acquisition target analysis. The deliverable must be a "
        "RANKED LIST OF SPECIFIC ACQUISITION CANDIDATES with full due-diligence profiles. "
        "\n\n"
        "1) GAMESTOP BASELINE: Analyze GameStop's current financial health — cash position, "
        "balance sheet, revenue trends, margin profile. Determine our realistic acquisition "
        "capacity (cash, debt capacity, equity as currency). Identify core competencies "
        "and the strategic gaps that an acquisition should fill. "
        "\n\n"
        "2) STRATEGIC ADJACENCIES: Given GameStop's business (physical retail, e-commerce, "
        "collectibles, Bitcoin/crypto treasury), map out the highest-value adjacencies — "
        "gaming studios, esports platforms, digital marketplaces, fintech/crypto infrastructure, "
        "collectibles/trading card companies, logistics/fulfillment, or other verticals. "
        "Rank each adjacency by strategic synergy, market size, and acquisition feasibility. "
        "\n\n"
        "3) DEEP CANDIDATE ANALYSIS: This is the most important section. Identify 3-6 "
        "specific publicly traded companies that GameStop could realistically acquire, and "
        "conduct a DEEP due-diligence analysis on each one. This is NOT a surface-level screen. "
        "For EACH candidate I need: full financial profile (revenue, margins, growth trajectory, "
        "balance sheet health, cash flow generation), enterprise value and what a realistic "
        "acquisition premium looks like, a thorough strategic rationale explaining exactly HOW "
        "this company fills GameStop's gaps and what the combined entity looks like post-merger, "
        "management quality and cultural compatibility, competitive moat and market position "
        "within their industry, and key risks specific to acquiring THIS company. "
        "Treat each candidate like you're writing a mini investment memo — I should be able "
        "to walk into a board meeting and present any one of these as a serious proposal. "
        "\n\n"
        "4) MACRO & M&A ENVIRONMENT: Evaluate the current deal environment — interest rates, "
        "credit conditions, regulatory climate, and sector valuation multiples. Buyer's or "
        "seller's market? What comparable transactions have occurred recently in gaming, "
        "digital media, and retail tech? "
        "\n\n"
        "5) DEAL RISK PROFILES: For each top candidate, assess integration complexity, "
        "cultural fit, overpayment risk, regulatory hurdles, and post-acquisition impact "
        "on GameStop's balance sheet, cash reserves, and earnings profile. "
        "\n\n"
        "6) MARKET SENTIMENT: What are analysts and institutional holders saying about "
        "GameStop's capital allocation? Any activist pressure for specific uses of cash? "
        "What is the market pricing in? "
        "\n\n"
        "The final output must be a board-ready report with DEEP PROFILES on each "
        "acquisition candidate — not a screening list, but full investment memos. Rank them "
        "by strategic fit and feasibility, with specific names, tickers, valuations, "
        "and a clear narrative on why each company belongs in GameStop's portfolio. "
        "Every recommendation must be backed by data."
    )

    result = agent.run(query)

    print(result.answer)


if __name__ == "__main__":
    test_deep_research()
