"""Re-run monitor for all portfolios belonging to michaellaret7@gmail.com."""
import os
from app.core.foundry.retrieval.search.hybrid import HybridSearch
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio
from app.db.jobs.portfolio.batch_monitor import BatchMonitorPortfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj
from langfuse import get_client, observe
from app.core.foundry.embeddings.pinecone_manager import PineconeManager

user = UserSession()

ml = user.query(User).filter(User.email == "michaellaret7@gmail.com").first()
print(serialize_sqlalchemy_obj(ml))


user.close()