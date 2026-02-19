# from collections import OrderedDict, defaultdict

# class LFUCache:
#     def __init__(self, capacity: int):
#         self.cap = capacity
#         self.cache = {}
#         self.key_freq = {}
#         self.freq_map = defaultdict(OrderedDict)
#         self.min_freq = 0
    
#     def _update(self, key: int):
#         freq = self.key_freq[key] # get the frequency of the key from key_freq eg [4(key), 1(freq)]

#         del self.freq_map[freq][key] # get rid of the key from the freq map (the number place in freq_map os the freq of the key) 

#         # if this was the minimum frequency bucket, move it to the next bucket and set the minimum frequency up 1
#         if not self.freq_map[freq] and freq == self.min_freq:
#             self.min_freq += 1
        
#         new_freq = freq + 1 # Now we are setting the frequency of the key_freq to +1 because we are updating it
#         self.key_freq[key] = new_freq
#         self.freq_map[new_freq][key] = None

#     def get(self, key: int) -> int:
#         if key not in self.cache:
#             return -1 
        
#         self._update(key)

#         return self.cache[key]

#     def put(self, key: int, value: int) -> None:
#         if self.cap <= 0:
#             return 

#         # If the key exists, set the new value to the key in the cache and then update the frequency tracking using _update
#         if key in self.cache:
#             self.cache[key] = value
#             self._update(key)
#             return 
        
#         if len(self.cache) >= self.cap:
#             # evicted_key, _ is because the values in the ordered dict are (key, None)
#             evict_key, _ = self.freq_map[self.min_freq].popitem(last=False) # get the lowest frequency key in the list, pop the least freq used key from the list
#             del self.cache[evict_key]
#             del self.key_freq[evict_key]
        
#         # insert new item 
#         self.cache[key] = value
#         self.key_freq[key] = 1 # set the freq to one because it has now been used once 
#         self.min_freq = 1 # reset minimum frequency because we now have a new item thats the smallest freq
#         self.freq_map[1][key] = None

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker


session = MarketSession()

tickers = session.query(Ticker).filter(
    Ticker.sector == 'equity_sector_information_technology',
    Ticker.market_cap < 100_000_000_000
).all()

for t in tickers:
    print(t.ticker)
