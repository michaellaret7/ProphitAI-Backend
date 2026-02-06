from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj

session = UserSession()

# 1. Get the RIA
ria = session.query(User).filter(User.email == 'michaellaret7@gmail.com').first()
print(f"RIA: {ria.first_name} {ria.last_name} (role: {ria.role})")

# 2. Get all portfolios for the RIA's clients (single query via join)
client_portfolios = session.query(Portfolio).join(
    User, Portfolio.user_id == User.id
).filter(
    User.handler_id == ria.id,
    Portfolio.is_current == True
).all()

for p in client_portfolios:
    print(f"  Portfolio: {p.name} | Client ID: {p.user_id} | Client Email: {p.user.email} | NAV: {p.nav}")
    for item in p.items:
        print(f"    Item: {item.ticker} | Allocation: {item.allocation} | Num Shares: {item.num_shares}")

session.close()
