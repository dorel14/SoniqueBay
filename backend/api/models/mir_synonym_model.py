"""
Modèle SQLAlchemy pour MIRSynonym - Synonyms dynamiques générés via Ollama.

Ce module définit le modèle MIRSynonym pour stocker les synonymes sémantiques
des tags (genres et moods) avec leurs embeddings générés par Ollama.

Dépendances:
    - SQLAlchemy pour l'ORM
    - PostgreSQL avec extensions ARRAY et pgvector
    - Ollama pour la génération d'embeddings

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Column, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from backend.api.utils.database import Base


class MIRSynonym(Base):
    """
    Synonym généré via Ollama pour les tags avec embedding sémantique.

    Ce modèle stocke les synonymes dynamiques pour les genres et moods,
    permettant une recherche hybride SQL + vectorielle.

    Structure JSONB pour `synonyms`:
        {
            "search_terms": ["rock", "hard rock", "rock classique"],
            "related_tags": ["guitar", "energetic", "band"],
            "usage_context": ["party", "workout"],
            "translations": {"en": ["rock"], "fr": ["rock"]}
        }

    Attributs:
        id: Identifiant unique du synonym.
        tag_type: Type de tag ('genre' ou 'mood').
        tag_value: Valeur du tag (nom du genre ou mood).
        synonyms: Données JSONB contenant les synonymes structurés.
        embedding: Vecteur sémantique généré par Ollama (768 dimensions).
        source: Source de génération ('ollama' par défaut).
        confidence: Score de confiance de la génération (0.0 à 1.0).
        is_active: Drapeau d'activation pour les requêtes.

    Exemples:
        >>> synonym = MIRSynonym(
        ...     tag_type='genre',
        ...     tag_value='rock',
        ...     synonyms={
        ...         'search_terms': ['rock', 'hard rock'],
        ...         'related_tags': ['energetic', 'guitar'],
        ...         'translations': {'en': ['rock'], 'fr': ['rock']}
        ...     },
        ...     embedding=[0.1, 0.2, ...]
        ... )
    """

    __tablename__ = 'mir_synonyms'

    # Colonnes principales
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        doc="Identifiant unique du synonym"
    )

    # Type de tag ('genre' ou 'mood')
    tag_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Type de tag : 'genre' ou 'mood'"
    )

    # Valeur du tag (nom du genre ou mood)
    tag_value: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom du genre ou mood"
    )

    # Synonyms générés (JSONB)
    synonyms: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        doc="Structure JSONB contenant les synonymes et termes associés"
    )

    # Embedding sémantique via Ollama nomic-embed-text (768 dimensions)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(768),
        nullable=True,
        doc="Embedding sémantique via Ollama nomic-embed-text (768 dimensions)"
    )

    # Métadonnées de traçabilité
    source: Mapped[str] = mapped_column(
        String(50),
        default='ollama',
        doc="Source de génération du synonym"
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        doc="Score de confiance de la génération (0.0 à 1.0)"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        doc="Drapeau d'activation pour les requêtes"
    )

    # Définition des index
    __table_args__ = (
        # Index pgvector pour recherche sémantique (IVFFlat)
        Index(
            'idx_mir_synonyms_embedding',
            'embedding',
            postgresql_using='ivfflat',
        ),
        # Index composite sur tag_type + tag_value
        Index(
            'idx_mir_synonyms_type_value',
            'tag_type',
            'tag_value',
        ),
        # Index sur is_active pour filtrer les enregistrements actifs
        Index(
            'idx_mir_synonyms_active',
            'is_active',
        ),
        # Contrainte d'unicité sur tag_type + tag_value
        Index(
            'uq_mir_synonyms_type_value',
            'tag_type',
            'tag_value',
            unique=True,
            postgresql_where=is_active.is_(True),
        ),
    )

    def __repr__(self) -> str:
        """Représentation lisible de l'instance MIRSynonym."""
        return (
            f"MIRSynonym(id={self.id}, "
            f"tag_type='{self.tag_type}', "
            f"tag_value='{self.tag_value}', "
            f"source='{self.source}', "
            f"confidence={self.confidence})"
        )

    @property
    def search_terms(self) -> list[str]:
        """
        Récupère les termes de recherche depuis la structure JSONB.

        Returns:
            Liste des termes de recherche associés au tag.
        """
        return self.synonyms.get('search_terms', [])

    @property
    def related_tags(self) -> list[str]:
        """
        Récupère les tags liés depuis la structure JSONB.

        Returns:
            Liste des tags liés au tag principal.
        """
        return self.synonyms.get('related_tags', [])

    @property
    def usage_contexts(self) -> list[str]:
        """
        Récupère les contextes d'usage depuis la structure JSONB.

        Returns:
            Liste des contextes d'usage pour ce tag.
        """
        return self.synonyms.get('usage_context', [])

    @property
    def translations(self) -> dict[str, list[str]]:
        """
        Récupère les traductions depuis la structure JSONB.

        Returns:
            Dictionnaire des traductions par langue.
        """
        return self.synonyms.get('translations', {})
