# -*- coding: utf-8 -*-
"""
Queries GraphQL pour les embeddings vectoriels des pistes.

Rôle:
    Définit les requêtes GraphQL pour récupérer les embeddings vectoriels
    et effectuer des recherches par similarité.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_embeddings_service: TrackEmbeddingsService
    - backend.api.utils.database: get_db_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional, List

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_embeddings_type import (
    TrackEmbeddingsType,
    SimilarTrackResult,
)
from backend.api.services.track_embeddings_service import TrackEmbeddingsService
from backend.api.utils.database import get_db_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackEmbeddingsQuery:
    """
    Queries GraphQL pour les embeddings vectoriels des pistes.
    """

    @strawberry.field
    async def track_embeddings(
        self,
        track_id: int,
        embedding_type: Optional[str] = None,
    ) -> List[TrackEmbeddingsType]:
        """
        Récupère les embeddings d'une piste.

        Args:
            track_id: ID de la piste
            embedding_type: Type d'embedding optionnel (filtre)

        Returns:
            Liste des embeddings de la piste
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            results = await service.get_by_track_id(
                track_id=track_id,
                embedding_type=embedding_type,
            )

            return [
                TrackEmbeddingsType(
                    id=emb.id,
                    track_id=emb.track_id,
                    embedding_type=emb.embedding_type,
                    embedding_source=emb.embedding_source,
                    embedding_model=emb.embedding_model,
                    created_at=emb.created_at,
                    date_added=emb.date_added,
                    date_modified=emb.date_modified,
                )
                for emb in results
            ]

    @strawberry.field
    async def track_embedding_by_id(
        self, embedding_id: int
    ) -> Optional[TrackEmbeddingsType]:
        """
        Récupère un embedding par son ID.

        Args:
            embedding_id: ID de l'embedding

        Returns:
            L'embedding ou None si non trouvé
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            embedding = await service.get_by_id(embedding_id)

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

    @strawberry.field
    async def find_similar_tracks(
        self,
        query_vector: List[float],
        embedding_type: str = "semantic",
        limit: int = 10,
        min_similarity: Optional[float] = None,
        exclude_track_ids: Optional[List[int]] = None,
    ) -> List[SimilarTrackResult]:
        """
        Recherche les pistes similaires à un vecteur donné.

        Args:
            query_vector: Vecteur de recherche (512 dimensions)
            embedding_type: Type d'embedding à rechercher
            limit: Nombre maximum de résultats
            min_similarity: Similarité minimale (0-1)
            exclude_track_ids: IDs de pistes à exclure

        Returns:
            Liste des résultats de similarité
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            results = await service.find_similar(
                query_vector=query_vector,
                embedding_type=embedding_type,
                limit=limit,
                min_similarity=min_similarity,
                exclude_track_ids=exclude_track_ids,
            )

            # Convertir la distance en score de similarité (0-1)
            # Plus la distance est petite, plus la similarité est grande
            return [
                SimilarTrackResult(
                    embedding=TrackEmbeddingsType(
                        id=emb.id,
                        track_id=emb.track_id,
                        embedding_type=emb.embedding_type,
                        embedding_source=emb.embedding_source,
                        embedding_model=emb.embedding_model,
                        created_at=emb.created_at,
                        date_added=emb.date_added,
                        date_modified=emb.date_modified,
                    ),
                    distance=distance,
                    similarity_score=max(0.0, 1.0 - distance),
                )
                for emb, distance in results
            ]

    @strawberry.field
    async def find_similar_tracks_by_track_id(
        self,
        track_id: int,
        embedding_type: str = "semantic",
        limit: int = 10,
        exclude_self: bool = True,
    ) -> List[SimilarTrackResult]:
        """
        Trouve les pistes similaires à une piste donnée.

        Args:
            track_id: ID de la piste de référence
            embedding_type: Type d'embedding à utiliser
            limit: Nombre maximum de résultats
            exclude_self: Exclure la piste de référence

        Returns:
            Liste des résultats de similarité
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            results = await service.find_similar_by_track_id(
                track_id=track_id,
                embedding_type=embedding_type,
                limit=limit,
                exclude_self=exclude_self,
            )

            return [
                SimilarTrackResult(
                    embedding=TrackEmbeddingsType(
                        id=emb.id,
                        track_id=emb.track_id,
                        embedding_type=emb.embedding_type,
                        embedding_source=emb.embedding_source,
                        embedding_model=emb.embedding_model,
                        created_at=emb.created_at,
                        date_added=emb.date_added,
                        date_modified=emb.date_modified,
                    ),
                    distance=distance,
                    similarity_score=max(0.0, 1.0 - distance),
                )
                for emb, distance in results
            ]

    @strawberry.field
    async def embedding_types_count(self) -> dict:
        """
        Retourne le nombre d'embeddings par type.

        Returns:
            Dictionnaire {type: count}
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            counts = await service.get_embedding_types_count()
            return counts

    @strawberry.field
    async def embeddings_statistics(self) -> dict:
        """
        Retourne des statistiques sur les embeddings.

        Returns:
            Dictionnaire des statistiques
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            stats = await service.get_models_statistics()
            return stats

    @strawberry.field
    async def tracks_without_embeddings(
        self,
        embedding_type: str = "semantic",
        limit: int = 100,
    ) -> List[dict]:
        """
        Récupère les IDs des pistes sans embeddings d'un type donné.

        Args:
            embedding_type: Type d'embedding recherché
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans embeddings
        """
        async with get_db_session() as session:
            service = TrackEmbeddingsService(session)
            results = await service.get_tracks_without_embeddings(
                embedding_type=embedding_type,
                limit=limit,
            )
            return results
