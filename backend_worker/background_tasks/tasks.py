"""
Nouveau fichier tasks.py pour assurer la compatibilité avec l'ancienne architecture.
Ce fichier délègue aux nouveaux modules de la refactorisation.
"""

# Importations depuis les nouveaux modules
from backend_worker.celery_app import celery
from backend_worker.tasks.main_tasks import (
    scan_music_task_legacy,
    extract_metadata_batch_legacy,
    batch_entities_legacy,
    insert_batch_direct_legacy,
    extract_embedded_covers_batch_legacy,
    extract_artist_images_batch_legacy,
    show_migration_warnings
)

# Alias pour maintenir la compatibilité avec l'ancienne API
scan_music_task = scan_music_task_legacy
extract_metadata_batch = extract_metadata_batch_legacy
batch_entities = batch_entities_legacy
insert_batch_direct = insert_batch_direct_legacy
extract_embedded_covers_batch = extract_embedded_covers_batch_legacy
extract_artist_images_batch = extract_artist_images_batch_legacy

# Fonction utilitaire pour afficher les avertissements de migration
# REMOVED: Fonction redéfinie, utiliser celle importée depuis main_tasks

# Exportations pour faciliter l'importation
__all__ = [
    'celery',
    'scan_music_task',
    'extract_metadata_batch',
    'batch_entities',
    'insert_batch_direct',
    'extract_embedded_covers_batch',
    'extract_artist_images_batch',
    'show_migration_warnings'
]