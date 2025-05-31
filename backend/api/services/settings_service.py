import json
import httpx
import asyncio
import socket
from typing import Any, Dict, Optional
from backend.api.schemas.settings_schema import SettingCreate
from backend.services.path_variables import PathVariables
from helpers.logging import logger

# Clés des paramètres système
MUSIC_PATH_TEMPLATE = "music_path_template"
ARTIST_IMAGE_FILES = "artist_image_files"
ALBUM_COVER_FILES = "album_cover_files"

# Valeurs par défaut
DEFAULT_SETTINGS = {
    MUSIC_PATH_TEMPLATE: PathVariables.get_example_path(),
    ARTIST_IMAGE_FILES: json.dumps(["folder.jpg", "fanart.jpg"]),
    ALBUM_COVER_FILES: json.dumps(["cover.jpg", "folder.jpg"])
}

class SettingsService:
    def __init__(self, api_url: str = "http://localhost:8001", max_retries: int = 5):
        self.base_url = api_url.rstrip('/')  # Supprimer le slash final s'il existe
        self.api_settings_url = f"{self.base_url}/api/settings"  # URL unique pour les settings
        self.max_retries = max_retries
        self._cache = {}
        self.initialized = False
        # Configuration client HTTP
        self.client_kwargs = {
            "follow_redirects": True,
            "timeout": httpx.Timeout(10.0, connect=5.0),
            "headers": {"Accept": "application/json"}
        }
        socket.setdefaulttimeout(5)

    async def _check_server_available(self) -> bool:
        """Vérifie si le serveur est disponible."""
        try:
            async with httpx.AsyncClient(**self.client_kwargs) as client:
                response = await client.get(f"{self.base_url}/api/healthcheck")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Vérification serveur échouée: {e}")
            return False

    async def _wait_for_server(self, timeout: int = 30) -> bool:
        """Attend que le serveur soit disponible."""
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if await self._check_server_available():
                return True
            await asyncio.sleep(1)
        return False

    async def _wait_for_healthcheck(self, timeout: int = 30) -> bool:
        """Attend que le healthcheck de l'API réponde correctement."""
        start_time = asyncio.get_event_loop().time()
        async with httpx.AsyncClient(**self.client_kwargs) as client:
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    response = await client.get(f"{self.base_url}/api/healthcheck")
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)
            return False

    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[httpx.Response]:
        """Effectue une requête HTTP."""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(**self.client_kwargs) as client:
                    # S'assurer que l'URL est absolue
                    full_url = url if url.startswith('http') else f"{self.base_url}{url}"
                    response = await getattr(client, method)(full_url, **kwargs)
                    if response.status_code == 307:
                        # Gérer la redirection manuellement si nécessaire
                        redirect_url = response.headers['Location']
                        response = await getattr(client, method)(redirect_url, **kwargs)
                    return response
            except Exception as e:
                logger.error(f"Erreur requête {method} {url}: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def get_setting(self, key: str) -> Any:
        """Récupère un paramètre avec initialisation automatique."""
        if not self.initialized:
            await self.initialize_default_settings()
        return await self._get_setting_internal(key)

    async def _get_setting_internal(self, key: str) -> Any:
        """Logique interne de récupération des paramètres."""
        # Vérifier d'abord le cache
        if key in self._cache:
            return self._cache[key]

        try:
            # Si le serveur n'est pas disponible, utiliser directement la valeur par défaut
            if not await self._check_server_available():
                return self._use_default(key)

            response = await self._make_request("get", f"{self.api_settings_url}/{key}")
            if response and response.status_code == 200:
                data = response.json()
                value = data.get("value") or DEFAULT_SETTINGS.get(key)
                self._cache[key] = value
                return value
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du paramètre {key}: {e}")
            return self._use_default(key)

    def _use_default(self, key: str) -> Any:
        """Utilise et met en cache la valeur par défaut."""
        default_value = DEFAULT_SETTINGS.get(key)
        self._cache[key] = default_value
        logger.warning(f"Utilisation valeur par défaut pour {key}")
        return default_value

    async def initialize_default_settings(self):
        """Initialise les paramètres par défaut uniquement s'ils n'existent pas."""
        if self.initialized:
            return

        logger.info("Vérification des settings existants...")
        
        # Attendre que l'API soit prête via le healthcheck
        if not await self._wait_for_healthcheck():
            logger.warning("API non disponible - utilisation des valeurs par défaut")
            self._cache = DEFAULT_SETTINGS.copy()
            self.initialized = True
            return

        # Vérifier d'abord les paramètres existants
        try:
            response = await self._make_request("get", self.api_settings_url)
            if response and response.status_code == 200:
                existing_settings = {s["key"]: s["value"] for s in response.json()}
                
                # Ne créer que les paramètres manquants
                for key, default_value in DEFAULT_SETTINGS.items():
                    if key not in existing_settings:
                        logger.info(f"Création du paramètre manquant: {key}")
                        setting = SettingCreate(
                            key=key,
                            value=default_value,
                            description=f"System setting: {key}",
                            is_encrypted=False
                        )
                        await self._make_request(
                            "post",
                            self.api_settings_url,
                            json=setting.model_dump()
                        )
                    else:
                        # Utiliser la valeur existante
                        self._cache[key] = existing_settings[key]
                        logger.debug(f"Paramètre existant conservé: {key}")

        except Exception as e:
            logger.error(f"Erreur lors de la vérification des settings: {e}")
            self._cache = DEFAULT_SETTINGS.copy()

        self.initialized = True
        logger.info("Initialisation des settings terminée")

    async def create_setting(self, setting: SettingCreate) -> bool:
        """Crée un nouveau paramètre en utilisant le schéma Pydantic."""
        try:
            logger.info(f"Tentative de création du paramètre: {setting.key}")
            response = await self._make_request(
                "post", 
                self.api_settings_url,
                json=setting.model_dump()
            )
            success = response.status_code in (200, 201)
            if success:
                logger.info(f"Paramètre {setting.key} créé avec succès")
            else:
                logger.error(f"Échec de la création du paramètre {setting.key}: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"Erreur lors de la création du paramètre {setting.key}: {e}")
            return False

    async def get_path_variables(self) -> Dict[str, str]:
        """Retourne les variables disponibles pour les chemins."""
        return PathVariables.get_available_variables()

    async def validate_path_template(self, template: str) -> bool:
        """Valide un template de chemin."""
        return PathVariables.validate_path_template(template)
