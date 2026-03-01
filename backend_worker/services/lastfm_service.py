# -*- coding: UTF-8 -*-
"""
Last.fm Service Refactorisé

Service pour récupérer les informations Last.fm en utilisant la bibliothèque pylast.
Ce service remplace l'ancienne implémentation basée sur des appels HTTP directs.
"""

import pylast
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from backend_worker.utils.logging import logger
from backend_worker.services.settings_service import SettingsService
from backend_worker.services.cache_service import cache_service

settings_service = SettingsService()

class LastFMService:
    """Service pour l'intégration avec l'API Last.fm utilisant pylast."""

    def __init__(self):
        self._network = None
        self._cache_service = cache_service

    @property
    def network(self) -> pylast.LastFMNetwork:
        """Initialisation paresseuse de la connexion réseau Last.fm avec approche synchrone."""
        if self._network is None:
            logger.info("[LASTFM] Initializing network via lazy loading with synchronous approach...")
            try:
                # Récupérer les credentials de manière synchrone depuis l'API
                import httpx
                import os

                # Méthode synchrone pour obtenir les settings depuis l'API
                def get_setting_sync(key: str) -> str:
                    """Obtient un setting de manière synchrone depuis l'API."""
                    try:
                        # Utiliser httpx de manière synchrone pour éviter les conflits de boucle d'événements
                        api_url = os.getenv('API_URL', 'http://api:8001')
                        with httpx.Client(timeout=15.0) as client:
                            response = client.get(f"{api_url}/api/settings/{key}")
                            if response.status_code == 200:
                                data = response.json()
                                return data.get('value', '')
                            else:
                                logger.warning(f"[LASTFM] Could not get setting {key} from API: {response.status_code}")
                                return ""

                    except Exception as e:
                        logger.warning(f"[LASTFM] Could not get setting {key} synchronously: {e}")
                        return ""

                api_key = get_setting_sync("lastfm_api_key")
                api_secret = get_setting_sync("lastfm_shared_secret")

                if not api_key or not api_secret:
                    raise ValueError("Last.fm API key and secret not configured in settings")

                logger.info("[LASTFM] Initializing Last.fm network with pylast (anonymous mode)")

                # Créer une session anonyme (lecture seule uniquement)
                # Pas besoin de username/password pour les opérations en lecture seule
                self._network = pylast.LastFMNetwork(
                    api_key=api_key,
                    api_secret=api_secret
                )

                logger.info("[LASTFM] Last.fm network initialized with pylast")
                logger.info(f"[LASTFM] Network object type: {type(self._network)}")

                # Vérifier si l'objet réseau est une coroutine
                import inspect
                if inspect.iscoroutine(self._network):
                    logger.error("[LASTFM] CRITICAL: Last.fm network is a coroutine, not initialized!")
                    raise RuntimeError("Last.fm network initialization returned a coroutine")

            except Exception as e:
                logger.error(f"[LASTFM] Failed to initialize Last.fm network: {e}")
                import traceback
                logger.error(f"[LASTFM] Full traceback: {traceback.format_exc()}")
                raise

        return self._network

    async def _initialize_network(self):
        """Initialise le réseau pylast avec gestion des erreurs."""
        try:
            # Récupérer les credentials depuis le service de settings
            api_key = await settings_service.get_setting("lastfm_api_key")
            api_secret = await settings_service.get_setting("lastfm_shared_secret")

            if not api_key or not api_secret:
                raise ValueError("Last.fm API key and secret not configured in settings")

            logger.info("[LASTFM] Initializing Last.fm network with pylast (anonymous mode)")

            # Créer une session anonyme (lecture seule uniquement)
            # Pas besoin de username/password pour les opérations en lecture seule
            self._network = pylast.LastFMNetwork(
                api_key=api_key,
                api_secret=api_secret
            )

            logger.info("[LASTFM] Last.fm network initialized with pylast")
            logger.info(f"[LASTFM] Network object type: {type(self._network)}")

            # Vérifier si l'objet réseau est une coroutine
            import inspect
            if inspect.iscoroutine(self._network):
                logger.error("[LASTFM] CRITICAL: Last.fm network is a coroutine, not initialized!")
                raise RuntimeError("Last.fm network initialization returned a coroutine")

        except Exception as e:
            logger.error(f"[LASTFM] Failed to initialize Last.fm network: {e}")
            import traceback
            logger.error(f"[LASTFM] Full traceback: {traceback.format_exc()}")
            raise

    # ======================
    # Fonctions principales par entité
    # ======================

    async def get_artist_info(self, artist_name: str, mb_artist_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations complètes d'un artiste depuis Last.fm.

        Args:
            artist_name: Nom de l'artiste à rechercher
            mb_artist_id: MusicBrainz Artist ID pour une correspondance précise (optionnel)

        Returns:
            Dictionnaire contenant les informations de l'artiste ou None en cas d'erreur
        """
        cache_key = f"lastfm:artist:{artist_name.lower()}:{mb_artist_id or 'nom'}"
        return await self._cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            cache_key,
            self._fetch_artist_info,
            artist_name, mb_artist_id
        )

    async def _fetch_artist_info(self, artist_name: str, mb_artist_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fonction interne pour récupérer les infos artistes depuis pylast."""
        try:
            # Rechercher l'artiste sur Last.fm en utilisant MBID si disponible
            if mb_artist_id:
                logger.debug(f"[LASTFM] Utilisation de MBID {mb_artist_id} pour l'artiste {artist_name}")
                logger.debug(f"[LASTFM] Network type before get_artist_by_mbid: {type(self.network)}")
                logger.debug(f"[LASTFM] Network object: {self.network}")

                # Vérifier si la méthode est une coroutine
                import inspect
                if hasattr(self.network, 'get_artist_by_mbid'):
                    method = getattr(self.network, 'get_artist_by_mbid')
                    logger.debug(f"[LASTFM] get_artist_by_mbid method type: {type(method)}")
                    logger.debug(f"[LASTFM] get_artist_by_mbid is coroutine: {inspect.iscoroutinefunction(method)}")

                lastfm_artist = self.network.get_artist_by_mbid(mb_artist_id)
                logger.debug(f"[LASTFM] Artist object type: {type(lastfm_artist)}")
                logger.debug(f"[LASTFM] Artist object: {lastfm_artist}")
            else:
                logger.debug(f"[LASTFM] Recherche par nom pour l'artiste {artist_name}")
                lastfm_artist = self.network.get_artist(artist_name)

            # Extraire les informations de base
            artist_info = {
                "url": str(lastfm_artist.get_url()),
                "listeners": int(lastfm_artist.get_listener_count()),
                "playcount": int(lastfm_artist.get_playcount()),
                "tags": self._extract_tags(lastfm_artist),
                "bio": self._get_artist_bio(lastfm_artist),
                "images": self._get_artist_images(lastfm_artist),
                "fetched_at": datetime.utcnow().isoformat(),
                "musicbrainz_id": str(mb_artist_id or lastfm_artist.get_mbid())  # Conserver le MBID utilisé
            }

            logger.info(f"[LASTFM] Successfully fetched info for artist: {artist_name} (MBID: {mb_artist_id or 'N/A'})")
            return artist_info

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch artist info for {artist_name} (MBID: {mb_artist_id or 'N/A'}): {e}")
            return None

    async def get_similar_artists(self, artist_name: str, limit: int = 5, mb_artist_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Récupère les artistes similaires depuis Last.fm.

        Args:
            artist_name: Nom de l'artiste
            limit: Nombre maximum d'artistes similaires à retourner
            mb_artist_id: MusicBrainz Artist ID pour une correspondance précise (optionnel)

        Returns:
            Liste d'artistes similaires ou None en cas d'erreur
        """
        cache_key = f"lastfm:similar:{artist_name.lower()}:{limit}:{mb_artist_id or 'nom'}"
        return await self._cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            cache_key,
            self._fetch_similar_artists,
            artist_name, limit, mb_artist_id
        )

    async def _fetch_similar_artists(self, artist_name: str, limit: int, mb_artist_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Fonction interne pour récupérer les artistes similaires."""
        try:
            # Get the artist from Last.fm
            if mb_artist_id:
                logger.debug(f"[LASTFM] Utilisation de MBID {mb_artist_id} pour l'artiste {artist_name}")
                lastfm_artist = self.network.get_artist_by_mbid(mb_artist_id)
            else:
                logger.debug(f"[LASTFM] Recherche par nom pour l'artiste {artist_name}")
                lastfm_artist = self.network.get_artist(artist_name)

            similar_artists = lastfm_artist.get_similar(limit=limit)

            result = []
            for similar in similar_artists:
                similar_name = similar.item.get_name()
                result.append({
                    "name": similar_name,
                    "url": similar.item.get_url(),
                    "weight": float(similar.weight),
                    "match": similar.item.get_match() if hasattr(similar, 'match') else None
                })

            logger.info(f"[LASTFM] Successfully fetched {len(result)} similar artists for: {artist_name}")

            # Store the similar artists in the database
            await self._store_similar_artists(artist_name, result, mb_artist_id)

            return result

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch similar artists for {artist_name}: {e}")
            return None

    async def _store_similar_artists(self, artist_name: str, similar_artists: List[Dict[str, Any]], mb_artist_id: Optional[str] = None) -> bool:
        """Store similar artists in the database via API with correct format."""
        import httpx
        import os
        
        try:
            # Get the API URL
            api_url = os.getenv('API_URL', 'http://api:8001')
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, get the artist ID from the database using the artist name or mb_artist_id
                artist_id = None
                if mb_artist_id:
                    logger.debug(f"[LASTFM] Utilisation de MBID {mb_artist_id} pour trouver l'artiste {artist_name}")
                    response = await client.get(f"{api_url}/api/artists/search", params={"musicbrainz_artistid": mb_artist_id})
                    if response.status_code == 200:
                        artists = response.json()
                        if artists:
                            artist_id = artists[0]['id']
                            logger.debug(f"[LASTFM] Found artist by MBID: {artist_id}")
                    else:
                        logger.warning(f"[LASTFM] Could not find artist by MBID {mb_artist_id}: {response.status_code}")
                
                # If mb_artist_id approach failed or wasn't provided, fall back to name search
                if not artist_id:
                    logger.debug(f"[LASTFM] Recherche par nom pour l'artiste {artist_name}")
                    response = await client.get(f"{api_url}/api/artists/search", params={"name": artist_name})
                    if response.status_code == 200:
                        artists = response.json()
                        if artists:
                            artist_id = artists[0]['id']
                            logger.debug(f"[LASTFM] Found artist by name: {artist_id}")
                        else:
                            logger.warning(f"[LASTFM] No artist found with name {artist_name}")
                            return False
                    else:
                        logger.warning(f"[LASTFM] Could not find artist {artist_name} in database: {response.status_code}")
                        return False
                
                # Prepare the data in the format expected by the API endpoint
                # The endpoint expects: [{"name": "Artist Name", "weight": 0.8}]
                similar_data = []
                for similar in similar_artists:
                    similar_name = similar.get('name')
                    weight = similar.get('weight')
                    if similar_name and weight is not None:
                        similar_data.append({
                            "name": similar_name,
                            "weight": float(weight)
                        })
                
                if not similar_data:
                    logger.warning(f"[LASTFM] No valid similar artists data to store for {artist_name}")
                    return False
                
                logger.info(f"[LASTFM] Storing {len(similar_data)} similar artists for {artist_name} (artist_id: {artist_id})")
                logger.debug(f"[LASTFM] Similar artists data: {similar_data[:3]}...")  # Log first 3 for debugging
                
                # Store the similar artists in the database using the correct endpoint
                store_response = await client.post(
                    f"{api_url}/api/artists/{artist_id}/similar",
                    json=similar_data
                )
                
                if store_response.status_code == 200:
                    result = store_response.json()
                    logger.info(f"[LASTFM] Successfully stored similar artists for {artist_name}: {result.get('message', 'Success')}")
                    return True
                else:
                    logger.error(f"[LASTFM] Failed to store similar artists for {artist_name}: {store_response.status_code} - {store_response.text}")
                    # Log the request data for debugging
                    logger.error(f"[LASTFM] Request data that failed: {similar_data}")
                    return False
                
        except Exception as e:
            logger.error(f"[LASTFM] Error storing similar artists for {artist_name}: {e}")
            import traceback
            logger.error(f"[LASTFM] Full traceback: {traceback.format_exc()}")
            return False

    async def get_album_info(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un album depuis Last.fm.

        Args:
            artist_name: Nom de l'artiste
            album_name: Nom de l'album

        Returns:
            Dictionnaire contenant les informations de l'album ou None en cas d'erreur
        """
        cache_key = f"lastfm:album:{artist_name.lower()}:{album_name.lower()}"
        return await self._cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            cache_key,
            self._fetch_album_info,
            artist_name, album_name
        )

    async def _fetch_album_info(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """Fonction interne pour récupérer les infos album."""
        try:
            lastfm_artist = self.network.get_artist(artist_name)
            lastfm_album = lastfm_artist.get_album(album_name)

            album_info = {
                "title": lastfm_album.get_title(),
                "artist": lastfm_album.get_artist().get_name(),
                "url": lastfm_album.get_url(),
                "listeners": lastfm_album.get_listener_count(),
                "playcount": lastfm_album.get_playcount(),
                "tracks": self._get_album_tracks(lastfm_album),
                "tags": self._extract_tags(lastfm_album),
                "images": self._get_album_images(lastfm_album),
                "release_date": lastfm_album.get_release_date(),
                "fetched_at": datetime.utcnow().isoformat()
            }

            logger.info(f"[LASTFM] Successfully fetched info for album: {album_name} by {artist_name}")
            return album_info

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch album info for {album_name} by {artist_name}: {e}")
            return None

    async def get_track_info(self, artist_name: str, track_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une piste depuis Last.fm.

        Args:
            artist_name: Nom de l'artiste
            track_name: Nom de la piste

        Returns:
            Dictionnaire contenant les informations de la piste ou None en cas d'erreur
        """
        cache_key = f"lastfm:track:{artist_name.lower()}:{track_name.lower()}"
        return await self._cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            cache_key,
            self._fetch_track_info,
            artist_name, track_name
        )

    async def _fetch_track_info(self, artist_name: str, track_name: str) -> Optional[Dict[str, Any]]:
        """Fonction interne pour récupérer les infos piste."""
        try:
            lastfm_artist = self.network.get_artist(artist_name)
            lastfm_track = lastfm_artist.get_track(track_name)

            track_info = {
                "title": lastfm_track.get_title(),
                "artist": lastfm_track.get_artist().get_name(),
                "url": lastfm_track.get_url(),
                "listeners": lastfm_track.get_listener_count(),
                "playcount": lastfm_track.get_playcount(),
                "duration": lastfm_track.get_duration(),
                "tags": self._extract_tags(lastfm_track),
                "images": self._get_track_images(lastfm_track),
                "fetched_at": datetime.utcnow().isoformat()
            }

            logger.info(f"[LASTFM] Successfully fetched info for track: {track_name} by {artist_name}")
            return track_info

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch track info for {track_name} by {artist_name}: {e}")
            return None

    async def get_artist_image(self, artist_name: str) -> Optional[Tuple[str, str]]:
        """
        Récupère l'image d'un artiste depuis Last.fm (remplace l'ancienne fonction).

        Args:
            artist_name: Nom de l'artiste

        Returns:
            Tuple (données_base64, type_mime) ou None en cas d'erreur
        """
        cache_key = f"lastfm:artist_image:{artist_name.lower()}"
        return await self._cache_service.call_with_cache_and_circuit_breaker(
            "lastfm",
            cache_key,
            self._fetch_artist_image,
            artist_name
        )

    async def _fetch_artist_image(self, artist_name: str) -> Optional[Tuple[str, str]]:
        """Fonction interne pour récupérer l'image de l'artiste."""
        try:
            lastfm_artist = self.network.get_artist(artist_name)

            # Chercher une image de taille intermédiaire d'abord
            preferred_sizes = ["extralarge", "large", "mega", "medium", "small"]
            for size in preferred_sizes:
                try:
                    image_url = lastfm_artist.get_image(size)
                    if image_url:
                        logger.info(f"[LASTFM] Found {size} image for artist: {artist_name}")

                        # Télécharger et convertir l'image en base64
                        import httpx
                        import base64
                        async with httpx.AsyncClient(timeout=10) as client:
                            img_response = await client.get(image_url, timeout=10)
                            if img_response.status_code == 200:
                                image_data = base64.b64encode(img_response.content).decode('utf-8')
                                mime_type = img_response.headers.get('content-type', 'image/jpeg')
                                return (f"data:{mime_type};base64,{image_data}", mime_type)
                except Exception:
                    continue

            logger.warning(f"[LASTFM] No suitable image found for artist: {artist_name}")
            return None

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch artist image for {artist_name}: {e}")
            return None

    # ======================
    # Fonctions utilitaires
    # ======================

    def _extract_tags(self, lastfm_entity) -> List[str]:
        """Extrait les tags d'une entité Last.fm."""
        try:
            tags = lastfm_entity.get_top_tags(limit=10)
            return [tag.item.get_name() for tag in tags if hasattr(tag, 'item')]
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to extract tags: {e}")
            return []

    def _get_artist_bio(self, artist: pylast.Artist) -> Optional[str]:
        """Récupère la biographie d'un artiste."""
        try:
            bio = artist.get_bio_content()
            return bio if bio else None
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to get artist bio: {e}")
            return None

    def _get_artist_images(self, artist: pylast.Artist) -> List[Dict[str, Any]]:
        """Récupère les images d'un artiste."""
        try:
            # pylast.Artist may not have get_images(), try get_image() for different sizes
            images = []
            sizes = ["small", "medium", "large", "extralarge", "mega"]
            for size in sizes:
                try:
                    image_url = artist.get_image(size)
                    if image_url:
                        images.append({
                            "size": size,
                            "url": image_url
                        })
                except Exception:
                    continue
            return images
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to get artist images: {e}")
            return []

    def _get_album_tracks(self, album: pylast.Album) -> List[Dict[str, Any]]:
        """Récupère les pistes d'un album."""
        try:
            tracks = album.get_tracks()
            return [{
                "title": track.get_title(),
                "duration": track.get_duration(),
                "url": track.get_url()
            } for track in tracks]
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to get album tracks: {e}")
            return []

    def _get_album_images(self, album: pylast.Album) -> List[Dict[str, Any]]:
        """Récupère les images d'un album."""
        try:
            images = album.get_images()
            return [{
                "size": img.get("size"),
                "url": img.get("#text")
            } for img in images if img.get("size") and img.get("#text")]
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to get album images: {e}")
            return []

    def _get_track_images(self, track: pylast.Track) -> List[Dict[str, Any]]:
        """Récupère les images d'une piste."""
        try:
            images = track.get_images()
            return [{
                "size": img.get("size"),
                "url": img.get("#text")
            } for img in images if img.get("size") and img.get("#text")]
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to get track images: {e}")
            return []

# Instance globale du service
lastfm_service = LastFMService()

# Fonction autonome pour compatibilité avec les imports existants
async def get_lastfm_artist_image(client, artist_name: str) -> Optional[Tuple[str, str]]:
    """
    Fonction autonome pour récupérer l'image d'un artiste depuis Last.fm.
    Utilise l'instance globale du service LastFMService.

    Args:
        client: Client HTTP asynchrone (httpx.AsyncClient)
        artist_name: Nom de l'artiste

    Returns:
        Tuple (données_base64, type_mime) ou None en cas d'erreur
    """
    return await lastfm_service.get_artist_image(artist_name)
