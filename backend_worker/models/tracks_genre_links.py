from __future__ import annotations
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin


class genre_links(TimestampMixin, Base):
    __tablename__ = 'genre_links'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracks.id'))
    genre_id: Mapped[int] = mapped_column(Integer, ForeignKey('genres.id'))

    track: Mapped["Track"] = relationship("Track", back_populates="genre_links") # type: ignore # noqa: F821
    genre: Mapped["Genre"] = relationship("Genre", back_populates="genre_links") # type: ignore # noqa: F821

    def __repr__(self):
        return f"<GenreLink(track_id='{self.track_id}', genre_id='{self.genre_id}')>"
