from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class PriceData(BaseModel):
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
