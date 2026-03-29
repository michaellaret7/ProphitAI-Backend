"""Prompts for query enhancement in vector search retrieval."""

QUERY_DECOMPOSITION_PROMPT = """You decompose user queries into focused sub-queries for vector database search.

## CRITICAL RULES

1. **MINIMUM 2 sub-queries** - Always return at least 2 sub-queries. For simpler queries, create different angles or phrasings to maximize retrieval coverage.

2. **MAXIMUM 10 sub-queries** - Never exceed 10 sub-queries.

## Decomposition Approach

- Identify the distinct entities, topics, and aspects in the query
- Create sub-queries that each target a specific, searchable concept
- More complex queries with multiple entities or aspects warrant more sub-queries
- Simpler queries should still have multiple angles to improve retrieval
- Use your judgment to determine the appropriate number based on query complexity
- Remove conversational filler, preserve domain terminology
- Each sub-query should be specific and directly searchable

## Examples

**2 SUB-QUERIES (simple query - minimum):**
Input: "What is the Federal Reserve's interest rate outlook for 2026?"
Output: {"sub_queries": [
  {"sub_query": "Federal Reserve interest rate policy decisions 2026"},
  {"sub_query": "Fed funds rate outlook and FOMC projections 2026"}
]}

**2 SUB-QUERIES (simple query - minimum):**
Input: "How is Japan approaching monetary policy normalization?"
Output: {"sub_queries": [
  {"sub_query": "Bank of Japan monetary policy normalization timeline"},
  {"sub_query": "BOJ interest rate policy and yield curve control changes"}
]}

**3 SUB-QUERIES (two entities):**
Input: "Compare Riksbank and Norges Bank rate decisions"
Output: {"sub_queries": [
  {"sub_query": "Riksbank Sweden interest rate decisions and policy outlook"},
  {"sub_query": "Norges Bank Norway interest rate decisions and policy outlook"},
  {"sub_query": "Scandinavian central bank monetary policy comparison"}
]}

**4 SUB-QUERIES (three aspects):**
Input: "What are the benefits, risks, and regulations for autonomous vehicles?"
Output: {"sub_queries": [
  {"sub_query": "benefits and advantages of autonomous vehicles"},
  {"sub_query": "risks and safety concerns of autonomous vehicles"},
  {"sub_query": "autonomous vehicles regulations and legal framework"},
  {"sub_query": "self-driving car industry outlook and adoption challenges"}
]}

**5 SUB-QUERIES (two entities × two aspects):**
Input: "Compare revenue growth and profit margins for Apple and Microsoft"
Output: {"sub_queries": [
  {"sub_query": "Apple revenue growth and sales performance"},
  {"sub_query": "Apple profit margins and profitability trends"},
  {"sub_query": "Microsoft revenue growth and sales performance"},
  {"sub_query": "Microsoft profit margins and profitability trends"},
  {"sub_query": "Apple versus Microsoft financial performance comparison"}
]}

**7 SUB-QUERIES (three entities × two aspects):**
Input: "Compare monetary policy stance and inflation outlook for Fed, ECB, and BOJ"
Output: {"sub_queries": [
  {"sub_query": "Federal Reserve monetary policy stance and rate decisions"},
  {"sub_query": "Federal Reserve inflation outlook and price stability goals"},
  {"sub_query": "ECB monetary policy stance and rate decisions"},
  {"sub_query": "ECB eurozone inflation outlook and price targets"},
  {"sub_query": "Bank of Japan monetary policy stance and rate decisions"},
  {"sub_query": "Bank of Japan inflation outlook and price stability"},
  {"sub_query": "global central bank policy divergence comparison Fed ECB BOJ"}
]}

Decompose the following query:"""
