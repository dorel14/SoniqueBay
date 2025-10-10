from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ListeningHistoryBase(BaseModel):
    user_id: int
    track_id: int

class ListeningHistoryCreate(ListeningHistoryBase):
    pass

class ListeningHistory(ListeningHistoryBase):
    id: int
    date_listened: datetime

    model_config = ConfigDict(from_attributes=True)