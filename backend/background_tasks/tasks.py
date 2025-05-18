from backend.task_system import AsyncTask
from backend.indexing.indexer import MusicIndexer
from helpers.logging import logger

# Création de l'instance AsyncTask avant le décorateur
index_music = AsyncTask(name="index_music", description="Indexation des fichiers musicaux")

@index_music
async def index_music_task(update_progress, directory: str):
    """Tâche d'indexation avec monitoring de la progression."""
    try:
        logger.info(f"Démarrage de l'indexation de: {directory}")
        indexer = MusicIndexer()
        update_progress(0, "Démarrage de l'indexation...")
        await indexer.index_directory(directory, 
            lambda progress, msg: update_progress(progress, msg))
        update_progress(100, "Indexation terminée")
    except Exception as e:
        logger.error(f"Erreur d'indexation: {str(e)}", exc_info=True)
        raise