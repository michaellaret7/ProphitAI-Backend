import os
from dotenv import load_dotenv
import boto3

from app.db.core.models.market_data_models import *
from app.db.core.db_config import *
from app.utils.serialize_output import serialize_sqlalchemy_obj

session = MarketSession()

ticker = session.query(Ticker).filter(Ticker.ticker == "CWST").first()
print(serialize_sqlalchemy_obj(ticker))

session.close()