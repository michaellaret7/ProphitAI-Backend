"""Query decomposition for improved vector database retrieval."""

from pydantic import BaseModel

from prophitai_shared import build_client
from .prompts import QUERY_DECOMPOSITION_PROMPT

# Reason: GPT models support `response_format=PydanticModel` via OpenRouter's
# JSON-schema mode. Fast/cheap slug used here since decomposition is bounded.
DECOMPOSER_MODEL = "openai/gpt-5.4"


class SubQuery(BaseModel):
    """A single decomposed sub-query."""

    sub_query: str


class SubQueries(BaseModel):
    """Collection of decomposed sub-queries."""

    sub_queries: list[SubQuery]


def decompose_query(query: str) -> SubQueries:
    """Decompose a complex query into focused sub-queries for vector search.

    Args:
        query: The user's original query.

    Returns:
        SubQueries containing the decomposed sub-queries.
    """
    client, model = build_client(DECOMPOSER_MODEL)

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": QUERY_DECOMPOSITION_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format=SubQueries,
    )

    parsed = completion.choices[0].message.parsed

    if parsed is None:
        raise RuntimeError(f"Decomposer returned no structured output (model={model})")

    return parsed


if __name__ == "__main__":
    query = "Bank of Japan interest rate policy, yield curve control adjustments, and potential policy normalization timeline. Scandanavian rates Sweden Norway Denmark"
    sub_queries = decompose_query(query)
    print(sub_queries.model_dump_json(indent=4))
