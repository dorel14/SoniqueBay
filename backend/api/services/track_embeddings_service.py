# -*- coding: utf-8 -*-
"""
Service métier pour la gestion des embeddings vectoriels des pistes.

Rôle:
    Fournit les opérations CRUD et les requêtes de similarité vectorielle
    pour les embeddings des pistes musicales. Supporte plusieurs types
    d'embeddings (sémantique, audio, texte) pour les recommandations.

Dépendances:
    - backend.api.models.track_embeddings_model: TrackEmbeddings
    - backend.api.utils.logging: logger
    - sqlalchemy.ext.asyncio: AsyncSession
    - pgvector: pour les opérations vectorielles

Auteur: SoniqueBay Team
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, func, and_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.track_embeddings_model import TrackEmbeddings
from backend.api.utils.logging import logger


class TrackEmbeddingsService:
    """
    Service métier pour la gestion des embeddings vectoriels des pistes.

    Ce service fournit les opérations CRUD pour les embeddings, ainsi que
    des fonctionnalités avancées de recherche par similarité vectorielle
    utilisant l'index HNSW de pgvector.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB

    Example:
        >>> async with async_session() as session:
        ...     service = TrackEmbeddingsService(session)
        ...     similar = await service.find_similar(embedding_vector, limit=10)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialise le service avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
        """
        self.session = session

    async def get_by_id(self, embedding_id: int) -> Optional[TrackEmbeddings]:
        """
        Récupère un embedding par son ID.

        Args:
            embedding_id: ID de l'embedding

        Returns:
            L'embedding ou None si non trouvé
        """
        result = await self.session.execute(
            select(TrackEmbeddings).where(TrackEmbeddings.id == embedding_id)
        )
        return result.scalars().first()

    async def get_by_track_id(
        self,
        track_id: int,
        embedding_type: Optional[str] = None
    ) -> List[TrackEmbeddings]:
        """
        Récupère les embeddings d'une piste.

        Args:
            track_id: ID de la piste
            embedding_type: Type d'embedding optionnel (filtre)

        Returns:
            Liste des embeddings de la piste
        """
        query = select(TrackEmbeddings).where(
            TrackEmbeddings.track_id == track_id
        )

        if embedding_type:
            query = query.where(
                TrackEmbeddings.embedding_type == embedding_type
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_track_ids(
        self,
        track_ids: List[int],
        embedding_type: Optional[str] = None
    ) -> List[TrackEmbeddings]:
        """
        Récupère les embeddings pour plusieurs pistes.

        Args:
            track_ids: Liste des IDs de pistes
            embedding_type: Type d'embedding optionnel (filtre)

        Returns:
            Liste des embeddings trouvés
        """
        if not track_ids:
            return []

        query = select(TrackEmbeddings).where(
            TrackEmbeddings.track_id.in_(track_ids)
        )

        if embedding_type:
            query = query.where(
                TrackEmbeddings.embedding_type == embedding_type
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_single_by_track_id(
        self,
        track_id: int,
        embedding_type: str = 'semantic'
    ) -> Optional[TrackEmbeddings]:
        """
        Récupère un embedding unique d'une piste par type.

        Args:
            track_id: ID de la piste
            embedding_type: Type d'embedding (défaut: 'semantic')

        Returns:
            L'embedding ou None si non trouvé
        """
        result = await self.session.execute(
            select(TrackEmbeddings)
            .where(
                and_(
                    TrackEmbeddings.track_id == track_id,
                    TrackEmbeddings.embedding_type == embedding_type
                )
            )
        )
        return result.scalars().first()

    async def create(
        self,
        track_id: int,
        vector: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> TrackEmbeddings:
        """
        Crée un nouvel embedding pour une piste.

        Args:
            track_id: ID de la piste
            vector: Vecteur d'embedding (512 dimensions)
            embedding_type: Type d'embedding (semantic, audio, text, etc.)
            embedding_source: Source de vectorisation (ollama, etc.)
            embedding_model: Modèle utilisé (nomic-embed-text, etc.)

        Returns:
            L'embedding créé

        Raises:
            IntegrityError: Si un embedding du même type existe déjà pour cette piste
            ValueError: Si le vecteur n'a pas 512 dimensions
        """
        if len(vector) != 512:
            raise ValueError(f"Le vecteur doit avoir 512 dimensions, pas {len(vector)}")

        embedding = TrackEmbeddings(
            track_id=track_id,
            vector=vector,
            embedding_type=embedding_type,
            embedding_source=embedding_source,
            embedding_model=embedding_model,
            created_at=datetime.utcnow(),
        )

        try:
            self.session.add(embedding)
            await self.session.commit()
            await self.session.refresh(embedding)
            logger.info(
                f"[EMBEDDINGS] Créé pour track_id={track_id}, type={embedding_type}"
            )
            return embedding
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"[EMBEDDINGS] Erreur création pour track_id={track_id}: {e}"
            )
            raise

    async def create_or_update(
        self,
        track_id: int,
        vector: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> TrackEmbeddings:
        """
        Crée ou met à jour un embedding pour une piste.

        Args:
            track_id: ID de la piste
            vector: Vecteur d'embedding (512 dimensions)
            embedding_type: Type d'embedding
            embedding_source: Source de vectorisation
            embedding_model: Modèle utilisé

        Returns:
            L'embedding créé ou mis à jour
        """
        existing = await self.get_single_by_track_id(track_id, embedding_type)

        if existing:
            return await self.update(
                track_id=track_id,
                embedding_type=embedding_type,
                vector=vector,
                embedding_source=embedding_source,
                embedding_model=embedding_model,
            )
        else:
            return await self.create(
                track_id=track_id,
                vector=vector,
                embedding_type=embedding_type,
                embedding_source=embedding_source,
                embedding_model=embedding_model,
            )

    async def update(
        self,
        track_id: int,
        embedding_type: str,
        vector: Optional[List[float]] = None,
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> Optional[TrackEmbeddings]:
        """
        Met à jour un embedding existant.

        Args:
            track_id: ID de la piste
            embedding_type: Type d'embedding
            vector: Nouveau vecteur (optionnel)
            embedding_source: Nouvelle source (optionnel)
            embedding_model: Nouveau modèle (optionnel)

        Returns:
            L'embedding mis à jour ou None si non trouvé
        """
        embedding = await self.get_single_by_track_id(track_id, embedding_type)
        if not embedding:
            logger.warning(
                f"[EMBEDDINGS] Mise à jour impossible: track_id={track_id}, "
                f"type={embedding_type} non trouvé"
            )
            return None

        if vector is not None:
            if len(vector) != 512:
                raise ValueError(
                    f"Le vecteur doit avoir 512 dimensions, pas {len(vector)}"
                )
            embedding.vector = vector

        if embedding_source is not None:
            embedding.embedding_source = embedding_source

        if embedding_model is not None:
            embedding.embedding_model = embedding_model

        embedding.created_at = datetime.utcnow()
        embedding.date_modified = func.now()

        await self.session.commit()
        await self.session.refresh(embedding)
        logger.info(
            f"[EMBEDDINGS] Mis à jour pour track_id={track_id}, type={embedding_type}"
        )
        return embedding

    async def delete(
        self,
        track_id: int,
        embedding_type: Optional[str] = None
    ) -> bool:
        """
        Supprime les embeddings d'une piste.

        Args:
            track_id: ID de la piste
            embedding_type: Type spécifique à supprimer (None = tous)

        Returns:
            True si supprimé, False si non trouvé
        """
        query = select(TrackEmbeddings).where(
            TrackEmbeddings.track_id == track_id
        )

        if embedding_type:
            query = query.where(
                TrackEmbeddings.embedding_type == embedding_type
            )

        result = await self.session.execute(query)
        embeddings = result.scalars().all()

        if not embeddings:
            return False

        for embedding in embeddings:
            await self.session.delete(embedding)

        await self.session.commit()
        logger.info(
            f"[EMBEDDINGS] Supprimés pour track_id={track_id}, "
            f"type={embedding_type or 'all'}"
        )
        return True

    async def delete_by_id(self, embedding_id: int) -> bool:
        """
        Supprime un embedding par son ID.

        Args:
            embedding_id: ID de l'embedding

        Returns:
            True si supprimé, False si non trouvé
        """
        embedding = await self.get_by_id(embedding_id)
        if not embedding:
            return False

        await self.session.delete(embedding)
        await self.session.commit()
        logger.info(f"[EMBEDDINGS] Supprimé id={embedding_id}")
        return True

    async def find_similar(
        self,
        query_vector: List[float],
        embedding_type: str = 'semantic',
        limit: int = 10,
        min_similarity: Optional[float] = None,
        exclude_track_ids: Optional[List[int]] = None,
    ) -> List[Tuple[TrackEmbeddings, float]]:
        """
        Recherche les embeddings les plus similaires à un vecteur donné.

        Utilise l'opérateur de distance euclidienne de pgvector pour trouver
        les vecteurs les plus proches.

        Args:
            query_vector: Vecteur de recherche (512 dimensions)
            embedding_type: Type d'embedding à rechercher
            limit: Nombre maximum de résultats
            min_similarity: Distance maximale (similarité minimale)
            exclude_track_ids: IDs de pistes à exclure des résultats

        Returns:
            Liste de tuples (embedding, distance) ordonnée par similarité
        """
        if len(query_vector) != 512:
            raise ValueError(
                f"Le vecteur de recherche doit avoir 512 dimensions, pas {len(query_vector)}"
            )

        # Construction de la requête avec distance euclidienne
        # pgvector utilise l'opérateur <-> pour la distance L2
        query = select(
            TrackEmbeddings,
            TrackEmbeddings.vector.l2_distance(query_vector).label('distance')
        ).where(
            TrackEmbeddings.embedding_type == embedding_type
        )

        if exclude_track_ids:
            query = query.where(
                ~TrackEmbeddings.track_id.in_(exclude_track_ids)
            )

        # Ordonner par distance croissante (plus proche d'abord)
        query = query.order_by('distance').limit(limit)

        result = await self.session.execute(query)
        results = result.all()

        # Filtrer par similarité minimale si spécifiée
        if min_similarity is not None:
            results = [
                (emb, dist) for emb, dist in results
                if dist <= min_similarity
            ]

        return results

    async def find_similar_by_track_id(
        self,
        track_id: int,
        embedding_type: str = 'semantic',
        limit: int = 10,
        exclude_self: bool = True,
    ) -> List[Tuple[TrackEmbeddings, float]]:
        """
        Trouve les pistes similaires à une piste donnée.

        Args:
            track_id: ID de la piste de référence
            embedding_type: Type d'embedding à utiliser
            limit: Nombre maximum de résultats
            exclude_self: Exclure la piste de référence des résultats

        Returns:
            Liste de tuples (embedding, distance) ordonnée par similarité
        """
        reference = await self.get_single_by_track_id(track_id, embedding_type)
        if not reference:
            logger.warning(
                f"[EMBEDDINGS] Piste de référence non trouvée: "
                f"track_id={track_id}, type={embedding_type}"
            )
            return []

        exclude_ids = [track_id] if exclude_self else None

        return await self.find_similar(
            query_vector=reference.vector,
            embedding_type=embedding_type,
            limit=limit,
            exclude_track_ids=exclude_ids,
        )

    async def find_similar_batch(
        self,
        query_vectors: List[List[float]],
        embedding_type: str = 'semantic',
        limit_per_query: int = 5,
    ) -> List[List[Tuple[TrackEmbeddings, float]]]:
        """
        Recherche des embeddings similaires pour plusieurs vecteurs.

        Args:
            query_vectors: Liste de vecteurs de recherche
            embedding_type: Type d'embedding
            limit_per_query: Nombre de résultats par requête

        Returns:
            Liste de listes de résultats (une par vecteur de recherche)
        """
        results = []
        for vector in query_vectors:
            similar = await self.find_similar(
                query_vector=vector,
                embedding_type=embedding_type,
                limit=limit_per_query,
            )
            results.append(similar)
        return results

    async def get_tracks_without_embeddings(
        self,
        embedding_type: str = 'semantic',
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les IDs des pistes sans embeddings d'un type donné.

        Utile pour les tâches de vectorisation à effectuer.

        Args:
            embedding_type: Type d'embedding recherché
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans embeddings
        """
        from backend.api.models.tracks_model import Track

        # Sous-requête pour les pistes ayant déjà l'embedding
        subquery = select(TrackEmbeddings.track_id).where(
            TrackEmbeddings.embedding_type == embedding_type
        )

        # Requête principale pour les pistes sans cet embedding
        result = await self.session.execute(
            select(Track.id)
            .where(~Track.id.in_(subquery))
            .limit(limit)
        )

        return [{'track_id': row[0]} for row in result.all()]

    async def get_embedding_types_count(self) -> Dict[str, int]:
        """
        Compte le nombre d'embeddings par type.

        Returns:
            Dictionnaire {type: count}
        """
        result = await self.session.execute(
            select(
                TrackEmbeddings.embedding_type,
                func.count(TrackEmbeddings.id)
            ).group_by(TrackEmbeddings.embedding_type)
        )

        return {row[0]: row[1] for row in result.all()}

    async def get_models_statistics(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les modèles d'embedding utilisés.

        Returns:
            Dictionnaire des statistiques par modèle
        """
        stats = {}

        # Nombre total d'embeddings
        total_result = await self.session.execute(
            select(func.count(TrackEmbeddings.id))
        )
        stats['total_embeddings'] = total_result.scalar() or 0

        # Par type
        stats['by_type'] = await self.get_embedding_types_count()

        # Par modèle et source
        model_result = await self.session.execute(
            select(
                TrackEmbeddings.embedding_model,
                TrackEmbeddings.embedding_source,
                func.count(TrackEmbeddings.id)
            )
            .group_by(
                TrackEmbeddings.embedding_model,
                TrackEmbeddings.embedding_source
            )
        )

        stats['by_model_source'] = [
            {
                'model': row[0] or 'unknown',
                'source': row[1] or 'unknown',
                'count': row[2]
            }
            for row in model_result.all()
        ]

        return stats

    async def get_average_vector(
        self,
        track_ids: List[int],
        embedding_type: str = 'semantic'
    ) -> Optional[List[float]]:
        """
        Calcule le vecteur moyen pour un ensemble de pistes.

        Utile pour créer des playlists ou recommandations basées sur
        plusieurs pistes.

        Args:
            track_ids: Liste des IDs de pistes
            embedding_type: Type d'embedding

        Returns:
            Le vecteur moyen ou None si aucun embedding trouvé
        """
        if not track_ids:
            return None

        # Utiliser SQL pour calculer la moyenne des vecteurs
        result = await self.session.execute(
            select(
                func.avg(TrackEmbeddings.vector).label('avg_vector')
            )
            .where(
                and_(
                    TrackEmbeddings.track_id.in_(track_ids),
                    TrackEmbeddings.embedding_type == embedding_type
                )
            )
        )

        avg_vector = result.scalar()
        return avg_vector

    async def find_tracks_in_vector_range(
        self,
        center_vector: List[float],
        radius: float,
        embedding_type: str = 'semantic',
        limit: int = 100
    ) -> List[TrackEmbeddings]:
        """
        Trouve tous les embeddings dans une sphère de rayon donné.

        Args:
            center_vector: Centre de la sphère
            radius: Rayon de recherche (distance maximale)
            embedding_type: Type d'embedding
            limit: Nombre maximum de résultats

        Returns:
            Liste des embeddings dans la sphère
        """
        if len(center_vector) != 512:
            raise ValueError(
                f"Le vecteur centre doit avoir 512 dimensions, pas {len(center_vector)}"
            )

        # Requête avec filtre de distance
        query = select(TrackEmbeddings).where(
            and_(
                TrackEmbeddings.embedding_type == embedding_type,
                TrackEmbeddings.vector.l2_distance(center_vector) <= radius
            )
        ).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
