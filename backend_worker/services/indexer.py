<<<<<<< HEAD
# music/indexer.py
import os
import shutil
from typing import Callable, Optional, Dict
from backend_worker.services.music_scan import scan_music_files
from backend_worker.utils.logging import logger
import httpx
import json

API_URL= os.getenv("API_URL", "http://localhost:8000")

async def remote_get_or_create_index(index_dir: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/api/search/index", json=index_dir)
        response.raise_for_status()
        data = response.json()
        return data["index_dir"], data["index_name"]

async def remote_add_to_index(index_dir: str, index_name: str, whoosh_data: dict):
    async with httpx.AsyncClient() as client:
        logger.info(f"Ajout de données à l'index Whoosh: {whoosh_data}")
        logger.info(json.dumps({"index_dir": index_dir, "index_name": index_name, "whoosh_data": whoosh_data}))
        response = await client.post(f"{API_URL}/api/search/add",
                                    json={"index_dir": index_dir, "index_name": index_name, "whoosh_data": whoosh_data})
        response.raise_for_status()
        return response.json()

class MusicIndexer:
    def __init__(self, index_dir="./backend/data/whoosh_index"):
        self.index_dir = index_dir
        self.index_dir_actual = None
        self.index_name = None
        self.index = None
    async def async_init(self):
        """Initialise l'index Whoosh de manière asynchrone."""
        self.index_dir_actual, self.index_name = await remote_get_or_create_index(self.index_dir)
    def prepare_whoosh_data(self, track_data: Dict) -> Dict:
        """Prépare les données pour l'indexation Whoosh uniquement."""
        whoosh_data = {
            "id": track_data.get("id"),
            "title": track_data.get("title"),
            "path": track_data.get("path"),
            "artist": track_data.get("artist"),
            "album": track_data.get("album"),
            "genre": track_data.get("genre"),
            "year": track_data.get("year"),
            "duration": track_data.get("duration", 0),
            "track_number": track_data.get("track_number"),
            "disc_number": track_data.get("disc_number"),
            "musicbrainz_id": track_data.get("musicbrainz_id"),
            "musicbrainz_albumid": track_data.get("musicbrainz_albumid"),
            "musicbrainz_artistid": track_data.get("musicbrainz_artistid")
        }
        return {k: v for k, v in whoosh_data.items() if v is not None}

    async def index_directory(self, directory: str, scan_config: dict, progress_callback=None):
        """Indexe uniquement dans Whoosh."""
        try:
            logger.info(f"Démarrage indexation Whoosh: {directory}")
            # Scan des fichiers
            files = []
            async for file_data in scan_music_files(directory, scan_config):
                files.append(file_data)
            total_files = len(files)

            # Traiter chaque fichier uniquement pour Whoosh
            for index, file_data in enumerate(files):
                try:
                    # Préparer et ajouter à l'index Whoosh
                    whoosh_data = self.prepare_whoosh_data(file_data)
                    await remote_add_to_index(self.index_dir_actual, self.index_name, whoosh_data)
                    logger.debug(f"Fichier indexé dans Whoosh: {file_data.get('title')}")

                    # Mise à jour du progrès
                    if progress_callback:
                        progress = (index + 1) / total_files * 100
                        progress_callback(progress)

                except Exception as e:
                    logger.error(f"Erreur indexation Whoosh: {str(e)}")
                    continue

            logger.info("Indexation Whoosh terminée")

        except Exception as e:
            logger.error(f"Erreur indexation globale: {str(e)}")
            raise

    async def reindex_all(self, directory: str, progress_callback: Optional[Callable[[float], None]] = None):
        """
        Force la réindexation complète.

        Args:
            directory: Chemin du répertoire à réindexer
            progress_callback: Fonction callback(progress: float) pour suivre la progression
        """
        logger.info("Début de la réindexation complète...")

        # Security: Validate index_dir path before using it
        normalized = os.path.normpath(self.index_dir)
        if os.path.isabs(normalized) or '..' in normalized:
            logger.error(f"Invalid index directory path: {self.index_dir}")
            raise ValueError(f"Invalid index directory: {self.index_dir}")

        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        self.index_dir_actual, self.index_name = await remote_get_or_create_index(self.index_dir)
        await self.index_directory(directory, {}, progress_callback)
=======
# music/indexer.py
import os
import shutil
from typing import Callable, Optional, Dict
from backend_worker.services.music_scan import scan_music_files
from backend_worker.utils.logging import logger
import httpx
import json

API_URL= os.getenv("API_URL", "http://localhost:8000")

async def remote_get_or_create_index(index_dir: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/api/search/index", json=index_dir)
        response.raise_for_status()
        data = response.json()
        return data["index_dir"], data["index_name"]

async def remote_add_to_index(index_dir: str, index_name: str, whoosh_data: dict):
    async with httpx.AsyncClient() as client:
        logger.info(f"Ajout de données à l'index Whoosh: {whoosh_data}")
        logger.info(json.dumps({"index_dir": index_dir, "index_name": index_name, "whoosh_data": whoosh_data}))
        response = await client.post(f"{API_URL}/api/search/add",
                                    json={"index_dir": index_dir, "index_name": index_name, "whoosh_data": whoosh_data})
        response.raise_for_status()
        return response.json()

class MusicIndexer:
    def __init__(self, index_dir="./backend/data/whoosh_index"):
        self.index_dir = index_dir
        self.index_dir_actual = None
        self.index_name = None
        self.index = None
    async def async_init(self):
        """Initialise l'index Whoosh de manière asynchrone."""
        self.index_dir_actual, self.index_name = await remote_get_or_create_index(self.index_dir)
    def prepare_whoosh_data(self, track_data: Dict) -> Dict:
        """Prépare les données pour l'indexation Whoosh uniquement."""
        # Inline and avoid extra dictionary to minimize memory ops and function calls
        result = {}
        # Only required keys for whoosh
        for key in (
            "id", "title", "path", "artist", "album", "genre", "year",
            "track_number", "disc_number", "musicbrainz_id",
            "musicbrainz_albumid", "musicbrainz_artistid"
        ):
            v = track_data.get(key)
            if v is not None:
                result[key] = v
        # Special case for duration with default
        v = track_data.get("duration", 0)
        if v is not None:
            result["duration"] = v
        return result

    async def index_directory(self, directory: str, scan_config: dict, progress_callback=None):
        """Indexe uniquement dans Whoosh."""
        try:
            logger.info(f"Démarrage indexation Whoosh: {directory}")
            # Scan des fichiers
            files = []
            async for file_data in scan_music_files(directory, scan_config):
                files.append(file_data)
            total_files = len(files)

            # Traiter chaque fichier uniquement pour Whoosh
            for index, file_data in enumerate(files):
                try:
                    # Préparer et ajouter à l'index Whoosh
                    whoosh_data = self.prepare_whoosh_data(file_data)
                    await remote_add_to_index(self.index_dir_actual, self.index_name, whoosh_data)
                    logger.debug(f"Fichier indexé dans Whoosh: {file_data.get('title')}")

                    # Mise à jour du progrès
                    if progress_callback:
                        progress = (index + 1) / total_files * 100
                        progress_callback(progress)

                except Exception as e:
                    logger.error(f"Erreur indexation Whoosh: {str(e)}")
                    continue

            logger.info("Indexation Whoosh terminée")

        except Exception as e:
            logger.error(f"Erreur indexation globale: {str(e)}")
            raise

    async def reindex_all(self, directory: str, progress_callback: Optional[Callable[[float], None]] = None):
        """
        Force la réindexation complète.

        Args:
            directory: Chemin du répertoire à réindexer
            progress_callback: Fonction callback(progress: float) pour suivre la progression
        """
        logger.info("Début de la réindexation complète...")

        # Security: Validate index_dir path before using it
        normalized = os.path.normpath(self.index_dir)
        if os.path.isabs(normalized) or '..' in normalized:
            logger.error(f"Invalid index directory path: {self.index_dir}")
            raise ValueError(f"Invalid index directory: {self.index_dir}")

        if os.path.exists(self.index_dir):
            shutil.rmtree(self.index_dir)
        self.index_dir_actual, self.index_name = await remote_get_or_create_index(self.index_dir)
        await self.index_directory(directory, {}, progress_callback)
>>>>>>> ba063c12b818c04239982e364c74d04115e059b0
