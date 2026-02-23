import os
from app.brokers.alpaca_broker import ProphitBroker
from dotenv import load_dotenv
load_dotenv()

broker = ProphitBroker(sandbox=True)

journal = broker.journal_cash(os.getenv("ALPACA_FIRM_ACCOUNT_ID"), 'd27aa8c2-5931-499b-bdfa-05c47b07ad70', 1000)
print(journal)

account = broker.accounts.client.get_account_by_id(account_id='d27aa8c2-5931-499b-bdfa-05c47b07ad70')
print(account)

