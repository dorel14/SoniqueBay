# -*- coding: utf-8 -*-
"""
Types GraphQL Strawberry pour les métadonnées enrichies des pistes.

Rôle:
    Définit les types GraphQL pour TrackMetadata, incluant le type
    de sortie, les inputs pour mutations et les opérations batch.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict

import strawberry

from backend.api.utils.logging import logger


@strawberry.type
class TrackMetadataType:
    """
    Type GraphQL pour les métadonnées enrichies d'une piste.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        metadata_key: Clé de métadonnée (ex: 'lastfm_playcount')
        metadata_value: Valeur de la métadonnée
        metadata_source: Source de la métadonnée (lastfm, listenbrainz, etc.)
        created_at: Date de création
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    metadata_key: str
    metadata_value: Optional[str] = None
    metadata_source: Optional[str] = None
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.type
class TrackMetadataBatchResult:
    """
    Type GraphQL pour le résultat d'une opération batch sur les métadonnées.

    Attributes:
        created_count: Nombre de métadonnées créées
        updated_count: Nombre de métadonnées mises à jour
        failed_count: Nombre d'échecs
        metadata_list: Liste des métadonnées créées/mises à jour
        errors: Liste des erreurs éventuelles
    """

    created_count: int
    updated_count: int
    failed_count: int
    metadata_list: List[TrackMetadataType]
    errors: List[str]


@strawberry.type
class MetadataKeyStatistics:
    """
    Type GraphQL pour les statistiques par clé de métadonnée.

    Attributes:
        key: Clé de métadonnée
        count: Nombre d'occurrences
    """

    key: str
    count: int


@strawberry.type
class MetadataSourceStatistics:
    """
    Type GraphQL pour les statistiques par source de métadonnée.

    Attributes:
        source: Source de métadonnée
        count: Nombre d'occurrences
    """

    source: str
    count: int


@strawberry.type
class TrackMetadataStatistics:
    """
    Type GraphQL pour les statistiques globales des métadonnées.

    Attributes:
        total_entries: Nombre total d'entrées
        tracks_with_metadata: Nombre de pistes ayant des métadonnées
        by_key: Statistiques par clé
        by_source: Statistiques par source
    """

    total_entries: int
    tracks_with_metadata: int
    by_key: List[MetadataKeyStatistics]
    by_source: List[MetadataSourceStatistics]


@strawberry.input
class TrackMetadataInput:
    """
    Input GraphQL pour créer une métadonnée.

    Attributes:
        track_id: ID de la piste (obligatoire)
        metadata_key: Clé de métadonnée (obligatoire)
        metadata_value: Valeur de la métadonnée
        metadata_source: Source de la métadonnée
    """

    track_id: int
    metadata_key: str
    metadata_value: Optional[str] = None
    metadata_source: Optional[str] = None


@strawberry.input
class TrackMetadataUpdateInput:
    """
    Input GraphQL pour mettre à jour une métadonnée.

    Attributes:
        track_id: ID de la piste (obligatoire)
        metadata_key: Clé de métadonnée à mettre à jour (obligatoire)
        metadata_value: Nouvelle valeur
        metadata_source: Source (pour identifier l'entrée si plusieurs sources)
    """

    track_id: int
    metadata_key: str
    metadata_value: Optional[str] = None
    metadata_source: Optional[str] = None


@strawberry.input
class TrackMetadataBatchInput:
    """
    Input GraphQL pour créer/mettre à jour plusieurs métadonnées en batch.

    Attributes:
        track_id: ID de la piste (obligatoire)
        metadata_dict: Dictionnaire {clé: valeur} des métadonnées
        metadata_source: Source commune pour toutes les métadonnées
    """

    track_id: int
    metadata_dict: Dict[str, str]
    metadata_source: Optional[str] = None


@strawberry.input
class TrackMetadataSearchInput:
    """
    Input GraphQL pour rechercher des métadonnées.

    Attributes:
        metadata_key: Clé exacte à rechercher
        key_prefix: Préfixe de clé (recherche par début de clé)
        metadata_value: Valeur à rechercher
        exact_match: Si True, recherche exacte, sinon partielle
        metadata_source: Source à filtrer
        skip: Nombre de résultats à ignorer
        limit: Nombre maximum de résultats
    """

    metadata_key: Optional[str] = None
    key_prefix: Optional[str] = None
    metadata_value: Optional[str] = None
    exact_match: bool = False
    metadata_source: Optional[str] = None
    skip: int = 0
    limit: int = 100


@strawberry.input
class TrackMetadataDeleteInput:
    """
    Input GraphQL pour supprimer des métadonnées.

    Attributes:
        track_id: ID de la piste (obligatoire)
        metadata_key: Clé spécifique à supprimer (None = toutes)
        metadata_source: Source spécifique à supprimer (None = toutes)
    """

    track_id: int
    metadata_key: Optional[str] = None
    metadata_source: Optional[str] = None
