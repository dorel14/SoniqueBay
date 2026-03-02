"""
Service pour les opérations bulk (inserts/updates/deletes en masse) via SQLAlchemy async.

Optimisé pour les workers Celery avec connexion directe à Supabase PostgreSQL.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, update, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend_worker.utils.supabase_sqlalchemy import get_async_session, import_models
from backend_worker.utils.logging import logger


class BulkOperationsService:
    """
    Service pour opérations bulk haute performance sur Supabase.
    
    Utilise SQLAlchemy async avec optimisations PostgreSQL pour :
    - Bulk inserts avec ON CONFLICT DO UPDATE (upsert)
    - Batch updates
    - Deletes conditionnels
    """
    
    def __init__(self):
        self.models = import_models()
    
    async def bulk_insert_tracks(
        self,
        tracks_data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> List[int]:
        """
        Insère des pistes en bulk avec upsert sur conflit.
        
        Args:
            tracks_data: Liste des données de pistes
            batch_size: Taille des batches pour contrôler la mémoire
            
        Returns:
            Liste des IDs insérés/mis à jour
        """
        if not tracks_data:
            return []
        
        Track = self.models.get('Track')
        if not Track:
            raise ValueError("Modèle Track non disponible")
        
        inserted_ids = []
        
        async for session in get_async_session():
            try:
                # Traiter par batches pour contrôler la mémoire
                for i in range(0, len(tracks_data), batch_size):
                    batch = tracks_data[i:i + batch_size]
                    
                    # Upsert: INSERT ... ON CONFLICT DO UPDATE
                    stmt = pg_insert(Track).values(batch)
                    update_dict = {
                        c.name: c for c in stmt.excluded if c.name != 'id'
                    }
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_=update_dict
                    )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    # Récupérer les IDs
                    for track in batch:
                        if 'id' in track:
                            inserted_ids.append(track['id'])
                    
                    logger.info(f"[BulkOps] Batch tracks {i//batch_size + 1}: {len(batch)} lignes")
                
                return inserted_ids
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur bulk insert tracks: {e}")
                raise
    
    async def bulk_insert_albums(
        self,
        albums_data: List[Dict[str, Any]],
        batch_size: int = 500
    ) -> List[int]:
        """
        Insère des albums en bulk avec upsert.
        
        Args:
            albums_data: Liste des données d'albums
            batch_size: Taille des batches
            
        Returns:
            Liste des IDs insérés/mis à jour
        """
        if not albums_data:
            return []
        
        Album = self.models.get('Album')
        if not Album:
            raise ValueError("Modèle Album non disponible")
        
        inserted_ids = []
        
        async for session in get_async_session():
            try:
                for i in range(0, len(albums_data), batch_size):
                    batch = albums_data[i:i + batch_size]
                    
                    stmt = pg_insert(Album).values(batch)
                    update_dict = {
                        c.name: c for c in stmt.excluded if c.name != 'id'
                    }
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_=update_dict
                    )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    for album in batch:
                        if 'id' in album:
                            inserted_ids.append(album['id'])
                    
                    logger.info(f"[BulkOps] Batch albums {i//batch_size + 1}: {len(batch)} lignes")
                
                return inserted_ids
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur bulk insert albums: {e}")
                raise
    
    async def bulk_insert_artists(
        self,
        artists_data: List[Dict[str, Any]],
        batch_size: int = 500
    ) -> List[int]:
        """
        Insère des artistes en bulk avec upsert.
        
        Args:
            artists_data: Liste des données d'artistes
            batch_size: Taille des batches
            
        Returns:
            Liste des IDs insérés/mis à jour
        """
        if not artists_data:
            return []
        
        Artist = self.models.get('Artist')
        if not Artist:
            raise ValueError("Modèle Artist non disponible")
        
        inserted_ids = []
        
        async for session in get_async_session():
            try:
                for i in range(0, len(artists_data), batch_size):
                    batch = artists_data[i:i + batch_size]
                    
                    stmt = pg_insert(Artist).values(batch)
                    update_dict = {
                        c.name: c for c in stmt.excluded if c.name != 'id'
                    }
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_=update_dict
                    )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    for artist in batch:
                        if 'id' in artist:
                            inserted_ids.append(artist['id'])
                    
                    logger.info(f"[BulkOps] Batch artists {i//batch_size + 1}: {len(batch)} lignes")
                
                return inserted_ids
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur bulk insert artists: {e}")
                raise
    
    async def bulk_insert_embeddings(
        self,
        embeddings_data: List[Dict[str, Any]],
        batch_size: int = 500
    ) -> int:
        """
        Insère des embeddings en bulk.
        
        Args:
            embeddings_data: Liste des embeddings (track_id, embedding, model_name)
            batch_size: Taille des batches
            
        Returns:
            Nombre d'embeddings insérés
        """
        if not embeddings_data:
            return 0
        
        TrackEmbeddings = self.models.get('TrackEmbeddings')
        if not TrackEmbeddings:
            raise ValueError("Modèle TrackEmbeddings non disponible")
        
        total_inserted = 0
        
        async for session in get_async_session():
            try:
                for i in range(0, len(embeddings_data), batch_size):
                    batch = embeddings_data[i:i + batch_size]
                    
                    stmt = pg_insert(TrackEmbeddings).values(batch)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=['track_id', 'model_name']
                    )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    total_inserted += result.rowcount
                    logger.info(f"[BulkOps] Batch embeddings {i//batch_size + 1}: {result.rowcount} lignes")
                
                return total_inserted
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur bulk insert embeddings: {e}")
                raise
    
    async def bulk_insert_mir_scores(
        self,
        scores_data: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        Insère des scores MIR en bulk avec upsert.
        
        Args:
            scores_data: Liste des scores (track_id, energy_score, etc.)
            batch_size: Taille des batches
            
        Returns:
            Nombre de scores insérés/mis à jour
        """
        if not scores_data:
            return 0
        
        TrackMIRScores = self.models.get('TrackMIRScores')
        if not TrackMIRScores:
            raise ValueError("Modèle TrackMIRScores non disponible")
        
        total_inserted = 0
        
        async for session in get_async_session():
            try:
                for i in range(0, len(scores_data), batch_size):
                    batch = scores_data[i:i + batch_size]
                    
                    stmt = pg_insert(TrackMIRScores).values(batch)
                    update_dict = {
                        c.name: c for c in stmt.excluded if c.name not in ['id', 'track_id']
                    }
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['track_id'],
                        set_=update_dict
                    )
                    
                    result = await session.execute(stmt)
                    await session.commit()
                    
                    total_inserted += result.rowcount
                    logger.info(f"[BulkOps] Batch MIR scores {i//batch_size + 1}: {result.rowcount} lignes")
                
                return total_inserted
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur bulk insert MIR scores: {e}")
                raise
    
    async def update_track_metadata(
        self,
        track_updates: List[Dict[str, Any]]
    ) -> int:
        """
        Met à jour les métadonnées de pistes en batch.
        
        Args:
            track_updates: Liste des mises à jour (doivent contenir 'id')
            
        Returns:
            Nombre de pistes mises à jour
        """
        if not track_updates:
            return 0
        
        Track = self.models.get('Track')
        if not Track:
            raise ValueError("Modèle Track non disponible")
        
        total_updated = 0
        
        async for session in get_async_session():
            try:
                for update_data in track_updates:
                    track_id = update_data.pop('id', None)
                    if not track_id:
                        continue
                    
                    stmt = (
                        update(Track)
                        .where(Track.id == track_id)
                        .values(**update_data)
                    )
                    result = await session.execute(stmt)
                    total_updated += result.rowcount
                
                await session.commit()
                logger.info(f"[BulkOps] Métadonnées mises à jour: {total_updated} pistes")
                return total_updated
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur update metadata: {e}")
                raise
    
    async def delete_orphaned_records(
        self,
        table_name: str,
        condition: Dict[str, Any]
    ) -> int:
        """
        Supprime les enregistrements orphelins selon une condition.
        
        Args:
            table_name: Nom de la table
            condition: Condition de suppression (ex: {'album_id': None})
            
        Returns:
            Nombre de lignes supprimées
        """
        # Mapping table_name -> modèle
        model_map = {
            'tracks': self.models.get('Track'),
            'albums': self.models.get('Album'),
            'artists': self.models.get('Artist'),
        }
        
        Model = model_map.get(table_name)
        if not Model:
            raise ValueError(f"Table {table_name} non supportée")
        
        async for session in get_async_session():
            try:
                stmt = delete(Model)
                for key, value in condition.items():
                    stmt = stmt.where(getattr(Model, key) == value)
                
                result = await session.execute(stmt)
                await session.commit()
                
                logger.info(f"[BulkOps] Orphelins supprimés de {table_name}: {result.rowcount}")
                return result.rowcount
                
            except Exception as e:
                await session.rollback()
                logger.error(f"[BulkOps] Erreur delete orphaned: {e}")
                raise


# Singleton
_bulk_service: Optional[BulkOperationsService] = None


def get_bulk_operations_service() -> BulkOperationsService:
    """Factory pour BulkOperationsService."""
    global _bulk_service
    if _bulk_service is None:
        _bulk_service = BulkOperationsService()
    return _bulk_service


def reset_bulk_operations_service():
    """Reset du singleton."""
    global _bulk_service
    _bulk_service = None


__all__ = [
    'BulkOperationsService',
    'get_bulk_operations_service',
    'reset_bulk_operations_service',
]
