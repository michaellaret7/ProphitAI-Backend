from app.db.core.db_config import MarketSession, UserSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.user_data_models import User
from app.utils.serialize_output import serialize_sqlalchemy_obj

with UserSession() as session:
    users = session.query(User).all()
    for user in users:
        print(serialize_sqlalchemy_obj(user))
        print("--------------------------------")

from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())