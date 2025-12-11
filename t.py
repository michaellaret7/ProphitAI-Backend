from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.core.db_config import UserSession
from app.db.core.models.market_data_models import Ticker, Price, DailyPrices
from app.db.core.models.user_data_models import User, Watchlist, WatchlistItem
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.time_utils import get_current_utc_time

with UserSession() as session:
    # Returns the User object
    user = session.query(User).join(Watchlist).join(WatchlistItem).filter(User.email == "michaellaret7@gmail.com").first()

    

