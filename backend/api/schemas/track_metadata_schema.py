# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour les métadonnées enrichies des pistes.

Rôle:
    Définit les schémas de validation pour les données TrackMetadata
    utilisés dans les routers API et les services d'enrichissement.

Dépendances:
    - pydantic: BaseModel, Field, ConfigDict
    - backend.api.schemas.base_schema: TimestampedSchema

Schémas:
    - TrackMetadataBase: Schéma de base avec tous les champs
    - TrackMetadataCreate: Schéma pour la création
    - TrackMetadataUpdate: Schéma pour la mise à jour
    - TrackMetadata: Schéma de lecture complet
    - TrackMetadataWithTrack: Schéma avec relation Track incluse
    - TrackMetadataBatch: Schéma pour les opérations batch
    - TrackMetadataBySource: Regroupement des métadonnées par source

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.schemas.base_schema import TimestampedSchema

if TYPE_CHECKING:
    from backend.api.schemas.tracks_schema import Track


class TrackMetadataBase(BaseModel):
    """
    Schéma de base pour les métadonnées enrichies d'une piste.

    Utilise un format clé-valeur extensible pour stocker des métadonnées
    provenant de sources externes sans modifier le schéma de la DB.
    """

    track_id: int = Field(
        ..., description="ID de la piste associée (relation N:1)"
    )

    metadata_key: str = Field(
        ...,
        max_length=255,
        description="Clé de métadonnée (ex: lastfm_playcount, musicbrainz_rating)"
    )

    metadata_value: Optional[str] = Field(
        None,
        description="Valeur de la métadonnée (stockée comme texte, JSON possible)"
    )

    metadata_source: Optional[str] = Field(
        None,
        max_length=100,
        description="Source: lastfm, listenbrainz, discogs, manual, etc."
    )

    created_at: Optional[datetime] = Field(
        None, description="Date de création de la métadonnée"
    )


class TrackMetadataCreate(TrackMetadataBase):
    """
    Schéma pour la création d'une entrée TrackMetadata.

    Tous les champs de TrackMetadataBase sont requis sauf ceux
    explicitement optionnels.
    """
    pass


class TrackMetadataUpdate(BaseModel):
    """
    Schéma pour la mise à jour d'une entrée TrackMetadata.

    Tous les champs sont optionnels pour permettre les mises à jour
    partielles des métadonnées.
    """

    track_id: Optional[int] = Field(None, description="ID de la piste")
    metadata_key: Optional[str] = Field(None, max_length=255)
    metadata_value: Optional[str] = Field(None, description="Valeur")
    metadata_source: Optional[str] = Field(None, max_length=100)
    created_at: Optional[datetime] = None


class TrackMetadata(TrackMetadataBase, TimestampedSchema):
    """
    Schéma de lecture complet pour TrackMetadata.

    Inclut l'ID, les timestamps et tous les champs de base.
    Utilisé pour les réponses API.
    """

    id: int = Field(..., description="ID unique de l'entrée de métadonnée")

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


class TrackMetadataWithTrack(TrackMetadata):
    """
    Schéma de lecture avec la relation Track incluse.
    """

    track: Optional["Track"] = Field(
        None, description="Piste associée à cette métadonnée"
    )


class TrackMetadataCompact(BaseModel):
    """
    Schéma compact pour les réponses rapides.

    Inclut uniquement les champs essentiels pour les listes
    et les réponses légères (optimisé pour RPi4).
    """

    id: int
    track_id: int
    metadata_key: str
    metadata_value: Optional[str] = None
    metadata_source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TrackMetadataByKey(BaseModel):
    """
    Regroupement des métadonnées par clé.

    Permet de récupérer toutes les valeurs pour une clé donnée
    (ex: toutes les sources pour 'playcount').
    """

    metadata_key: str = Field(..., description="Clé de métadonnée")
    values_by_source: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Valeurs regroupées par source"
    )

    model_config = ConfigDict(from_attributes=True)


class TrackMetadataBySource(BaseModel):
    """
    Regroupement des métadonnées par source.

    Permet de récupérer toutes les métadonnées d'une source donnée
    pour une piste (ex: toutes les métadonnées Last.fm).
    """

    metadata_source: str = Field(..., description="Source des métadonnées")
    metadata: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Métadonnées sous forme de dictionnaire clé-valeur"
    )

    model_config = ConfigDict(from_attributes=True)


class TrackMetadataBatchCreate(BaseModel):
    """
    Requête pour la création batch de métadonnées.

    Permet de créer plusieurs entrées de métadonnées en une seule
    opération (optimisé pour l'enrichissement par workers).
    """

    track_id: int = Field(..., description="ID de la piste cible")

    metadata_items: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des métadonnées à créer"
    )

    metadata_source: str = Field(
        ...,
        max_length=100,
        description="Source commune pour toutes les métadonnées"
    )

    replace_existing: bool = Field(
        default=False,
        description="Remplacer les métadonnées existantes pour cette source"
    )


class TrackMetadataBatchResponse(BaseModel):
    """
    Réponse d'une opération batch de métadonnées.
    """

    track_id: int = Field(..., description="ID de la piste")
    total_requested: int = Field(..., description="Nombre total demandé")
    successful: int = Field(..., description="Nombre de succès")
    failed: int = Field(..., description="Nombre d'échecs")
    errors: List[str] = Field(default=[], description="Messages d'erreur")

    model_config = ConfigDict(from_attributes=True)


class TrackMetadataFilter(BaseModel):
    """
    Filtres pour la recherche de métadonnées.

    Utilisé dans les endpoints de recherche et de listing.
    """

    track_id: Optional[int] = Field(None, description="Filtrer par ID de piste")
    metadata_key: Optional[str] = Field(None, description="Filtrer par clé")
    metadata_source: Optional[str] = Field(None, description="Filtrer par source")
    key_prefix: Optional[str] = Field(
        None, description="Préfixe de clé (recherche LIKE)"
    )


class TrackMetadataStats(BaseModel):
    """
    Statistiques sur les métadonnées d'une piste.

    Fournit un résumé des sources et clés disponibles.
    """

    track_id: int = Field(..., description="ID de la piste")
    total_entries: int = Field(..., description="Nombre total d'entrées")
    sources: List[str] = Field(
        default=[], description="Liste des sources disponibles"
    )
    keys_by_source: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Clés regroupées par source"
    )

    model_config = ConfigDict(from_attributes=True)


# Types de métadonnées prédéfinis pour la validation et l'autocomplétion
class CommonMetadataKeys:
    """
    Clés de métadonnées couramment utilisées.

    Ces constantes servent de référence pour standardiser
    les noms des clés de métadonnées.
    """

    # Last.fm
    LASTFM_PLAYCOUNT = "lastfm_playcount"
    LASTFM_LISTENERS = "lastfm_listeners"
    LASTFM_USER_PLAYCOUNT = "lastfm_user_playcount"
    LASTFM_TAGS = "lastfm_tags"

    # MusicBrainz
    MB_RATING = "musicbrainz_rating"
    MB_TAG_COUNT = "musicbrainz_tag_count"

    # ListenBrainz
    LB_LISTEN_COUNT = "listenbrainz_listen_count"

    # Discogs
    DISCOGS_COMMUNITY_HAVE = "discogs_community_have"
    DISCOGS_COMMUNITY_WANT = "discogs_community_want"

    # Audio features étendus
    AUDIO_FEATURES_VERSION = "audio_features_version"
    ANALYSIS_CONFIDENCE = "analysis_confidence"
