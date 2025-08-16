from __future__ import annotations
from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.api.models.tracks_model import Track # Supprimé pour éviter les imports circulaires
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import TypeDecorator
import json
from backend.utils.database import Base

class JSONList(TypeDecorator):
    impl = Text
    cache_ok = True  # nécessaire pour éviter les warnings SQLAlchemy

    @property
    def python_type(self):
        return list  # ✅ <- ceci évite l'erreur de Strawchemy

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)



class TrackVector(Base):
    __tablename__ = 'track_vectors'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    vector_data: Mapped[list] = mapped_column(MutableList.as_mutable(JSONList))  # Stocke sous forme de liste JSON
    # Relations
    track: Mapped["Track"] = relationship("Track", back_populates="vectors")  # type: ignore # noqa: F821

    def __repr__(self):
        return f"<TrackVector(track_id='{self.track_id}', vector_data='{self.vector_data[:20]}...')>"  # Display first 20 characters of vector data