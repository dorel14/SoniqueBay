from sqlalchemy import Column, String, Integer, DateTime, Enum, func, UniqueConstraint, Index
import enum
from backend.utils.database import Base

class EntityCoverType(str, enum.Enum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"

class Cover(Base):
    __tablename__ = "covers"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(Enum(EntityCoverType), nullable=False)  # Utiliser l'enum ici
    entity_id = Column(Integer, nullable=False)
    cover_data = Column(String)  # Base64
    mime_type = Column(String)
    url = Column(String)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    date_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', name='uq_entity_cover'),
        Index('idx_entity_lookup', 'entity_type', 'entity_id')
    )

    def __repr__(self):
        return f"<Cover(id={self.id}, type={self.entity_type}, entity_id={self.entity_id})>"
