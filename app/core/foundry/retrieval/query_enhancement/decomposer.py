"""Query decomposition for improved vector database retrieval."""

from pydantic import BaseModel

from app.utils.choose_model_and_client import get_model_and_client
from .prompts import QUERY_DECOMPOSITION_PROMPT


class SubQuery(BaseModel):
    """A single decomposed sub-query."""

    sub_query: str


class SubQueries(BaseModel):
    """Collection of decomposed sub-queries."""

    sub_queries: list[SubQuery]


def decompose_query(query: str) -> SubQueries:
    """
    Decompose a complex query into focused sub-queries for vector search.

    Args:
        query: The user's original query.

    Returns:
        SubQueries containing the decomposed sub-queries.
    """
    model, client = get_model_and_client(provider="groq", model="openai-gpt-oss-120b")

    response = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": QUERY_DECOMPOSITION_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format=SubQueries,
    )

    return response.choices[0].message.parsed


if __name__ == "__main__":
    query = "Bank of Japan interest rate policy, yield curve control adjustments, and potential policy normalization timeline. Scandanavian rates Sweden Norway Denmark"
    sub_queries = decompose_query(query)
    print(sub_queries.model_dump_json(indent=4))
