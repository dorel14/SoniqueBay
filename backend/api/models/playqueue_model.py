"""
Modèle SQLAlchemy pour la playqueue.
Stocke la file de lecture en base de données PostgreSQL.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class PlayQueueTrack(Base):
    __tablename__ = "playqueue_tracks"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to track
    track = relationship("Track", back_populates="playqueue_entries")

class PlayQueue(Base):
    __tablename__ = "playqueue"

    id = Column(Integer, primary_key=True, default=1)  # Singleton pattern
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationship to tracks
    tracks = relationship("PlayQueueTrack", order_by="PlayQueueTrack.position", cascade="all, delete-orphan")