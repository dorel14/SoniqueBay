from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, Enum, func, UniqueConstraint, Index
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
import enum
from backend.library_api.utils.database import Base

class EntityCoverType(str, enum.Enum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"

class Cover(Base):
    __tablename__ = "covers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[EntityCoverType] = mapped_column(Enum(EntityCoverType), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cover_data: Mapped[str] = mapped_column(String, nullable=True)
    mime_type: Mapped[str] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', name='uq_entity_cover'),
        Index('idx_entity_lookup', 'entity_type', 'entity_id')
    )

    def __repr__(self):
        return f"<Cover(id={self.id}, type={self.entity_type}, entity_id={self.entity_id})>"
