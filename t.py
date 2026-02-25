from app.db.core.models.user_data_models import User, TradeProposal
from app.db.core.db_config import UserSession
from app.utils.serialize_output import serialize_sqlalchemy_obj

with UserSession() as session:
    user = session.query(User).filter(User.email == "michaellaret7@gmail.com").first()

    print(serialize_sqlalchemy_obj(user))

    print('id: ', user.id)
    print('clerk_id: ', user.clerk_id)
    print('broker_account_id: ', user.broker_account_id)
    print('email: ', user.email)
