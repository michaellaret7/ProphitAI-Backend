"""Re-run monitor for all portfolios belonging to michaellaret7@gmail.com."""
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio
from app.db.jobs.portfolio.batch_monitor import BatchMonitorPortfolio

session = UserSession()
user = session.query(User).all()

for u in user:
    print(u.email)
    print(u.portfolios)
    for p in u.portfolios:
        print(p.name)


session.close()
