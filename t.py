from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio, PortfolioItem

user_session = UserSession()

user = user_session.query(User).filter(User.email == "michael@prophitai.com").first()

print(user.clerk_id)

user_session.close()