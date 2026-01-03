"""
Tâches legacy pour compatibilité avec l'ancienne architecture.

Ces tâches seront progressivement supprimées lors de la migration.
"""

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery

# === ALIAS POUR LES ANCIENNES TÂCHES ===

@celery.task(name="scan_music_task", queue="scan")
def scan_music_task_legacy(directory: str, progress_callback=None):
    """
    Alias legacy pour la tâche scan.discovery.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'scan.discovery' à la place.
    """
    logger.error("[LEGACY] scan_music_task est maintenant supprimée. Utilisez 'scan.discovery' directement.")
    logger.error("[LEGACY] Exemple: celery.send_task('scan.discovery', args=[directory, progress_callback])")
    raise NotImplementedError("scan_music_task est supprimée. Utilisez scan.discovery directement.")


@celery.task(name="extract_metadata_batch", queue="extract")
def extract_metadata_batch_legacy(file_paths: list, batch_id: str = None):
    """
    Alias legacy pour la tâche metadata.extract_batch.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'metadata.extract_batch' à la place.
    """
    logger.warning("[LEGACY] extract_metadata_batch est dépréciée. Utilisez metadata.extract_batch à la place.")
    return celery.send_task('metadata.extract_batch', args=[file_paths, batch_id])


@celery.task(name="batch_entities", queue="batch")
def batch_entities_legacy(metadata_list: list, batch_id: str = None):
    """
    Alias legacy pour la tâche batch.process_entities.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'batch.process_entities' à la place.
    """
    logger.warning("[LEGACY] batch_entities est dépréciée. Utilisez batch.process_entities à la place.")
    return celery.send_task('batch.process_entities', args=[metadata_list, batch_id])


@celery.task(name="insert_batch_direct", queue="insert")
def insert_batch_direct_legacy(insertion_data: dict):
    """
    Alias legacy pour la tâche insert.direct_batch.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'insert.direct_batch' à la place.
    """
    logger.warning("[LEGACY] insert_batch_direct est dépréciée. Utilisez insert.direct_batch à la place.")
    return celery.send_task('insert.direct_batch', args=[insertion_data])


@celery.task(name="extract_embedded_covers_batch", queue="deferred")
def extract_embedded_covers_batch_legacy(file_paths: list):
    """
    Alias legacy pour la tâche covers.extract_embedded.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'covers.extract_embedded' à la place.
    """
    logger.warning("[LEGACY] extract_embedded_covers_batch est dépréciée. Utilisez covers.extract_embedded à la place.")
    return celery.send_task('covers.extract_embedded', args=[file_paths])


@celery.task(name="extract_artist_images_batch", queue="deferred")
def extract_artist_images_batch_legacy(file_paths: list):
    """
    Alias legacy pour la tâche covers.extract_artist_images.
    
    Cette tâche sera supprimée dans une version future.
    Utilisez 'covers.extract_artist_images' à la place.
    """
    logger.warning("[LEGACY] extract_artist_images_batch est dépréciée. Utilisez covers.extract_artist_images à la place.")
    return celery.send_task('covers.extract_artist_images', args=[file_paths])


# === TÂCHES UTILITAIRES ===

def show_migration_warnings():
    """
    Affiche les avertissements de migration pour les tâches dépréciées.
    """
    logger.info("[MIGRATION] Les tâches suivantes sont dépréciées et seront supprimées :")
    logger.info("  - scan_music_task → scan.discovery")
    logger.info("  - extract_metadata_batch → metadata.extract_batch") 
    logger.info("  - batch_entities → batch.process_entities")
    logger.info("  - insert_batch_direct → insert.direct_batch")
    logger.info("  - extract_embedded_covers_batch → covers.extract_embedded")
    logger.info("  - extract_artist_images_batch → covers.extract_artist_images")
    logger.info("[MIGRATION] Consultez BACKEND_WORKER_REFACTOR_PLAN.md pour plus de détails.")