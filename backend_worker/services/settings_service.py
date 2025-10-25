import asyncio
import httpx
import os
from typing import Any
# Définition locale des clés de settings
ALBUM_COVER_FILES = "album_cover_files"
ARTIST_IMAGE_FILES = "artist_image_files"
MUSIC_PATH_TEMPLATE = "music_path_template"
_settings_cache = {}
class SettingsService:
    def __init__(self, api_url: str = os.getenv('API_URL', 'http://library:8001')):
        self.api_url = f"{api_url}/api/settings"

    async def get_setting(self, key: str) -> Any:
        """Récupère une valeur de paramètre depuis l'API avec gestion d'erreur robuste."""
        import logging
        logger = logging.getLogger(__name__)

        logger.debug(f"[SettingsService] Récupération du paramètre '{key}' depuis {self.api_url}/{key}")

        if key in _settings_cache:
            cached_value = _settings_cache[key]
            logger.debug(f"[SettingsService] Paramètre '{key}' trouvé en cache: {cached_value} (type: {type(cached_value)})")
            # DIAGNOSTIC: Vérifier si la valeur cachée est un dictionnaire problématique
            if isinstance(cached_value, dict):
                logger.error(f"[SettingsService] ERREUR: Paramètre '{key}' en cache est un dictionnaire: {cached_value}")
            return cached_value

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                logger.debug(f"[SettingsService] Tentative {attempt + 1}/{max_retries} pour '{key}'...")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(f"{self.api_url}/{key}")
                    logger.debug(f"[SettingsService] Réponse reçue - Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        value = data.get("value")
                        # DIAGNOSTIC: Analyser la valeur reçue
                        logger.debug(f"[SettingsService] Données brutes reçues pour '{key}': {data} (type: {type(data)})")
                        logger.debug(f"[SettingsService] Valeur extraite pour '{key}': {value} (type: {type(value)})")

                        # CORRECTION: Vérifier si la valeur est un dictionnaire problématique
                        if isinstance(value, dict):
                            logger.error(f"[SettingsService] ERREUR: Valeur reçue pour '{key}' est un dictionnaire: {value}")
                            logger.error(f"[SettingsService] Clés du dictionnaire: {list(value.keys())}")
                            # CORRECTION: Essayer d'extraire une valeur par défaut depuis le dictionnaire
                            if 'value' in value:
                                logger.warning(f"[SettingsService] Correction: Utilisation de value par défaut depuis le dictionnaire")
                                value = value['value']
                            elif len(value) == 1:
                                logger.warning(f"[SettingsService] Correction: Utilisation de la première valeur du dictionnaire")
                                value = list(value.values())[0]
                            else:
                                logger.error(f"[SettingsService] Impossible de corriger automatiquement le dictionnaire")
                                value = None

                        _settings_cache[key] = value
                        logger.debug(f"[SettingsService] Paramètre '{key}' récupéré avec succès: {value}")
                        return value
                    elif response.status_code == 404:
                        logger.warning(f"[SettingsService] Paramètre '{key}' non trouvé (404)")
                        return None
                    else:
                        logger.warning(f"[SettingsService] Échec de récupération du paramètre '{key}' - Status: {response.status_code}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5
                            continue
                        return None

            except httpx.ConnectError as e:
                logger.warning(f"[SettingsService] Erreur de connexion pour '{key}' (tentative {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                logger.error(f"[SettingsService] Échec définitif de connexion pour '{key}' après {max_retries} tentatives")
                raise

            except httpx.TimeoutException as e:
                logger.warning(f"[SettingsService] Timeout pour '{key}' (tentative {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                logger.error(f"[SettingsService] Timeout définitif pour '{key}' après {max_retries} tentatives")
                raise

            except Exception as e:
                logger.error(f"[SettingsService] Erreur inattendue pour '{key}': {e}")
                raise

        return None

    async def update_setting(self, key: str, value: str) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.put(f"{self.api_url}/{key}", params={"value": value})
            return response.status_code == 200

    async def get_path_variables(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/path_variables")
            if response.status_code == 200:
                return response.json()
            return {}