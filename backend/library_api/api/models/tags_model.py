from __future__ import annotations
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.library_api.utils.database import Base

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
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    tracks: Mapped[list["Track"]] = relationship("Track", secondary=track_genre_tags, back_populates="genre_tags") # type: ignore # noqa: F821

class MoodTag(Base):
    __tablename__ = 'mood_tags'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    tracks: Mapped[list["Track"]] = relationship("Track", secondary=track_mood_tags, back_populates="mood_tags") # type: ignore # noqa: F821
