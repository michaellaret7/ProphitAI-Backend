from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_verified: bool
    created_at: str
    updated_at: str

class UserSession(BaseModel):
    user: User
    access_token: str
    refresh_token: str