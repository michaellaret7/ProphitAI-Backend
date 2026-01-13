from pydantic import BaseModel, Field
from typing import List

class InsightsResponseModel(BaseModel):
    insights: List[str] = Field(..., description="List of insights about the portfolio")