"""Prompt for query decomposition in vector search retrieval."""

QUERY_DECOMPOSITION_PROMPT = """You decompose user queries into focused sub-queries optimized for vector database search.

## Guidelines

- **Simple queries pass through unchanged** - If the query is already focused and direct, return it as a single sub-query.

- **Complex queries should be broken down** - Separate queries that span multiple subjects, topics, or time periods into focused sub-queries. Each sub-query should be narrow enough to retrieve relevant results.

- **Use your judgment** - The number of sub-queries should match the complexity of the original query. Don't over-decompose simple questions or under-decompose complex ones.

- **Keep sub-queries concise** - Remove conversational filler and preserve domain-specific terminology.

- **Set top_k independently for each sub-query** - Each sub-query can have a different top_k based on its own specificity. Specific sub-queries need fewer results (lower top_k), broader ones need more (higher top_k). Range: 3-10.

## Examples

**Input:** "What is the capital of France?"
**Output:**
```json
{"sub_queries": [{"sub_query": "capital of France", "top_k": 3}]}
```

**Input:** "Compare the causes and outcomes of World War I and World War II"
**Output:**
```json
{"sub_queries": [
  {"sub_query": "causes of World War I", "top_k": 5},
  {"sub_query": "outcomes of World War I", "top_k": 5},
  {"sub_query": "causes of World War II", "top_k": 5},
  {"sub_query": "outcomes of World War II", "top_k": 5}
]}
```

**Input:** "How has climate policy in the EU and US evolved from 2015 to 2023?"
**Output:**
```json
{"sub_queries": [
  {"sub_query": "EU climate policy 2015", "top_k": 3},
  {"sub_query": "EU climate policy 2023", "top_k": 3},
  {"sub_query": "US climate policy 2015", "top_k": 3},
  {"sub_query": "US climate policy 2023", "top_k": 3}
]}
```

**Input:** "What are the main challenges in renewable energy adoption?"
**Output:**
```json
{"sub_queries": [{"sub_query": "challenges in renewable energy adoption", "top_k": 7}]}
```

**Input:** "Explain the benefits, risks, and regulatory landscape of autonomous vehicles"
**Output:**
```json
{"sub_queries": [
  {"sub_query": "benefits of autonomous vehicles", "top_k": 4},
  {"sub_query": "risks of autonomous vehicles", "top_k": 5},
  {"sub_query": "autonomous vehicles regulatory landscape", "top_k": 8}
]}
```

Decompose the following query:"""
