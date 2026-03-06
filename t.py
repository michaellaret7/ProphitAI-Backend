import time
from app.repositories.user.broker import resolve_snaptrade_credentials, get_snaptrade_broker

EMAIL = "michaellaret7@gmail.com"

creds = resolve_snaptrade_credentials(email=EMAIL)
user_id = creds["snaptrade_user_id"]
user_secret = creds["snaptrade_user_secret"]
account_id = creds["snaptrade_account_id"]

broker = get_snaptrade_broker()

start_time = time.time()

orders = broker.get_orders(
    user_id=user_id,
    user_secret=user_secret,
    account_id=account_id,
    start_date="2026-02-15",
    end_date="2026-03-06",
)

portfolio = broker.get_portfolio(
    user_id=user_id,
    user_secret=user_secret,
    account_id=account_id,
)

elapsed = time.time() - start_time

print(f"\nFetched {len(orders)} orders in {elapsed:.2f}s\n")
for order in orders:
    print(f"  {order.type:<4} | {order.ticker:<6} | {order.units:>8.2f} units @ ${order.price:>9.2f} | ${order.amount:>10.2f} | {order.trade_date} | {order.asset_type}")
print(portfolio)