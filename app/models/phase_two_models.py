from pydantic import BaseModel, Field
from typing import Dict, List, Any

# Pydantic models for phase two output validation
class SupportingMetrics(BaseModel):
    """Flexible schema for supporting metrics - allows any key-value pairs"""
    class Config:
        extra = "allow"

class StockRecommendation(BaseModel):
    ticker: str
    allocation: float
    reason_for_recommendation: str
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict)

class PhaseTwoRecommendations(BaseModel):
    total_stocks_analyzed: int
    recommendations: List[StockRecommendation]
    
