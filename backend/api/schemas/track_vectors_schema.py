from pydantic import BaseModel, ConfigDict
from typing import List

class TrackVectorBase(BaseModel):
    track_id: int
    vector_data: List[float]

class TrackVectorCreate(TrackVectorBase):
    pass

class TrackVector(TrackVectorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)