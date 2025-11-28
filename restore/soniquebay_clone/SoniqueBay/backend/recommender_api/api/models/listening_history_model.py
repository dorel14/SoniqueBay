
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Integer, DateTime, func
from sqlalchemy.orm import  Mapped, mapped_column
from backend.api.utils.database import Base


class ListeningHistory(Base):
    __tablename__ = 'listening_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date_listened: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[str] = mapped_column(nullable=True)



    def __repr__(self):
        return f"<ListeningHistory(user_id='{self.user_id}', track_id='{self.track_id}', date_listened='{self.date_listened}')>"