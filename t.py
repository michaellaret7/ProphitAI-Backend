from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User

session = UserSession()
u = session.query(User).filter(User.email == "michael@prophitai.com").first()
print(u)
session.close()