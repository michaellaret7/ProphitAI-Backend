"""Re-run monitor for all portfolios belonging to michaellaret7@gmail.com."""
import os
from app.core.foundry.retrieval.search.hybrid import HybridSearch
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio
from app.db.jobs.portfolio.batch_monitor import BatchMonitorPortfolio

from langfuse import get_client, observe
from app.core.foundry.embeddings.pinecone_manager import PineconeManager

@observe(name="test")
def retrieve_context() -> str:
    hybrid_search = HybridSearch(use_rerank=True, enhanced=True)

    results = hybrid_search.search(
        query="Scandanavia central bank and interest rates. Japanese central bank and interest rates.",
        namespace="macro_research",
        top_k=3,
    )

    return [result.metadata["text"] for result in results]

print(retrieve_context())