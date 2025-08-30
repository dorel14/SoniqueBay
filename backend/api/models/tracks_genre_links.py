from __future__ import annotations
from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone

from backend.utils.database import Base

class genre_links(Base):
    __tablename__ = 'genre_links'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracks.id'))
    genre_id: Mapped[int] = mapped_column(Integer, ForeignKey('genres.id'))
    date_added: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_modified: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    track: Mapped["Track"] = relationship("Track", back_populates="genre_links") # type: ignore # noqa: F821
    genre: Mapped["Genre"] = relationship("Genre", back_populates="genre_links") # type: ignore # noqa: F821

    def __repr__(self):
        return f"<GenreLink(track_id='{self.track_id}', genre_id='{self.genre_id}')>"