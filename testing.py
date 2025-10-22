from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from typing import Protocol

# list = ['SPIB', 'STOT', 'PRIV', 'TOTL', 'HYBL']

# session = MarketSession()
# for ticker in list:
#     x = session.query(Ticker).filter(Ticker.ticker == ticker).first()
#     if x == None:
#         print(f"Ticker {ticker} not found")
#     else:
#         print(f"Ticker {ticker} found")
# session.close()

# Define the protocol
class Trade(Protocol):
    def execute(self) -> None:
        ...
    def cancel(self) -> None:
        ...

# These classes DON'T inherit from Drawable
class BuyOrder:
    def execute(self) -> None:
        print("Executing buy order")
    def cancel(self) -> None:
        print("Canceling buy order")

class SellOrder:
    def execute(self) -> None:
        print("Executing sell order")
    def cancel(self) -> None:
        print("Canceling sell order")

# This function accepts anything "Drawable"
def render(shape: Trade) -> None:
    shape.execute()

# Both work!
render(BuyOrder())  # ✓
render(SellOrder())  # ✓