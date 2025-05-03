from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SettingBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    is_encrypted: bool = False

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase):
    id: int
    date_added: datetime
    date_modified: datetime

    class Config:
        from_attributes = True
