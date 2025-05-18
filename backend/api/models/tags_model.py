from sqlalchemy import Column, String, Integer, Table, ForeignKey
from backend.database import Base

class MoodTag(Base):
    __tablename__ = 'mood_tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

class GenreTag(Base):
    __tablename__ = 'genre_tags'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

# Tables de liaison
track_mood_tags = Table(
    'track_mood_tags',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id')),
    Column('mood_tag_id', Integer, ForeignKey('mood_tags.id'))
)

track_genre_tags = Table(
    'track_genre_tags',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id')),
    Column('genre_tag_id', Integer, ForeignKey('genre_tags.id'))
)
