from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.core.db_config import UserSession
from app.db.core.models.market_data_models import Ticker, Price, DailyPrices
from app.db.core.models.user_data_models import User, Watchlist, WatchlistItem, Company, Portfolio
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.time_utils import get_current_utc_time

with UserSession() as session:
    # Returns the User object
    x = session.query(User).all()
    for u in x:
        print(serialize_sqlalchemy_obj(u))

        # if u.email == 'michael@prophitai.com':
        #     session.delete(u)
        #     session.commit()


        



    # company_id = user.company_id

    # company = session.query(Company).filter(Company.id == company_id).first()

    # print(serialize_sqlalchemy_obj(user))
    # print(serialize_sqlalchemy_obj(company))

    # user sync is necessary in clerk
    # change name to individual from Default Company 
    

