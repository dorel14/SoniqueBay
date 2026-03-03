# -*- coding: utf-8 -*-
"""
Mutations GraphQL pour les embeddings vectoriels des pistes.

Rôle:
    Définit les mutations GraphQL pour créer, mettre à jour et supprimer
    les embeddings vectoriels des pistes musicales.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_embeddings_service: TrackEmbeddingsService
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional, List

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_embeddings_type import (
    TrackEmbeddingsType,
    TrackEmbeddingsInput,
    TrackEmbeddingsUpdateInput,
)
from backend.api.services.track_embeddings_service import TrackEmbeddingsService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackEmbeddingsMutation:
    """
    Mutations GraphQL pour les embeddings vectoriels des pistes.
    """

    @strawberry.mutation
    async def create_track_embedding(
        self, input: TrackEmbeddingsInput
    ) -> TrackEmbeddingsType:
        """
        Crée un nouvel embedding pour une piste.

        Args:
            input: Données de l'embedding à créer

        Returns:
            L'embedding créé

        Raises:
            ValueError: Si le vecteur n'a pas 512 dimensions
            Exception: Si un embedding du même type existe déjà
        """
        async with get_async_session() as session:
            service = TrackEmbeddingsService(session)

            try:
                embedding = await service.create(
                    track_id=input.track_id,
                    vector=input.vector,
                    embedding_type=input.embedding_type,
                    embedding_source=input.embedding_source,
                    embedding_model=input.embedding_model,
                )

                return TrackEmbeddingsType(
                    id=embedding.id,
                    track_id=embedding.track_id,
                    embedding_type=embedding.embedding_type,
                    embedding_source=embedding.embedding_source,
                    embedding_model=embedding.embedding_model,
                    created_at=embedding.created_at,
                    date_added=embedding.date_added,
                    date_modified=embedding.date_modified,
                )
            except Exception as e:
                logger.error(
                    f"[GRAPHQL] Erreur création embedding pour "
                    f"track_id={input.track_id}: {e}"
                )
                raise

    @strawberry.mutation
    async def create_or_update_track_embedding(
        self, input: TrackEmbeddingsInput
    ) -> TrackEmbeddingsType:
        """
        Crée ou met à jour un embedding pour une piste.

        Args:
            input: Données de l'embedding

        Returns:
            L'embedding créé ou mis à jour
        """
        async with get_async_session() as session:
            service = TrackEmbeddingsService(session)

            embedding = await service.create_or_update(
                track_id=input.track_id,
                vector=input.vector,
                embedding_type=input.embedding_type,
                embedding_source=input.embedding_source,
                embedding_model=input.embedding_model,
            )

            return TrackEmbeddingsType(
                id=embedding.id,
                track_id=embedding.track_id,
                embedding_type=embedding.embedding_type,
                embedding_source=embedding.embedding_source,
                embedding_model=embedding.embedding_model,
                created_at=embedding.created_at,
                date_added=embedding.date_added,
                date_modified=embedding.date_modified,
            )

    @strawberry.mutation
    async def update_track_embedding(
        self, input: TrackEmbeddingsUpdateInput
    ) -> Optional[TrackEmbeddingsType]:
        """
        Met à jour un embedding existant.

        Args:
            input: Données de mise à jour (track_id et embedding_type obligatoires)

        Returns:
            L'embedding mis à jour ou None si non trouvé
        """
        async with get_async_session() as session:
            service = TrackEmbeddingsService(session)

            embedding = await service.update(
                track_id=input.track_id,
                embedding_type=input.embedding_type,
                vector=input.vector,
                embedding_source=input.embedding_source,
                embedding_model=input.embedding_model,
            )

            if not embedding:
                return None

            return TrackEmbeddingsType(
                id=embedding.id,
                track_id=embedding.track_id,
                embedding_type=embedding.embedding_type,
                embedding_source=embedding.embedding_source,
                embedding_model=embedding.embedding_model,
                created_at=embedding.created_at,
                date_added=embedding.date_added,
                date_modified=embedding.date_modified,
            )

    @strawberry.mutation
    async def delete_track_embeddings(
        self,
        track_id: int,
        embedding_type: Optional[str] = None,
    ) -> bool:
        """
        Supprime les embeddings d'une piste.

        Args:
            track_id: ID de la piste
            embedding_type: Type spécifique à supprimer (None = tous)

        Returns:
            True si supprimés, False si non trouvés
        """
        async with get_async_session() as session:
            service = TrackEmbeddingsService(session)
            result = await service.delete(
                track_id=track_id,
                embedding_type=embedding_type,
            )
            return result

    @strawberry.mutation
    async def delete_track_embedding_by_id(
        self, embedding_id: int
    ) -> bool:
        """
        Supprime un embedding par son ID.

        Args:
            embedding_id: ID de l'embedding

        Returns:
            True si supprimé, False si non trouvé
        """
        async with get_async_session() as session:
            service = TrackEmbeddingsService(session)
            result = await service.delete_by_id(embedding_id=embedding_id)
            return result
