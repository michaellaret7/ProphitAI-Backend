from pydantic import BaseModel
from typing import Optional

class UserProfile(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    organization_id: str

class LoginResponse(BaseModel):
    message: str
    user: UserProfile
    redirect_url: str
