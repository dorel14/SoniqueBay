from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra='allow'
    )

class TimestampedSchema(BaseModel):
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

    @field_validator('date_added', 'date_modified', mode='before')
    @classmethod
    def convert_datetime(cls, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        return datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        return None
        return None
