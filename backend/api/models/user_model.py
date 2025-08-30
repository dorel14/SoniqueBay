from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, timezone
from backend.utils.database import Base
from backend.api.models.listening_history_model import ListeningHistory # Supprimé pour éviter les imports circulaires


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    date_joined: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    listening_history: Mapped[list["ListeningHistory"]] = relationship("ListeningHistory", back_populates="user")  # type: ignore # noqa: F821

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', date_joined='{self.date_joined}')>"