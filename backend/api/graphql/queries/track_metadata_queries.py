# -*- coding: utf-8 -*-
"""
Queries GraphQL pour les métadonnées enrichies des pistes.

Rôle:
    Définit les requêtes GraphQL pour récupérer les métadonnées extensibles
    des pistes sous forme de clé-valeur.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_metadata_service: TrackMetadataService
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional, List, Dict

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_metadata_type import (
    TrackMetadataType,
    TrackMetadataStatistics,
    MetadataKeyStatistics,
    MetadataSourceStatistics,
)
from backend.api.services.track_metadata_service import TrackMetadataService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackMetadataQuery:
    """
    Queries GraphQL pour les métadonnées enrichies des pistes.
    """

    @strawberry.field
    async def track_metadata(
        self,
        track_id: int,
        metadata_key: Optional[str] = None,
        metadata_source: Optional[str] = None,
    ) -> List[TrackMetadataType]:
        """
        Récupère les métadonnées d'une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée optionnelle (filtre)
            metadata_source: Source optionnelle (filtre)

        Returns:
            Liste des métadonnées de la piste
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.get_by_track_id(
                track_id=track_id,
                metadata_key=metadata_key,
                metadata_source=metadata_source,
            )

            return [
                TrackMetadataType(
                    id=m.id,
                    track_id=m.track_id,
                    metadata_key=m.metadata_key,
                    metadata_value=m.metadata_value,
                    metadata_source=m.metadata_source,
                    created_at=m.created_at,
                    date_added=m.date_added,
                    date_modified=m.date_modified,
                )
                for m in results
            ]

    @strawberry.field
    async def track_metadata_by_id(
        self, metadata_id: int
    ) -> Optional[TrackMetadataType]:
        """
        Récupère une métadonnée par son ID.

        Args:
            metadata_id: ID de la métadonnée

        Returns:
            La métadonnée ou None si non trouvée
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            metadata = await service.get_by_id(metadata_id)

            if not metadata:
                return None

            return TrackMetadataType(
                id=metadata.id,
                track_id=metadata.track_id,
                metadata_key=metadata.metadata_key,
                metadata_value=metadata.metadata_value,
                metadata_source=metadata.metadata_source,
                created_at=metadata.created_at,
                date_added=metadata.date_added,
                date_modified=metadata.date_modified,
            )

    @strawberry.field
    async def track_metadata_value(
        self,
        track_id: int,
        metadata_key: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """
        Récupère la valeur d'une métadonnée spécifique.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            default: Valeur par défaut si non trouvée

        Returns:
            La valeur de la métadonnée ou la valeur par défaut
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            value = await service.get_metadata_value(
                track_id=track_id,
                metadata_key=metadata_key,
                default=default,
            )
            return value

    @strawberry.field
    async def track_metadata_as_dict(
        self,
        track_id: int,
        metadata_source: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Récupère toutes les métadonnées d'une piste sous forme de dictionnaire.

        Args:
            track_id: ID de la piste
            metadata_source: Source optionnelle (filtre)

        Returns:
            Dictionnaire {clé: valeur} des métadonnées
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            result = await service.get_metadata_as_dict(
                track_id=track_id,
                metadata_source=metadata_source,
            )
            return result

    @strawberry.field
    async def search_metadata_by_key(
        self,
        metadata_key: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMetadataType]:
        """
        Recherche les métadonnées par clé.

        Args:
            metadata_key: Clé de métadonnée à rechercher
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.search_by_key(
                metadata_key=metadata_key,
                skip=skip,
                limit=limit,
            )

            return [
                TrackMetadataType(
                    id=m.id,
                    track_id=m.track_id,
                    metadata_key=m.metadata_key,
                    metadata_value=m.metadata_value,
                    metadata_source=m.metadata_source,
                    created_at=m.created_at,
                    date_added=m.date_added,
                    date_modified=m.date_modified,
                )
                for m in results
            ]

    @strawberry.field
    async def search_metadata_by_key_prefix(
        self,
        key_prefix: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMetadataType]:
        """
        Recherche les métadonnées dont la clé commence par un préfixe.

        Args:
            key_prefix: Préfixe de la clé
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.search_by_key_prefix(
                key_prefix=key_prefix,
                skip=skip,
                limit=limit,
            )

            return [
                TrackMetadataType(
                    id=m.id,
                    track_id=m.track_id,
                    metadata_key=m.metadata_key,
                    metadata_value=m.metadata_value,
                    metadata_source=m.metadata_source,
                    created_at=m.created_at,
                    date_added=m.date_added,
                    date_modified=m.date_modified,
                )
                for m in results
            ]

    @strawberry.field
    async def search_metadata_by_value(
        self,
        metadata_value: str,
        exact_match: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMetadataType]:
        """
        Recherche les métadonnées par valeur.

        Args:
            metadata_value: Valeur à rechercher
            exact_match: Si True, recherche exacte, sinon partielle
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.search_by_value(
                metadata_value=metadata_value,
                exact_match=exact_match,
                skip=skip,
                limit=limit,
            )

            return [
                TrackMetadataType(
                    id=m.id,
                    track_id=m.track_id,
                    metadata_key=m.metadata_key,
                    metadata_value=m.metadata_value,
                    metadata_source=m.metadata_source,
                    created_at=m.created_at,
                    date_added=m.date_added,
                    date_modified=m.date_modified,
                )
                for m in results
            ]

    @strawberry.field
    async def search_metadata_by_source(
        self,
        metadata_source: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMetadataType]:
        """
        Recherche les métadonnées par source.

        Args:
            metadata_source: Source à rechercher (lastfm, listenbrainz, etc.)
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées de cette source
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.search_by_source(
                metadata_source=metadata_source,
                skip=skip,
                limit=limit,
            )

            return [
                TrackMetadataType(
                    id=m.id,
                    track_id=m.track_id,
                    metadata_key=m.metadata_key,
                    metadata_value=m.metadata_value,
                    metadata_source=m.metadata_source,
                    created_at=m.created_at,
                    date_added=m.date_added,
                    date_modified=m.date_modified,
                )
                for m in results
            ]

    @strawberry.field
    async def metadata_statistics(self) -> TrackMetadataStatistics:
        """
        Retourne des statistiques sur les métadonnées.

        Returns:
            Statistiques globales des métadonnées
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            stats = await service.get_metadata_statistics()

            return TrackMetadataStatistics(
                total_entries=stats.get("total_entries", 0),
                tracks_with_metadata=stats.get("tracks_with_metadata", 0),
                by_key=[
                    MetadataKeyStatistics(key=k, count=v)
                    for k, v in stats.get("by_key", {}).items()
                ],
                by_source=[
                    MetadataSourceStatistics(source=k, count=v)
                    for k, v in stats.get("by_source", {}).items()
                ],
            )

    @strawberry.field
    async def tracks_without_metadata(
        self,
        metadata_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[dict]:
        """
        Récupère les IDs des pistes sans métadonnées.

        Args:
            metadata_key: Clé de métadonnée spécifique (None = toutes)
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans métadonnées
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            results = await service.get_tracks_without_metadata(
                metadata_key=metadata_key,
                limit=limit,
            )
            return results
