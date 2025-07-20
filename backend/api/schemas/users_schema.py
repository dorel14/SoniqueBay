from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: str
    password_hash: str
    is_active: bool = True

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    date_joined: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True