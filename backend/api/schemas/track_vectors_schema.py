from pydantic import BaseModel
from typing import List

class TrackVectorBase(BaseModel):
    track_id: int
    vector_data: List[float]

class TrackVectorCreate(TrackVectorBase):
    pass

class TrackVector(TrackVectorBase):
    id: int

    class Config:
        from_attributes = True