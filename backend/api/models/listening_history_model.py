
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from utils.database import Base
from backend.api.models.user_model import User # Supprimé pour éviter les imports circulaires
from backend.api.models.tracks_model import Track # Supprimé pour éviter les imports circulaires


class ListeningHistory(Base):
    __tablename__ = 'listening_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracks.id'), nullable=False)
    date_listened: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    user: Mapped["User"] = relationship("User", back_populates="listening_history")  # type: ignore # noqa: F821
    track: Mapped["Track"] = relationship("Track", back_populates="listening_history")  # type: ignore # noqa: F821

    def __repr__(self):
        return f"<ListeningHistory(user_id='{self.user_id}', track_id='{self.track_id}', date_listened='{self.date_listened}')>"