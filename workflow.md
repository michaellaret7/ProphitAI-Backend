### RIA Logs on to the platform for the first time

RIA logs in and registers as a user and identifies with a company 
    --> Create user func (role='ria)
    --> Create company func 
    --> Set the user variables 

RIA then logs clients and their portfolios 
    --> The ria creates a portfolio and a user when registering 

The RIA then sees all of the portfolios for their clients   
    --> need to create a func for this 

```python
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
```


