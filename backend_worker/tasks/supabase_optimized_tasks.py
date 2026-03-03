"""
Tâches Celery optimisées pour Supabase avec SQLAlchemy async bulk operations.

Ces tâches remplacent les anciennes tâches en utilisant :
- Connexion SQLAlchemy async directe à Supabase PostgreSQL
- Bulk inserts/updates pour performance maximale
- Pas d'appels API HTTP (trop lents pour ETL)
"""

import asyncio
from typing import List, Dict, Any
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from backend_worker.services.bulk_operations_service import get_bulk_operations_service
from backend_worker.utils.supabase_sqlalchemy import test_connection
from backend_worker.utils.logging import logger


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='insert',
    time_limit=3600,  # 1h pour gros volumes
    soft_time_limit=3300,
)
def bulk_insert_tracks_task(self, tracks_data: List[Dict[str, Any]], batch_size: int = 1000):
    """
    Tâche Celery pour insertion bulk de pistes.
    
    Args:
        tracks_data: Liste des pistes à insérer
        batch_size: Taille des batches
        
    Returns:
        Dict avec nombre d'insertions et IDs
    """
    async def _execute():
        try:
            logger.info(f"[BulkTask] Démarrage insertion de {len(tracks_data)} pistes")
            
            # Test connexion
            if not await test_connection():
                raise ConnectionError("Impossible de se connecter à Supabase")
            
            # Service de bulk operations
            bulk_service = get_bulk_operations_service()
            
            # Exécution bulk insert avec upsert
            inserted_ids = await bulk_service.bulk_insert_tracks(tracks_data, batch_size)
            
            result = {
                "status": "success",
                "total_processed": len(tracks_data),
                "inserted_or_updated": len(inserted_ids),
                "sample_ids": inserted_ids[:5] if inserted_ids else [],
            }
            
            logger.info(f"[BulkTask] Succès: {result['inserted_or_updated']} pistes insérées/mises à jour")
            return result
            
        except Exception as exc:
            logger.error(f"[BulkTask] Erreur: {exc}")
            raise exc
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        if self.request.retries < self.max_retries:
            logger.info(f"[BulkTask] Retry {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            logger.error("[BulkTask] Max retries exceeded")
            raise MaxRetriesExceededError(f"Échec après {self.max_retries} tentatives: {exc}")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue='insert',
    time_limit=1800,
)
def bulk_insert_albums_task(self, albums_data: List[Dict[str, Any]], batch_size: int = 500):
    """
    Tâche Celery pour insertion bulk d'albums.
    
    Args:
        albums_data: Liste des albums à insérer
        batch_size: Taille des batches
        
    Returns:
        Dict avec résultat de l'opération
    """
    async def _execute():
        logger.info(f"[BulkTask] Démarrage insertion de {len(albums_data)} albums")
        
        bulk_service = get_bulk_operations_service()
        inserted_ids = await bulk_service.bulk_insert_albums(albums_data, batch_size)
        
        return {
            "status": "success",
            "total_processed": len(albums_data),
            "inserted_or_updated": len(inserted_ids),
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur albums: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue='insert',
    time_limit=1800,
)
def bulk_insert_artists_task(self, artists_data: List[Dict[str, Any]], batch_size: int = 500):
    """
    Tâche Celery pour insertion bulk d'artistes.
    
    Args:
        artists_data: Liste des artistes à insérer
        batch_size: Taille des batches
        
    Returns:
        Dict avec résultat de l'opération
    """
    async def _execute():
        logger.info(f"[BulkTask] Démarrage insertion de {len(artists_data)} artistes")
        
        bulk_service = get_bulk_operations_service()
        inserted_ids = await bulk_service.bulk_insert_artists(artists_data, batch_size)
        
        return {
            "status": "success",
            "total_processed": len(artists_data),
            "inserted_or_updated": len(inserted_ids),
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur artistes: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='insert',
    time_limit=3600,
)
def bulk_insert_embeddings_task(self, embeddings_data: List[Dict[str, Any]], batch_size: int = 500):
    """
    Tâche Celery pour insertion bulk d'embeddings.
    
    Args:
        embeddings_data: Liste des embeddings (track_id, embedding, model_name)
        batch_size: Taille des batches
        
    Returns:
        Dict avec nombre d'embeddings insérés
    """
    async def _execute():
        logger.info(f"[BulkTask] Démarrage insertion de {len(embeddings_data)} embeddings")
        
        bulk_service = get_bulk_operations_service()
        total_inserted = await bulk_service.bulk_insert_embeddings(embeddings_data, batch_size)
        
        return {
            "status": "success",
            "total_processed": len(embeddings_data),
            "inserted": total_inserted,
            "skipped": len(embeddings_data) - total_inserted,  # Doublons
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur embeddings: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='insert',
    time_limit=3600,
)
def bulk_insert_mir_scores_task(self, scores_data: List[Dict[str, Any]], batch_size: int = 1000):
    """
    Tâche Celery pour insertion bulk de scores MIR.
    
    Args:
        scores_data: Liste des scores (track_id, energy_score, etc.)
        batch_size: Taille des batches
        
    Returns:
        Dict avec nombre de scores insérés/mis à jour
    """
    async def _execute():
        logger.info(f"[BulkTask] Démarrage insertion de {len(scores_data)} scores MIR")
        
        bulk_service = get_bulk_operations_service()
        total_inserted = await bulk_service.bulk_insert_mir_scores(scores_data, batch_size)
        
        return {
            "status": "success",
            "total_processed": len(scores_data),
            "inserted_or_updated": total_inserted,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur MIR scores: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue='batch',
    time_limit=1800,
)
def update_tracks_metadata_task(self, updates: List[Dict[str, Any]]):
    """
    Tâche Celery pour mise à jour batch des métadonnées.
    
    Args:
        updates: Liste des mises à jour (doivent contenir 'id')
        
    Returns:
        Dict avec nombre de mises à jour
    """
    async def _execute():
        logger.info(f"[BulkTask] Démarrage mise à jour de {len(updates)} pistes")
        
        bulk_service = get_bulk_operations_service()
        total_updated = await bulk_service.update_track_metadata(updates)
        
        return {
            "status": "success",
            "total_updated": total_updated,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur update metadata: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue='maintenance',
    time_limit=900,
)
def cleanup_orphaned_records_task(self, table_name: str, condition: Dict[str, Any]):
    """
    Tâche Celery pour nettoyage des enregistrements orphelins.
    
    Args:
        table_name: Nom de la table ('tracks', 'albums', 'artists')
        condition: Condition de suppression
        
    Returns:
        Dict avec nombre de suppressions
    """
    async def _execute():
        logger.info(f"[BulkTask] Nettoyage orphelins dans {table_name}")
        
        bulk_service = get_bulk_operations_service()
        deleted_count = await bulk_service.delete_orphaned_records(table_name, condition)
        
        return {
            "status": "success",
            "table": table_name,
            "deleted_count": deleted_count,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur cleanup: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='insert',
    time_limit=7200,  # 2h pour scan complet
)
def process_scan_batch_task(self, batch_data: Dict[str, Any]):
    """
    Tâche Celery pour traiter un batch de scan complet.
    
    Combine les insertions d'artistes, albums et pistes en une seule tâche.
    
    Args:
        batch_data: Dict avec 'artists', 'albums', 'tracks'
        
    Returns:
        Dict avec résumé des opérations
    """
    async def _execute():
        logger.info("[BulkTask] Traitement batch de scan")
        
        bulk_service = get_bulk_operations_service()
        results = {
            "artists": {"processed": 0, "inserted": 0},
            "albums": {"processed": 0, "inserted": 0},
            "tracks": {"processed": 0, "inserted": 0},
        }
        
        # 1. Insérer les artistes d'abord (pour les FK)
        artists_data = batch_data.get('artists', [])
        if artists_data:
            artist_ids = await bulk_service.bulk_insert_artists(artists_data)
            results["artists"] = {
                "processed": len(artists_data),
                "inserted": len(artist_ids),
            }
            logger.info(f"[BulkTask] Artistes: {len(artist_ids)} insérés")
        
        # 2. Insérer les albums (dépendent des artistes)
        albums_data = batch_data.get('albums', [])
        if albums_data:
            album_ids = await bulk_service.bulk_insert_albums(albums_data)
            results["albums"] = {
                "processed": len(albums_data),
                "inserted": len(album_ids),
            }
            logger.info(f"[BulkTask] Albums: {len(album_ids)} insérés")
        
        # 3. Insérer les pistes (dépendent des albums et artistes)
        tracks_data = batch_data.get('tracks', [])
        if tracks_data:
            track_ids = await bulk_service.bulk_insert_tracks(tracks_data)
            results["tracks"] = {
                "processed": len(tracks_data),
                "inserted": len(track_ids),
            }
            logger.info(f"[BulkTask] Pistes: {len(track_ids)} insérées")
        
        return {
            "status": "success",
            "results": results,
        }
    
    try:
        return asyncio.run(_execute())
    except Exception as exc:
        logger.error(f"[BulkTask] Erreur scan batch: {exc}")
        raise self.retry(exc=exc)


# Export des tâches
__all__ = [
    'bulk_insert_tracks_task',
    'bulk_insert_albums_task',
    'bulk_insert_artists_task',
    'bulk_insert_embeddings_task',
    'bulk_insert_mir_scores_task',
    'update_tracks_metadata_task',
    'cleanup_orphaned_records_task',
    'process_scan_batch_task',
]
