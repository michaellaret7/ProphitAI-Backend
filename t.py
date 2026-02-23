import os
from app.brokers.alpaca_broker import ProphitBroker
from dotenv import load_dotenv
load_dotenv()

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User

broker = ProphitBroker(sandbox=True)

id_broker_account = 'd27aa8c2-5931-499b-bdfa-05c47b07ad70'

acct_info = broker.accounts.client.get_account_by_id(account_id=id_broker_account)
acct = broker.accounts.get_account(id_broker_account)

print(acct['buying_power'])

acct = broker.get_positions(id_broker_account)
print(acct)


session = UserSession()
user = session.query(User).filter(User.email == "michaellaret7@gmail.com").first()
print(user.broker_account_id)
session.close()




