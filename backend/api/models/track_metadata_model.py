# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les métadonnées enrichies des pistes.

Rôle:
    Stocke les métadonnées enrichies et extensibles des pistes sous forme
    de clé-valeur, permettant d'ajouter des informations de sources externes
    (Last.fm, ListenBrainz, etc.) sans modifier le schéma.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin

Relations:
    - Track: Relation N:1 avec la table tracks

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.api.models.tracks_model import Track


class TrackMetadata(Base, TimestampMixin):
    """
    Métadonnées enrichies extensibles pour une piste musicale.

    Cette table utilise un format clé-valeur pour permettre l'ajout
    dynamique de métadonnées provenant de sources externes sans
    modification du schéma de base de données.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track
        metadata_key: Clé de métadonnée (ex: 'lastfm_playcount')
        metadata_value: Valeur de métadonnée
        metadata_source: Source de la métadonnée (lastfm, listenbrainz, etc.)
        created_at: Date de création de l'entrée
    """

    __tablename__ = 'track_metadata'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False
    )

    # Format clé-valeur extensible
    metadata_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Clé de métadonnée (ex: lastfm_playcount, musicbrainz_rating)"
    )

    # Valeur stockée sous forme de texte (JSON possible si besoin)
    metadata_value: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Valeur de la métadonnée (stockée comme texte)"
    )

    # Source de la métadonnée pour la traçabilité
    metadata_source: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        doc="Source: lastfm, listenbrainz, discogs, manual, etc."
    )

    # Date de création de l'entrée
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de création de la métadonnée"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="metadata_entries",
        lazy="selectin"
    )

    __table_args__ = (
        # Index pour les recherches par track_id
        Index('idx_track_metadata_track_id', 'track_id'),
        # Index pour les recherches par clé de métadonnée
        Index('idx_track_metadata_key', 'metadata_key'),
        # Index pour les recherches par source
        Index('idx_track_metadata_source', 'metadata_source'),
        # Index composite unique pour éviter les doublons (track_id, key, source)
        Index(
            'uq_track_metadata_track_key_source',
            'track_id',
            'metadata_key',
            'metadata_source',
            unique=True
        ),
        # Index composite pour les recherches par track + clé
        Index('idx_track_metadata_track_key', 'track_id', 'metadata_key'),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackMetadata(id={self.id}, track_id={self.track_id}, "
            f"key={self.metadata_key}, source={self.metadata_source})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'metadata_key': self.metadata_key,
            'metadata_value': self.metadata_value,
            'metadata_source': self.metadata_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
