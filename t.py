from app.brokers.snaptrade.broker import SnapTradeBroker

broker = SnapTradeBroker()

user_id = "TEST_USER_1"
user_secret = "7ff3ee67-bf0f-41c0-9d04-cb1de522edfe"
account_id = "dff012b2-21ea-4997-9819-5f92f1fbf5f5"

order = broker.buy(user_id=user_id, user_secret=user_secret, account_id=account_id, symbol="CRWV", units=1)
print(order)