from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

class Note(BaseModel):
    """A notebook for agent execution."""

    title: str = Field(..., description="The title of the notebook")
    content: str = Field(..., description="The content of the notebook")
    created_at: datetime = Field(..., description="The date and time the notebook was created")
    updated_at: datetime = Field(..., description="The date and time the notebook was last updated")  

class Notebook(BaseModel):
    """A notebook for agent execution."""

    notes: List[Note] = Field(..., description="The notes in the notebook")