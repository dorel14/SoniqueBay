# -*- coding: utf-8 -*-
"""
Service métier pour la gestion des métadonnées enrichies des pistes.

Rôle:
    Fournit les opérations CRUD pour les métadonnées extensibles des pistes
    sous forme de clé-valeur, permettant d'ajouter des informations de
    sources externes (Last.fm, ListenBrainz, etc.) sans modifier le schéma.

Dépendances:
    - backend.api.models.track_metadata_model: TrackMetadata
    - backend.api.utils.logging: logger
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.track_metadata_model import TrackMetadata
from backend.api.utils.logging import logger


class TrackMetadataService:
    """
    Service métier pour la gestion des métadonnées enrichies des pistes.

    Ce service fournit les opérations CRUD pour les métadonnées extensibles,
    permettant de stocker des informations arbitraires de sources externes
    sous forme de clé-valeur avec traçabilité de la source.

    Attributes:
        session: Session SQLAlchemy asynchrone pour les opérations DB

    Example:
        >>> async with async_session() as session:
        ...     service = TrackMetadataService(session)
        ...     metadata = await service.get_by_track_id(1)
    """

    def __init__(self, session: AsyncSession):
        """
        Initialise le service avec une session de base de données.

        Args:
            session: Session SQLAlchemy asynchrone
        """
        self.session = session

    async def get_by_id(self, metadata_id: int) -> Optional[TrackMetadata]:
        """
        Récupère une métadonnée par son ID.

        Args:
            metadata_id: ID de la métadonnée

        Returns:
            La métadonnée ou None si non trouvée
        """
        result = await self.session.execute(
            select(TrackMetadata).where(TrackMetadata.id == metadata_id)
        )
        return result.scalars().first()

    async def get_by_track_id(
        self,
        track_id: int,
        metadata_key: Optional[str] = None,
        metadata_source: Optional[str] = None
    ) -> List[TrackMetadata]:
        """
        Récupère les métadonnées d'une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée optionnelle (filtre)
            metadata_source: Source optionnelle (filtre)

        Returns:
            Liste des métadonnées de la piste
        """
        query = select(TrackMetadata).where(
            TrackMetadata.track_id == track_id
        )

        if metadata_key:
            query = query.where(
                TrackMetadata.metadata_key == metadata_key
            )

        if metadata_source:
            query = query.where(
                TrackMetadata.metadata_source == metadata_source
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_track_ids(
        self,
        track_ids: List[int],
        metadata_key: Optional[str] = None
    ) -> List[TrackMetadata]:
        """
        Récupère les métadonnées pour plusieurs pistes.

        Args:
            track_ids: Liste des IDs de pistes
            metadata_key: Clé de métadonnée optionnelle (filtre)

        Returns:
            Liste des métadonnées trouvées
        """
        if not track_ids:
            return []

        query = select(TrackMetadata).where(
            TrackMetadata.track_id.in_(track_ids)
        )

        if metadata_key:
            query = query.where(
                TrackMetadata.metadata_key == metadata_key
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_single_metadata(
        self,
        track_id: int,
        metadata_key: str,
        metadata_source: Optional[str] = None
    ) -> Optional[TrackMetadata]:
        """
        Récupère une métadonnée spécifique d'une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            metadata_source: Source optionnelle (filtre)

        Returns:
            La métadonnée ou None si non trouvée
        """
        query = select(TrackMetadata).where(
            and_(
                TrackMetadata.track_id == track_id,
                TrackMetadata.metadata_key == metadata_key
            )
        )

        if metadata_source:
            query = query.where(
                TrackMetadata.metadata_source == metadata_source
            )

        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_metadata_value(
        self,
        track_id: int,
        metadata_key: str,
        default: Any = None
    ) -> Any:
        """
        Récupère la valeur d'une métadonnée spécifique.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            default: Valeur par défaut si non trouvée

        Returns:
            La valeur de la métadonnée ou la valeur par défaut
        """
        metadata = await self.get_single_metadata(track_id, metadata_key)
        return metadata.metadata_value if metadata else default

    async def create(
        self,
        track_id: int,
        metadata_key: str,
        metadata_value: Optional[str] = None,
        metadata_source: Optional[str] = None,
    ) -> TrackMetadata:
        """
        Crée une nouvelle métadonnée pour une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            metadata_value: Valeur de la métadonnée
            metadata_source: Source de la métadonnée (lastfm, listenbrainz, etc.)

        Returns:
            La métadonnée créée

        Raises:
            IntegrityError: Si une métadonnée identique existe déjà
        """
        metadata = TrackMetadata(
            track_id=track_id,
            metadata_key=metadata_key,
            metadata_value=metadata_value,
            metadata_source=metadata_source,
            created_at=datetime.utcnow(),
        )

        try:
            self.session.add(metadata)
            await self.session.commit()
            await self.session.refresh(metadata)
            logger.info(
                f"[METADATA] Créé pour track_id={track_id}, key={metadata_key}"
            )
            return metadata
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(
                f"[METADATA] Erreur création pour track_id={track_id}, "
                f"key={metadata_key}: {e}"
            )
            raise

    async def create_or_update(
        self,
        track_id: int,
        metadata_key: str,
        metadata_value: Optional[str] = None,
        metadata_source: Optional[str] = None,
    ) -> TrackMetadata:
        """
        Crée ou met à jour une métadonnée pour une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            metadata_value: Valeur de la métadonnée
            metadata_source: Source de la métadonnée

        Returns:
            La métadonnée créée ou mise à jour
        """
        existing = await self.get_single_metadata(
            track_id, metadata_key, metadata_source
        )

        if existing:
            return await self.update(
                track_id=track_id,
                metadata_key=metadata_key,
                metadata_value=metadata_value,
                metadata_source=metadata_source,
            )
        else:
            return await self.create(
                track_id=track_id,
                metadata_key=metadata_key,
                metadata_value=metadata_value,
                metadata_source=metadata_source,
            )

    async def update(
        self,
        track_id: int,
        metadata_key: str,
        metadata_value: Optional[str] = None,
        metadata_source: Optional[str] = None,
    ) -> Optional[TrackMetadata]:
        """
        Met à jour une métadonnée existante.

        Args:
            track_id: ID de la piste
            metadata_key: Clé de métadonnée
            metadata_value: Nouvelle valeur (optionnel)
            metadata_source: Nouvelle source (optionnel)

        Returns:
            La métadonnée mise à jour ou None si non trouvée
        """
        metadata = await self.get_single_metadata(
            track_id, metadata_key, metadata_source
        )

        if not metadata:
            logger.warning(
                f"[METADATA] Mise à jour impossible: track_id={track_id}, "
                f"key={metadata_key} non trouvé"
            )
            return None

        if metadata_value is not None:
            metadata.metadata_value = metadata_value

        if metadata_source is not None:
            metadata.metadata_source = metadata_source

        metadata.created_at = datetime.utcnow()
        metadata.date_modified = func.now()

        await self.session.commit()
        await self.session.refresh(metadata)
        logger.info(
            f"[METADATA] Mis à jour pour track_id={track_id}, key={metadata_key}"
        )
        return metadata

    async def delete(
        self,
        track_id: int,
        metadata_key: Optional[str] = None,
        metadata_source: Optional[str] = None
    ) -> bool:
        """
        Supprime les métadonnées d'une piste.

        Args:
            track_id: ID de la piste
            metadata_key: Clé spécifique à supprimer (None = toutes)
            metadata_source: Source spécifique à supprimer (None = toutes)

        Returns:
            True si supprimé, False si non trouvé
        """
        query = select(TrackMetadata).where(
            TrackMetadata.track_id == track_id
        )

        if metadata_key:
            query = query.where(
                TrackMetadata.metadata_key == metadata_key
            )

        if metadata_source:
            query = query.where(
                TrackMetadata.metadata_source == metadata_source
            )

        result = await self.session.execute(query)
        metadata_entries = result.scalars().all()

        if not metadata_entries:
            return False

        for metadata in metadata_entries:
            await self.session.delete(metadata)

        await self.session.commit()
        logger.info(
            f"[METADATA] Supprimés pour track_id={track_id}, "
            f"key={metadata_key or 'all'}, source={metadata_source or 'all'}"
        )
        return True

    async def delete_by_id(self, metadata_id: int) -> bool:
        """
        Supprime une métadonnée par son ID.

        Args:
            metadata_id: ID de la métadonnée

        Returns:
            True si supprimé, False si non trouvé
        """
        metadata = await self.get_by_id(metadata_id)
        if not metadata:
            return False

        await self.session.delete(metadata)
        await self.session.commit()
        logger.info(f"[METADATA] Supprimé id={metadata_id}")
        return True

    async def get_tracks_without_metadata(
        self,
        metadata_key: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les IDs des pistes sans métadonnées (optionnellement par clé).

        Utile pour les tâches d'enrichissement à effectuer.

        Args:
            metadata_key: Clé de métadonnée spécifique (None = toutes)
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans métadonnées
        """
        from backend.api.models.tracks_model import Track

        # Sous-requête pour les pistes ayant des métadonnées
        subquery = select(TrackMetadata.track_id)
        if metadata_key:
            subquery = subquery.where(
                TrackMetadata.metadata_key == metadata_key
            )

        # Requête principale pour les pistes sans métadonnées
        result = await self.session.execute(
            select(Track.id)
            .where(~Track.id.in_(subquery))
            .limit(limit)
        )

        return [{'track_id': row[0]} for row in result.all()]

    async def search_by_key(
        self,
        metadata_key: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackMetadata]:
        """
        Recherche les métadonnées par clé.

        Args:
            metadata_key: Clé de métadonnée à rechercher
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        result = await self.session.execute(
            select(TrackMetadata)
            .where(TrackMetadata.metadata_key == metadata_key)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_key_prefix(
        self,
        key_prefix: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackMetadata]:
        """
        Recherche les métadonnées dont la clé commence par un préfixe.

        Args:
            key_prefix: Préfixe de la clé
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        result = await self.session.execute(
            select(TrackMetadata)
            .where(TrackMetadata.metadata_key.ilike(f"{key_prefix}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_value(
        self,
        metadata_value: str,
        exact_match: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackMetadata]:
        """
        Recherche les métadonnées par valeur.

        Args:
            metadata_value: Valeur à rechercher
            exact_match: Si True, recherche exacte, sinon recherche partielle
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées correspondantes
        """
        if exact_match:
            condition = TrackMetadata.metadata_value == metadata_value
        else:
            condition = TrackMetadata.metadata_value.ilike(f"%{metadata_value}%")

        result = await self.session.execute(
            select(TrackMetadata)
            .where(condition)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_source(
        self,
        metadata_source: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[TrackMetadata]:
        """
        Recherche les métadonnées par source.

        Args:
            metadata_source: Source à rechercher (lastfm, listenbrainz, etc.)
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des métadonnées de cette source
        """
        result = await self.session.execute(
            select(TrackMetadata)
            .where(TrackMetadata.metadata_source == metadata_source)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_metadata_as_dict(
        self,
        track_id: int,
        metadata_source: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Récupère toutes les métadonnées d'une piste sous forme de dictionnaire.

        Args:
            track_id: ID de la piste
            metadata_source: Source optionnelle (filtre)

        Returns:
            Dictionnaire {clé: valeur} des métadonnées
        """
        metadata_list = await self.get_by_track_id(
            track_id, metadata_source=metadata_source
        )
        return {
            m.metadata_key: m.metadata_value
            for m in metadata_list
            if m.metadata_value is not None
        }

    async def get_metadata_keys_statistics(self) -> Dict[str, int]:
        """
        Compte le nombre de métadonnées par clé.

        Returns:
            Dictionnaire {clé: count}
        """
        result = await self.session.execute(
            select(
                TrackMetadata.metadata_key,
                func.count(TrackMetadata.id)
            ).group_by(TrackMetadata.metadata_key)
        )

        return {row[0]: row[1] for row in result.all()}

    async def get_source_statistics(self) -> Dict[str, int]:
        """
        Compte le nombre de métadonnées par source.

        Returns:
            Dictionnaire {source: count}
        """
        result = await self.session.execute(
            select(
                TrackMetadata.metadata_source,
                func.count(TrackMetadata.id)
            ).group_by(TrackMetadata.metadata_source)
        )

        return {
            (row[0] or 'unknown'): row[1]
            for row in result.all()
        }

    async def get_metadata_statistics(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur les métadonnées.

        Returns:
            Dictionnaire des statistiques globales
        """
        stats = {}

        # Nombre total de métadonnées
        total_result = await self.session.execute(
            select(func.count(TrackMetadata.id))
        )
        stats['total_entries'] = total_result.scalar() or 0

        # Nombre de pistes ayant des métadonnées
        tracks_result = await self.session.execute(
            select(func.count(func.distinct(TrackMetadata.track_id)))
        )
        stats['tracks_with_metadata'] = tracks_result.scalar() or 0

        # Par clé
        stats['by_key'] = await self.get_metadata_keys_statistics()

        # Par source
        stats['by_source'] = await self.get_source_statistics()

        return stats

    async def batch_create(
        self,
        track_id: int,
        metadata_dict: Dict[str, str],
        metadata_source: Optional[str] = None
    ) -> List[TrackMetadata]:
        """
        Crée plusieurs métadonnées pour une piste en une seule opération.

        Args:
            track_id: ID de la piste
            metadata_dict: Dictionnaire {clé: valeur} des métadonnées
            metadata_source: Source commune pour toutes les métadonnées

        Returns:
            Liste des métadonnées créées
        """
        created = []

        for key, value in metadata_dict.items():
            try:
                metadata = await self.create_or_update(
                    track_id=track_id,
                    metadata_key=key,
                    metadata_value=value,
                    metadata_source=metadata_source,
                )
                created.append(metadata)
            except IntegrityError:
                # Ignorer les doublons
                logger.warning(
                    f"[METADATA] Doublon ignoré pour track_id={track_id}, key={key}"
                )
                continue

        logger.info(
            f"[METADATA] Batch créé: {len(created)} entrées pour track_id={track_id}"
        )
        return created
