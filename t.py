from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User

session = UserSession()
user = session.query(User).filter(User.email == "mwl+clerk_test@gmail.com").first()

print(user.broker_account_id)
