# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les embeddings vectoriels des pistes.

Rôle:
    Stocke les vecteurs d'embedding (sémantiques, audio, texte) pour
    la recherche vectorielle et les recommandations basées sur la similarité.
    Permet de gérer plusieurs types d'embeddings par piste.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin
    - pgvector.sqlalchemy: Vector pour les embeddings

Relations:
    - Track: Relation N:1 avec la table tracks

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from backend.api.utils.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.api.models.tracks_model import Track


class TrackEmbeddings(Base, TimestampMixin):
    """
    Embeddings vectoriels pour une piste musicale.

    Cette table permet de stocker plusieurs types d'embeddings par piste
    (sémantique, audio, texte, etc.) avec traçabilité de la source.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track
        embedding_type: Type d'embedding (semantic, audio, text, etc.)
        vector: Vecteur d'embedding (512 dimensions)
        embedding_source: Source de vectorisation (ollama, etc.)
        embedding_model: Modèle utilisé (nomic-embed-text, etc.)
        created_at: Date de création de l'embedding
    """

    __tablename__ = 'track_embeddings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False
    )

    # Type d'embedding pour différencier les vecteurs
    embedding_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default='semantic',
        doc="Type d'embedding: semantic, audio, text, combined"
    )

    # Vecteur d'embedding (512 dimensions)
    vector: Mapped[list[float]] = mapped_column(
        Vector(512),
        nullable=False,
        doc="Vecteur d'embedding 512 dimensions"
    )

    # Traçabilité de la vectorisation
    embedding_source: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="Source de vectorisation: ollama, huggingface, etc."
    )
    embedding_model: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="Modèle utilisé: nomic-embed-text, all-MiniLM-L6-v2, etc."
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de création de l'embedding"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="embeddings",
        lazy="selectin"
    )

    __table_args__ = (
        # Index pour les recherches par track_id
        Index('idx_track_embeddings_track_id', 'track_id'),
        # Index pour filtrer par type d'embedding
        Index('idx_track_embeddings_type', 'embedding_type'),
        # Index composite unique pour éviter les doublons (track_id, embedding_type)
        Index(
            'uq_track_embeddings_track_type',
            'track_id',
            'embedding_type',
            unique=True
        ),
        # Index HNSW pour recherche vectorielle rapide
        Index(
            'idx_track_embeddings_vector',
            'vector',
            postgresql_using='hnsw',
            postgresql_with={'m': 16, 'ef_construction': 64}
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackEmbeddings(id={self.id}, track_id={self.track_id}, "
            f"type={self.embedding_type}, model={self.embedding_model})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'embedding_type': self.embedding_type,
            'embedding_source': self.embedding_source,
            'embedding_model': self.embedding_model,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
