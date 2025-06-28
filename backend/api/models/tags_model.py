from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from backend.utils.database import Base

# Tables de liaison
track_genre_tags = Table(
    'track_genre_tags',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('genre_tags.id', ondelete='CASCADE'))
)

track_mood_tags = Table(
    'track_mood_tags',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('mood_tags.id', ondelete='CASCADE'))
)

class GenreTag(Base):
    __tablename__ = 'genre_tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    tracks = relationship("Track", secondary=track_genre_tags, back_populates="genre_tags")

class MoodTag(Base):
    __tablename__ = 'mood_tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    tracks = relationship("Track", secondary=track_mood_tags, back_populates="mood_tags")
