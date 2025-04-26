from sqlalchemy import Column, String, Integer

from backend.database import Base

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    genre = Column(String)
    musicbrain_id = Column(String, unique=True)  # Unique identifier from MusicBrainz