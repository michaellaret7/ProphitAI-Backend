from app.core.atlas.agents.orchestrator_agent import OrchestratorAgent

prompt = """
You are a senior equity research analyst conducting a comprehensive deep-dive on Snowflake Inc. (SNOW). Your objective is to produce an institutional-quality research report covering the general overview of the business and its forward outlook.

## Research Mandate

Produce a thorough, balanced, and data-driven analysis of Snowflake. The report should be suitable for an investment committee review — no fluff, no surface-level summaries. Back every claim with data where possible.

## Required Research Sections

### 1. Company Overview & Business Model
- What does Snowflake do at its core? Explain the Data Cloud platform, its architecture (separation of storage and compute), and why it matters.
- Revenue model: consumption-based pricing — how it works, what drives usage, and the implications for revenue predictability vs. traditional SaaS subscription models.
- Key products and platform capabilities: data warehousing, data lake, data sharing/marketplace, Snowpark (developer platform), Cortex AI (LLM/ML features), Streamlit (app development).
- How does Snowflake fit within the modern data stack? Who are the adjacent players they integrate with vs. compete against?

### 2. Market Opportunity & TAM
- Size and growth trajectory of the cloud data platform market.
- Snowflake's current penetration of its addressable market.
- Expansion vectors: AI/ML workloads, application development (Snowpark/Streamlit), data sharing & marketplace, government/regulated industries, international expansion.
- How is the AI wave specifically impacting Snowflake's TAM — both positively (more data processing demand) and as a risk (customers building on other platforms)?

### 3. Competitive Landscape
- Direct competitors: Databricks, Google BigQuery, Amazon Redshift, Azure Synapse, and emerging players.
- Snowflake's differentiation — what is their actual moat? Multi-cloud neutrality, ease of use, data sharing network effects, or something else?
- Where is Snowflake losing deals and to whom? What are the knock against them in competitive bake-offs?
- The Databricks rivalry specifically — how do their strategies differ, where do they overlap, and who is winning in AI/ML workloads?

### 4. Financial Deep-Dive
- Revenue growth trends (product revenue specifically), remaining performance obligations (RPO), and net revenue retention rate (NRR).
- Path to profitability: operating margins, free cash flow generation, stock-based compensation as a percentage of revenue.
- Customer metrics: total customers, customers spending $1M+, Fortune 500 penetration.
- Consumption model dynamics: how does macro/IT budget pressure affect consumption patterns? Analyze any optimization headwinds.
- Capital allocation: how are they deploying capital? Any M&A strategy?

### 5. Management & Leadership
- CEO Sridhar Ramaswamy (took over from Frank Slootman) — what has changed in strategy, culture, and execution since the transition?
- Key executives and their backgrounds.
- Insider ownership and alignment with shareholders.
- What is management's stated strategic vision for the next 3-5 years?

### 6. Risks & Bear Case
- Consumption-based revenue is inherently less predictable — what happens in a prolonged IT spending downturn?
- Cloud provider competition: AWS, Azure, and GCP all have native offerings. Could they squeeze Snowflake out over time?
- AI disruption risk: could new AI-native data platforms or LLM-based query tools reduce the need for traditional data warehousing?
- Valuation risk: is the current multiple justified by the growth trajectory?
- Key person risk, execution risk on AI strategy, and customer concentration.

### 7. Bull Case & Growth Catalysts
- AI as a tailwind: Cortex AI, LLM functions, vector search — how does Snowflake position as the data backbone for enterprise AI?
- Network effects from the data marketplace and data sharing capabilities.
- International expansion runway.
- Potential for margin expansion as the business scales and consumption grows.
- Product velocity and developer adoption trends.

### 8. Outlook & Forward View
- Consensus revenue and earnings estimates vs. what the data suggests.
- What are the key inflection points or catalysts to watch over the next 12-18 months?
- Is Snowflake a share gainer or share loser in the current environment?
- What would need to be true for Snowflake to significantly outperform or underperform expectations?
- Synthesize a balanced forward outlook: where is this business headed?

## Output Requirements
- Be specific and data-driven. Use actual numbers, growth rates, and metrics wherever possible.
- Clearly separate facts from opinion/analysis.
- Flag any areas where data is stale or unavailable and note what you could not verify.
- Write for a sophisticated audience — no need to explain basic financial concepts.
- Conclude with a concise executive summary that synthesizes the full analysis into key takeaways.
"""

orchestrator = OrchestratorAgent(
    task=prompt,
    provider="anthropic",
    model="claude-opus-4-6",
    plan_first=True,
    max_iterations=250
)

response = orchestrator.run()
print(response)