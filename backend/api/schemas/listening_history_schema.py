from pydantic import BaseModel
from datetime import datetime

class ListeningHistoryBase(BaseModel):
    user_id: int
    track_id: int

class ListeningHistoryCreate(ListeningHistoryBase):
    pass

class ListeningHistory(ListeningHistoryBase):
    id: int
    date_listened: datetime

    class Config:
        from_attributes = True