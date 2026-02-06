# -*- coding: utf-8 -*-
"""
Mutations GraphQL pour les métadonnées enrichies des pistes.

Rôle:
    Définit les mutations GraphQL pour créer, mettre à jour et supprimer
    les métadonnées extensibles des pistes musicales.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_metadata_service: TrackMetadataService
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional, List

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_metadata_type import (
    TrackMetadataType,
    TrackMetadataInput,
    TrackMetadataUpdateInput,
    TrackMetadataBatchInput,
    TrackMetadataBatchResult,
    TrackMetadataDeleteInput,
)
from backend.api.services.track_metadata_service import TrackMetadataService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackMetadataMutation:
    """
    Mutations GraphQL pour les métadonnées enrichies des pistes.
    """

    @strawberry.mutation
    async def create_track_metadata(
        self, input: TrackMetadataInput
    ) -> TrackMetadataType:
        """
        Crée une nouvelle métadonnée pour une piste.

        Args:
            input: Données de la métadonnée à créer

        Returns:
            La métadonnée créée

        Raises:
            Exception: Si une métadonnée identique existe déjà
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)

            try:
                metadata = await service.create(
                    track_id=input.track_id,
                    metadata_key=input.metadata_key,
                    metadata_value=input.metadata_value,
                    metadata_source=input.metadata_source,
                )

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
            except Exception as e:
                logger.error(
                    f"[GRAPHQL] Erreur création metadata pour "
                    f"track_id={input.track_id}, key={input.metadata_key}: {e}"
                )
                raise

    @strawberry.mutation
    async def create_or_update_track_metadata(
        self, input: TrackMetadataInput
    ) -> TrackMetadataType:
        """
        Crée ou met à jour une métadonnée pour une piste.

        Args:
            input: Données de la métadonnée

        Returns:
            La métadonnée créée ou mise à jour
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)

            metadata = await service.create_or_update(
                track_id=input.track_id,
                metadata_key=input.metadata_key,
                metadata_value=input.metadata_value,
                metadata_source=input.metadata_source,
            )

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

    @strawberry.mutation
    async def batch_create_track_metadata(
        self, input: TrackMetadataBatchInput
    ) -> TrackMetadataBatchResult:
        """
        Crée ou met à jour plusieurs métadonnées pour une piste en batch.

        Args:
            input: Données batch (track_id, metadata_dict, source)

        Returns:
            Résultat de l'opération batch
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)

            try:
                results = await service.batch_create(
                    track_id=input.track_id,
                    metadata_dict=input.metadata_dict,
                    metadata_source=input.metadata_source,
                )

                metadata_list = [
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

                # Déterminer combien ont été créés vs mis à jour
                # (simplifié - en pratique, le service pourrait retourner plus d'infos)
                return TrackMetadataBatchResult(
                    created_count=len(metadata_list),
                    updated_count=0,  # Simplifié
                    failed_count=0,
                    metadata_list=metadata_list,
                    errors=[],
                )
            except Exception as e:
                logger.error(
                    f"[GRAPHQL] Erreur batch metadata pour "
                    f"track_id={input.track_id}: {e}"
                )
                return TrackMetadataBatchResult(
                    created_count=0,
                    updated_count=0,
                    failed_count=len(input.metadata_dict),
                    metadata_list=[],
                    errors=[str(e)],
                )

    @strawberry.mutation
    async def update_track_metadata(
        self, input: TrackMetadataUpdateInput
    ) -> Optional[TrackMetadataType]:
        """
        Met à jour une métadonnée existante.

        Args:
            input: Données de mise à jour

        Returns:
            La métadonnée mise à jour ou None si non trouvée
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)

            metadata = await service.update(
                track_id=input.track_id,
                metadata_key=input.metadata_key,
                metadata_value=input.metadata_value,
                metadata_source=input.metadata_source,
            )

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

    @strawberry.mutation
    async def delete_track_metadata(
        self,
        track_id: int,
        metadata_key: Optional[str] = None,
        metadata_source: Optional[str] = None,
    ) -> bool:
        """
        Supprime les métadonnées d'une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé spécifique à supprimer (None = toutes)
            metadata_source: Source spécifique à supprimer (None = toutes)

        Returns:
            True si supprimées, False si non trouvées
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            result = await service.delete(
                track_id=track_id,
                metadata_key=metadata_key,
                metadata_source=metadata_source,
            )
            return result

    @strawberry.mutation
    async def delete_track_metadata_by_id(
        self, metadata_id: int
    ) -> bool:
        """
        Supprime une métadonnée par son ID.

        Args:
            metadata_id: ID de la métadonnée

        Returns:
            True si supprimée, False si non trouvée
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            result = await service.delete_by_id(metadata_id=metadata_id)
            return result

    @strawberry.mutation
    async def delete_track_metadata_by_input(
        self, input: TrackMetadataDeleteInput
    ) -> bool:
        """
        Supprime les métadonnées d'une piste via un input structuré.

        Args:
            input: Données de suppression (track_id, key optionnel, source optionnel)

        Returns:
            True si supprimées, False si non trouvées
        """
        async with get_async_session() as session:
            service = TrackMetadataService(session)
            result = await service.delete(
                track_id=input.track_id,
                metadata_key=input.metadata_key,
                metadata_source=input.metadata_source,
            )
            return result
