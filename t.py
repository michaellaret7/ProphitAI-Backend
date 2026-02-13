"""Re-run monitor for all portfolios belonging to michaellaret7@gmail.com."""
import os
from typing import OrderedDict
from app.core.foundry.retrieval.search.hybrid import HybridSearch
from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import User, Portfolio
from app.db.jobs.portfolio.batch_monitor import BatchMonitorPortfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj
from langfuse import get_client, observe
from app.core.foundry.embeddings.pinecone_manager import PineconeManager

from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = abs(capacity) # set capacity as positive integer
        self.cache = OrderedDict() # set empty ordered dictionary to store the cache

    def get(self, key: int) -> int:
        if key in self.cache:
            value = self.cache[key] # Get the value of the key if its in the cache

            self.cache.move_to_end(key) # Move the item to the end of the list for most recently used

            return value 
        else:
            return -1 # return -1 if the key is not in the cache
        
    def put(self, key: int, value: int) -> None:
        if key in self.cache: # check if the key exists in cache and update it by moving it to the end
            self.cache[key] = value # update the value of the key in the cache 
            self.cache.move_to_end(key) # move the key to the end of the list for most recently used
        else:
            self.cache[key] = value # add the key-value pair to the cache
            self.cache.move_to_end(key) # move the key to the end of the list for most recently used
        
        if len(self.cache) > self.capacity: # check if the cache is over the capacity
            self.cache.popitem(last=False) # remove the least recently used item from the cache (aka beginning of the list)





'''
PROBLEM:
Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.

Implement the LRUCache class:

LRUCache(int capacity) Initialize the LRU cache with positive size capacity.
int get(int key) Return the value of the key if the key exists, otherwise return -1.
void put(int key, int value) Update the value of the key if the key exists. Otherwise, add the key-value pair to the cache. If the number of keys exceeds the capacity from this operation, evict the least recently used key.
The functions get and put must each run in O(1) average time complexity.

 

Example 1:

Input
["LRUCache", "put", "put", "get", "put", "get", "put", "get", "get", "get"]
[[2], [1, 1], [2, 2], [1], [3, 3], [2], [4, 4], [1], [3], [4]]
Output
[null, null, null, 1, null, -1, null, -1, 3, 4]

Explanation
LRUCache lRUCache = new LRUCache(2);
lRUCache.put(1, 1); // cache is {1=1}
lRUCache.put(2, 2); // cache is {1=1, 2=2}
lRUCache.get(1);    // return 1
lRUCache.put(3, 3); // LRU key was 2, evicts key 2, cache is {1=1, 3=3}
lRUCache.get(2);    // returns -1 (not found)
lRUCache.put(4, 4); // LRU key was 1, evicts key 1, cache is {4=4, 3=3}
lRUCache.get(1);    // return -1 (not found)
lRUCache.get(3);    // return 3
lRUCache.get(4);    // return 4
'''