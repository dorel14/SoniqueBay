# -*- coding: utf-8 -*-
"""
Service d'embeddings local basé sur sentence-transformers.

Rôle:
    Génère des embeddings sémantiques pour les tracks musicales
    en utilisant le modèle ``all-mpnet-base-v2`` de sentence-transformers.
    Ce modèle produit des vecteurs de 768 dimensions compatibles avec
    la base de données pgvector (Vector(768)).

    Choix du modèle:
        - all-mpnet-base-v2 : 768 dimensions, CPU-friendly, standard HuggingFace
        - all-MiniLM-L6-v2 : 384 dimensions seulement (incompatible avec le schéma DB)
        - nomic-embed-text  : modèle Ollama, non disponible nativement via sentence-transformers

Dépendances:
    - backend_worker.utils.logging: logger
    - sentence_transformers: modèle local

Auteur: SoniqueBay Team
"""

import asyncio
from typing import List, Dict, Any, Optional

import httpx
from sentence_transformers import SentenceTransformer

from backend_worker.utils.logging import logger


class OllamaEmbeddingError(Exception):
    """Exception pour les erreurs lors de la génération d'embeddings.

    Le nom de la classe reste historique mais elle est maintenant utilisée
    par le service sentence-transformers.
    """

    pass


class OllamaEmbeddingService:
    """
    Service d'embeddings utilisant sentence-transformers.

    Le modèle **all-mpnet-base-v2** est chargé localement via
    la librairie `sentence-transformers` et produit des vecteurs
    de 768 dimensions compatibles avec le schéma pgvector (Vector(768)).

    Pourquoi all-mpnet-base-v2 ?
        - Produit exactement 768 dimensions (compatible Vector(768) en DB)
        - Disponible nativement via sentence-transformers sans configuration spéciale
        - Optimisé CPU, adapté Raspberry Pi 4
        - Meilleure qualité sémantique que all-MiniLM-L6-v2

    Exemple:
        >>> service = OllamaEmbeddingService()
        >>> embedding = await service.get_embedding("Rock song with heavy guitars")
        >>> len(embedding)
        768
    """

    # TODO: Sur RPi4, surveiller la mémoire lors du chargement du modèle (~420MB)
    MODEL_NAME = "all-mpnet-base-v2"
    EMBEDDING_DIMENSION = 768
    LIBRARY_API_URL = "http://api:8001"

    def __init__(self, library_api_url: str = None) -> None:
        """Initialise le service d'embeddings.

        Args:
            library_api_url: URL de l'API library (défaut: http://api:8001)
        """
        self.library_api_url = library_api_url or self.LIBRARY_API_URL
        # charger le modèle en mémoire (lecture/écriture bloquante)
        self.model = SentenceTransformer(self.MODEL_NAME)
        logger.info(
            f"[EMBEDDING] Service initialisé avec modèle={self.MODEL_NAME}"
        )

    async def get_embedding(self, text: str) -> List[float]:
        """Génère un embedding asynchrone pour un texte donné.

        L'appel est délégué à `sentence-transformers` via
        ``asyncio.to_thread`` pour ne pas bloquer la boucle.

        Args:
            text: Texte à vectoriser

        Returns:
            Vecteur de 768 dimensions

        Raises:
            OllamaEmbeddingError: Si la génération échoue
        """
        try:
            emb = await asyncio.to_thread(self.model.encode, text)
            # encoder renvoie un numpy array ou liste; forcer liste
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            return list(emb)
        except Exception as e:
            logger.error(f"[EMBEDDING] Erreur get_embedding: {e}")
            raise OllamaEmbeddingError(f"Échec génération embedding: {e}")

    async def get_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Génère des embeddings pour une liste de textes.

        Args:
            texts: Liste de textes à vectoriser

        Returns:
            Liste de vecteurs

        Raises:
            OllamaEmbeddingError: Si la génération batch échoue
        """
        try:
            emb = await asyncio.to_thread(
                self.model.encode, texts, convert_to_numpy=True
            )
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            return emb  # type: ignore
        except Exception as e:
            logger.error(f"[EMBEDDING] Erreur batch: {e}")
            raise OllamaEmbeddingError(f"Échec génération embeddings batch: {e}")

    def format_track_text(self, track_data: Dict[str, Any]) -> str:
        """Formate les données d'une track en texte pour embedding.

        Args:
            track_data: Données de la track

        Returns:
            Texte formaté pour Ollama
        """
        parts: List[str] = []

        # Titre (priorité haute)
        if title := track_data.get('title'):
            parts.append(f"Title: {title}")

        # Artiste (priorité haute)
        if artist := track_data.get('artist_name'):
            parts.append(f"Artist: {artist}")

        # Album (priorité moyenne)
        if album := track_data.get('album_title'):
            parts.append(f"Album: {album}")

        # Genre (priorité haute)
        if genre := track_data.get('genre'):
            parts.append(f"Genre: {genre}")
        if genre_main := track_data.get('genre_main'):
            parts.append(f"Genre: {genre_main}")

        # Clé musicale
        if key := track_data.get('key'):
            parts.append(f"Key: {key}")

        # BPM
        if bpm := track_data.get('bpm'):
            parts.append(f"BPM: {bpm}")

        # Tags (mood, atmosphere, etc.)
        tags: List[str] = []
        if mood_tags := track_data.get('mood_tags'):
            if isinstance(mood_tags, list):
                tags.extend(mood_tags)
        if synthetic_tags := track_data.get('synthetic_tags'):
            if isinstance(synthetic_tags, list):
                for tag in synthetic_tags:
                    if isinstance(tag, dict):
                        tags.append(tag.get('tag', ''))
                    else:
                        tags.append(str(tag))
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")

        # Durée
        if duration := track_data.get('duration'):
            parts.append(f"Duration: {duration}s")

        return " | ".join(parts)

    async def fetch_track_from_api(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les données d'une track depuis l'API.

        Args:
            track_id: ID de la track

        Returns:
            Données de la track ou None si non trouvée
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.library_api_url}/api/tracks/{track_id}"
                )
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    f"[EMBEDDING] Track {track_id} non trouvée: "
                    f"{response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"[EMBEDDING] Erreur fetch track {track_id}: {e}")
            return None

    async def fetch_tracks_from_api(
        self, track_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Récupère les données de plusieurs tracks depuis l'API.

        Args:
            track_ids: Liste des IDs de tracks

        Returns:
            Liste des données de tracks
        """
        tracks: List[Dict[str, Any]] = []
        for track_id in track_ids:
            track = await self.fetch_track_from_api(track_id)
            if track:
                tracks.append(track)
        logger.info(
            f"[EMBEDDING] Récupéré {len(tracks)}/{len(track_ids)} tracks"
        )
        return tracks

    async def store_embedding_to_database(
        self, track_id: int, embedding: List[float]
    ) -> bool:
        """Stocke l'embedding dans la base de données via l'API.

        Args:
            track_id: ID de la track
            embedding: Vecteur d'embedding

        Returns:
            True si succès, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                vector_data = {
                    "vector": embedding,
                    "embedding_type": "semantic",
                    "embedding_source": "sentence-transformers",
                    "embedding_model": self.MODEL_NAME
                }
                response = await client.post(
                    f"{self.library_api_url}/api/tracks/{track_id}/embeddings",
                    json=vector_data
                )
                if response.status_code in (200, 201):
                    logger.info(f"[EMBEDDING] Vecteur stocké pour track {track_id}")
                    return True
                else:
                    logger.error(
                        f"[EMBEDDING] Erreur stockage track {track_id}: "
                        f"{response.status_code}"
                    )
                    return False
        except Exception as e:
            logger.error(f"[EMBEDDING] Exception stockage track {track_id}: {e}")
            return False

    async def vectorize_track(
        self, track_id: int, track_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Vectorise une track complète.

        Args:
            track_id: ID de la track
            track_data: Données de la track (optionnel)

        Returns:
            Résultat de la vectorisation
        """
        try:
            # Récupérer les données si non fournies
            if track_data is None:
                track_data = await self.fetch_track_from_api(track_id)
                if not track_data:
                    return {
                        'track_id': track_id,
                        'status': 'error',
                        'message': 'Track non trouvée'
                    }

            # Formater le texte
            text = self.format_track_text(track_data)
            logger.debug(f"[EMBEDDING] Texte formaté: {text[:100]}...")

            # Générer l'embedding
            embedding = await self.get_embedding(text)

            if not embedding or len(embedding) != self.EMBEDDING_DIMENSION:
                logger.warning(
                    f"[EMBEDDING] Dimension inattendue: "
                    f"{len(embedding) if embedding else 0}"
                )

            # Stocker l'embedding
            success = await self.store_embedding_to_database(track_id, embedding)

            return {
                'track_id': track_id,
                'status': 'success' if success else 'warning',
                'vector_dimension': len(embedding),
                'embedding_model': self.MODEL_NAME,
                'storage_success': success
            }

        except OllamaEmbeddingError as e:
            logger.error(f"[EMBEDDING] Erreur vectorisation: {e}")
            return {
                'track_id': track_id,
                'status': 'error',
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"[EMBEDDING] Erreur inattendue: {e}")
            return {
                'track_id': track_id,
                'status': 'error',
                'message': str(e)
            }

    async def vectorize_tracks_batch(
        self, track_ids: List[int]
    ) -> Dict[str, Any]:
        """Vectorise un batch de tracks.

        Args:
            track_ids: Liste des IDs de tracks

        Returns:
            Résultats de la vectorisation batch
        """
        logger.info(
            f"[EMBEDDING] Début vectorisation batch: {len(track_ids)} tracks"
        )

        # Récupérer toutes les tracks
        tracks_data = await self.fetch_tracks_from_api(track_ids)
        if not tracks_data:
            return {
                'status': 'error',
                'message': 'Aucune track trouvée',
                'tracks_requested': len(track_ids),
                'tracks_processed': 0
            }

        # Formater les textes
        texts = [self.format_track_text(t) for t in tracks_data]

        # Générer les embeddings en batch
        try:
            embeddings = await self.get_embeddings_batch(texts)
        except OllamaEmbeddingError:
            # Fallback: traitement individuel
            logger.warning(
                "[EMBEDDING] Batch échoué, passage au traitement individuel"
            )
            embeddings = []
            for text in texts:
                try:
                    emb = await self.get_embedding(text)
                    embeddings.append(emb)
                except Exception:
                    embeddings.append([0.0] * self.EMBEDDING_DIMENSION)

        # Stocker les embeddings
        successful = 0
        failed = 0

        for track, embedding in zip(tracks_data, embeddings):
            track_id = track.get('id')
            if track_id:
                success = await self.store_embedding_to_database(track_id, embedding)
                if success:
                    successful += 1
                else:
                    failed += 1

        result = {
            'status': 'success' if failed == 0 else 'partial',
            'tracks_requested': len(track_ids),
            'tracks_processed': len(tracks_data),
            'successful': successful,
            'failed': failed,
            'vector_dimension': self.EMBEDDING_DIMENSION,
            'embedding_model': self.MODEL_NAME
        }

        logger.info(
            f"[EMBEDDING] Batch terminé: {successful} succès, {failed} échecs"
        )
        return result

    def is_model_available(self) -> bool:
        """Indique si le modèle local est prêt.

        Pour sentence-transformers, la simple existence de
        ``self.model`` suffit.
        """
        return hasattr(self, "model")

    async def pull_model(self) -> bool:
        """No-op pour chargement de modèle local.

        La librairie ``sentence-transformers`` gère le cache
        automatiquement lors de l'instanciation.
        """
        return True
