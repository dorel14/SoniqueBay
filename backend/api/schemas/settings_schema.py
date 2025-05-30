from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .base_schema import TimestampedSchema

class SettingBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    is_encrypted: bool = False

class SettingCreate(SettingBase):
    pass

class Setting(SettingBase, TimestampedSchema):
    id: int
    date_added: datetime
    date_modified: datetime

    class Config:
        from_attributes = True
