# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour les embeddings vectoriels des pistes.

Rôle:
    Définit les schémas de validation pour les données TrackEmbeddings
    utilisés dans les routers API et les services de recherche vectorielle.

Dépendances:
    - pydantic: BaseModel, Field, ConfigDict
    - backend.api.schemas.base_schema: TimestampedSchema

Schémas:
    - TrackEmbeddingsBase: Schéma de base avec tous les champs
    - TrackEmbeddingsCreate: Schéma pour la création
    - TrackEmbeddingsUpdate: Schéma pour la mise à jour
    - TrackEmbeddings: Schéma de lecture complet
    - TrackEmbeddingsWithTrack: Schéma avec relation Track incluse
    - TrackEmbeddingsVectorOnly: Schéma minimal pour la recherche vectorielle
    - TrackSimilarityResult: Résultat de recherche par similarité

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.schemas.base_schema import TimestampedSchema

if TYPE_CHECKING:
    from backend.api.schemas.tracks_schema import Track


class TrackEmbeddingsBase(BaseModel):
    """
    Schéma de base pour les embeddings vectoriels d'une piste.

    Stocke les vecteurs d'embedding (512 dimensions) pour la recherche
    vectorielle et les recommandations basées sur la similarité.
    """

    track_id: int = Field(
        ..., description="ID de la piste associée (relation N:1)"
    )

    embedding_type: str = Field(
        default="semantic",
        max_length=50,
        description="Type d'embedding: semantic, audio, text, combined"
    )

    # Le vecteur est stocké comme liste de floats (512 dimensions)
    # Note: Ce champ est exclu des schémas de création/maj par sécurité
    # car les vecteurs sont générés côté serveur

    embedding_source: Optional[str] = Field(
        None, max_length=100,
        description="Source de vectorisation: ollama, huggingface, etc."
    )

    embedding_model: Optional[str] = Field(
        None, max_length=100,
        description="Modèle utilisé: nomic-embed-text, all-MiniLM-L6-v2, etc."
    )

    created_at: Optional[datetime] = Field(
        None, description="Date de création de l'embedding"
    )


class TrackEmbeddingsCreate(BaseModel):
    """
    Schéma pour la création d'un embedding.

    Le vecteur doit être fourni lors de la création mais est généralement
    généré par le service de vectorisation.
    """

    track_id: int = Field(..., description="ID de la piste associée")

    embedding_type: str = Field(
        default="semantic",
        max_length=50,
        description="Type d'embedding"
    )

    vector: List[float] = Field(
        ...,
        min_length=512,
        max_length=512,
        description="Vecteur d'embedding (512 dimensions)"
    )

    embedding_source: Optional[str] = Field(
        None, max_length=100,
        description="Source de vectorisation"
    )

    embedding_model: Optional[str] = Field(
        None, max_length=100,
        description="Modèle utilisé"
    )

    created_at: Optional[datetime] = None


class TrackEmbeddingsUpdate(BaseModel):
    """
    Schéma pour la mise à jour d'un embedding.

    Tous les champs sont optionnels. Le vecteur peut être mis à jour
    lors d'une re-vectorisation.
    """

    track_id: Optional[int] = Field(None, description="ID de la piste")
    embedding_type: Optional[str] = Field(None, max_length=50)
    vector: Optional[List[float]] = Field(
        None, min_length=512, max_length=512
    )
    embedding_source: Optional[str] = Field(None, max_length=100)
    embedding_model: Optional[str] = Field(None, max_length=100)
    created_at: Optional[datetime] = None


class TrackEmbeddings(TrackEmbeddingsBase, TimestampedSchema):
    """
    Schéma de lecture complet pour TrackEmbeddings.

    Inclut l'ID, les timestamps et les métadonnées (mais pas le vecteur
    complet par défaut pour des raisons de performance sur RPi4).
    """

    id: int = Field(..., description="ID unique de l'embedding")

    model_config = ConfigDict(from_attributes=True)

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_created_at(cls, value):
        """Convertit les chaînes ISO en datetime si nécessaire."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None


class TrackEmbeddingsWithVector(TrackEmbeddings):
    """
    Schéma incluant le vecteur complet.

    À utiliser avec parcimonie car le vecteur fait 512 floats
    (environ 2KB par entrée).
    """

    vector: List[float] = Field(
        ...,
        description="Vecteur d'embedding complet (512 dimensions)"
    )


class TrackEmbeddingsWithTrack(TrackEmbeddings):
    """
    Schéma de lecture avec la relation Track incluse.
    """

    track: Optional["Track"] = Field(
        None, description="Piste associée à cet embedding"
    )


class TrackEmbeddingsVectorOnly(BaseModel):
    """
    Schéma minimal pour la recherche vectorielle.

    Inclut uniquement l'ID et le vecteur pour les opérations
    de similarité (optimisé pour RPi4).
    """

    id: int
    track_id: int
    vector: List[float] = Field(..., min_length=512, max_length=512)
    embedding_type: str

    model_config = ConfigDict(from_attributes=True)


class TrackSimilarityResult(BaseModel):
    """
    Résultat d'une recherche par similarité vectorielle.

    Contient la piste similaire et le score de similarité
    (distance cosinus ou euclidienne).
    """

    track_id: int = Field(..., description="ID de la piste similaire")
    similarity_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Score de similarité (0-1, 1 = identique)"
    )
    embedding_type: str = Field(
        ..., description="Type d'embedding utilisé pour la comparaison"
    )

    # Métadonnées optionnelles de la piste (chargées séparément)
    track_title: Optional[str] = None
    artist_name: Optional[str] = None
    album_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmbeddingBatchRequest(BaseModel):
    """
    Requête pour la création batch d'embeddings.

    Utilisé par les workers Celery pour vectoriser plusieurs pistes.
    """

    track_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des IDs de pistes à vectoriser"
    )

    embedding_type: str = Field(
        default="semantic",
        description="Type d'embedding à générer"
    )

    embedding_model: Optional[str] = Field(
        None,
        description="Modèle de vectorisation à utiliser"
    )

    replace_existing: bool = Field(
        default=False,
        description="Remplacer les embeddings existants"
    )


class EmbeddingBatchResponse(BaseModel):
    """
    Réponse d'une opération batch d'embeddings.
    """

    total_requested: int = Field(..., description="Nombre total demandé")
    successful: int = Field(..., description="Nombre de succès")
    failed: int = Field(..., description="Nombre d'échecs")
    errors: List[str] = Field(default=[], description="Messages d'erreur")

    model_config = ConfigDict(from_attributes=True)
