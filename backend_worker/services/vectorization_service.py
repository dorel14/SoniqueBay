"""
Service de vectorisation pour les tracks SoniqueBay.
Gère le calcul et le stockage des embeddings vectoriels des pistes musicales.

Auteur : Kilo Code
Dépendances : httpx, numpy, sentence-transformers, scikit-learn, backend_worker.utils.logging
"""
import asyncio
import httpx
import numpy as np
from typing import List, Optional, Dict, Any
import os
import warnings
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import StandardScaler
from backend_worker.utils.logging import logger

warnings.filterwarnings('ignore')


class VectorizationService:
    """
    Service pour la vectorisation des tracks utilisant un modèle d'embedding.

    Ce service gère la génération et le stockage des vecteurs d'embedding
    pour les pistes musicales, permettant la recherche sémantique et
    les recommandations basées sur le contenu.

    Auteur : Kilo Code
    Dépendances : httpx, numpy, backend_worker.utils.logging
    """

    def __init__(self):
        """
        Initialise le service de vectorisation.

        Configure les paramètres du modèle d'embedding et l'URL de l'API.
        """
        self.api_url = os.getenv("API_URL", "http://backend:8001")
        # Configuration du modèle d'embedding
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.text_embedding_dimension = 384  # Dimension par défaut pour all-MiniLM-L6-v2
        self.numeric_features_count = 12  # Nombre de features numériques
        self.embedding_dimension = self.text_embedding_dimension + self.numeric_features_count

        # Initialisation du modèle sentence-transformers
        try:
            self.sentence_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Modèle sentence-transformers chargé: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Erreur chargement modèle sentence-transformers: {e}")
            self.sentence_model = None

        # Initialisation du scaler sklearn pour les features numériques
        self.scaler = StandardScaler()

    async def generate_embedding(self, track_data: Dict[str, Any]) -> List[float]:
        """
        Génère un embedding vectoriel pour une track.

        Utilise les métadonnées textuelles et numériques de la track pour créer un vecteur
        représentatif combinant embeddings textuels et features audio normalisées.

        Args:
            track_data: Données de la track (titre, artiste, genre, etc.)

        Returns:
            Liste des valeurs du vecteur d'embedding normalisé

        Raises:
            Exception: En cas d'erreur de génération
        """
        try:
            if not self.sentence_model:
                raise Exception("Modèle sentence-transformers non initialisé")

            # Extraction des features textuelles
            text_features = self._extract_text_features(track_data)

            # Extraction des features numériques
            numeric_features = self._extract_numeric_features(track_data)

            # Génération de l'embedding textuel
            text_embedding = self.sentence_model.encode(text_features, convert_to_numpy=True)

            # Normalisation des features numériques
            if numeric_features:
                numeric_array = np.array(numeric_features).reshape(1, -1)
                numeric_scaled = self.scaler.fit_transform(numeric_array).flatten()
            else:
                numeric_scaled = np.zeros(self.numeric_features_count)

            # Combinaison des embeddings
            combined_embedding = np.concatenate([text_embedding, numeric_scaled])

            # Normalisation finale du vecteur combiné
            norm = np.linalg.norm(combined_embedding)
            if norm > 0:
                combined_embedding = combined_embedding / norm

            logger.debug(f"Embedding généré pour track {track_data.get('id', 'unknown')}: dimension {len(combined_embedding)}")
            return combined_embedding.tolist()

        except Exception as e:
            logger.error(f"Erreur génération embedding: {str(e)}")
            # Retourner un vecteur nul en cas d'erreur
            return [0.0] * self.embedding_dimension

    def _extract_text_features(self, track_data: Dict[str, Any]) -> str:
        """
        Extrait les features textuelles d'une track pour la vectorisation.

        Args:
            track_data: Données de la track

        Returns:
            Chaîne de caractères combinant les features textuelles
        """
        features = []

        # Titre de la track
        if track_data.get('title'):
            features.append(track_data['title'])

        # Artiste
        if track_data.get('artist_name'):
            features.append(track_data['artist_name'])

        # Album
        if track_data.get('album_title'):
            features.append(track_data['album_title'])

        # Featured artists
        if track_data.get('featured_artists'):
            features.append(track_data['featured_artists'])

        # Genres
        if track_data.get('genre'):
            features.append(track_data['genre'])
        if track_data.get('musicbrainz_genre'):
            features.append(track_data['musicbrainz_genre'])
        if track_data.get('genre_main'):
            features.append(track_data['genre_main'])

        # Clés musicales
        if track_data.get('key'):
            features.append(track_data['key'])
        if track_data.get('scale'):
            features.append(track_data['scale'])
        if track_data.get('camelot_key'):
            features.append(track_data['camelot_key'])

        # Tags
        if track_data.get('genre_tags'):
            if isinstance(track_data['genre_tags'], list):
                features.extend([tag.get('name', tag) if isinstance(tag, dict) else str(tag) for tag in track_data['genre_tags']])
            else:
                features.append(str(track_data['genre_tags']))
        if track_data.get('mood_tags'):
            if isinstance(track_data['mood_tags'], list):
                features.extend([tag.get('name', tag) if isinstance(tag, dict) else str(tag) for tag in track_data['mood_tags']])
            else:
                features.append(str(track_data['mood_tags']))

        return " ".join(features)

    def _extract_numeric_features(self, track_data: Dict[str, Any]) -> List[float]:
        """
        Extrait les features numériques d'une track pour la vectorisation.

        Args:
            track_data: Données de la track

        Returns:
            Liste des valeurs numériques normalisables
        """
        features = []

        # Durée en secondes
        duration = track_data.get('duration')
        features.append(float(duration) if duration else 0.0)

        # Année (conversion string vers int)
        year = track_data.get('year')
        try:
            features.append(float(year) if year else 0.0)
        except (ValueError, TypeError):
            features.append(0.0)

        # Bitrate
        bitrate = track_data.get('bitrate')
        features.append(float(bitrate) if bitrate else 0.0)

        # BPM
        bpm = track_data.get('bpm')
        features.append(float(bpm) if bpm else 0.0)

        # Caractéristiques audio
        danceability = track_data.get('danceability')
        features.append(float(danceability) if danceability else 0.0)

        mood_happy = track_data.get('mood_happy')
        features.append(float(mood_happy) if mood_happy else 0.0)

        mood_aggressive = track_data.get('mood_aggressive')
        features.append(float(mood_aggressive) if mood_aggressive else 0.0)

        mood_party = track_data.get('mood_party')
        features.append(float(mood_party) if mood_party else 0.0)

        mood_relaxed = track_data.get('mood_relaxed')
        features.append(float(mood_relaxed) if mood_relaxed else 0.0)

        instrumental = track_data.get('instrumental')
        features.append(float(instrumental) if instrumental else 0.0)

        acoustic = track_data.get('acoustic')
        features.append(float(acoustic) if acoustic else 0.0)

        tonal = track_data.get('tonal')
        features.append(float(tonal) if tonal else 0.0)

        return features

    async def store_track_vector(self, track_id: int, embedding: List[float]) -> bool:
        """
        Stocke le vecteur d'une track dans la base de données via sqlite-vec.

        Args:
            track_id: ID de la track
            embedding: Vecteur d'embedding à stocker

        Returns:
            True si le stockage a réussi, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Utiliser le nouvel endpoint sqlite-vec
                vector_data = {
                    "track_id": track_id,
                    "embedding": embedding
                }

                response = await client.post(
                    f"{self.api_url}/api/track-vectors/",
                    json=vector_data
                )

                if response.status_code in (200, 201):
                    logger.info(f"Vecteur stocké pour track {track_id} via sqlite-vec")
                    return True
                else:
                    logger.error(f"Erreur stockage vecteur track {track_id}: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Exception stockage vecteur track {track_id}: {str(e)}")
            return False

    async def get_track_data(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'une track depuis l'API.

        Args:
            track_id: ID de la track

        Returns:
            Données de la track ou None si non trouvée
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_url}/api/tracks/{track_id}")

                if response.status_code == 200:
                    return await response.json()
                else:
                    logger.error(f"Erreur récupération track {track_id}: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Exception récupération track {track_id}: {str(e)}")
            return None


async def vectorize_single_track(track_id: int) -> Dict[str, Any]:
    """
    Vectorise une track unique.

    Args:
        track_id: ID de la track à vectoriser

    Returns:
        Résultat de l'opération
    """
    service = VectorizationService()

    try:
        # Récupération des données de la track
        track_data = await service.get_track_data(track_id)
        if not track_data:
            return {"error": f"Track {track_id} non trouvée"}

        # Génération de l'embedding
        embedding = await service.generate_embedding(track_data)

        # Stockage du vecteur
        success = await service.store_track_vector(track_id, embedding)

        if success:
            logger.info(f"Vectorisation réussie pour track {track_id}")
            return {"track_id": track_id, "status": "success", "vector_dimension": len(embedding)}
        else:
            return {"track_id": track_id, "status": "failed", "error": "storage_failed"}

    except Exception as e:
        logger.error(f"Erreur vectorisation track {track_id}: {str(e)}")
        return {"track_id": track_id, "status": "error", "error": str(e)}


async def vectorize_tracks(track_ids: List[int]) -> Dict[str, Any]:
    """
    Vectorise une liste de tracks en parallèle.

    Args:
        track_ids: Liste des IDs de tracks à vectoriser

    Returns:
        Résultats de l'opération pour chaque track
    """
    logger.info(f"Démarrage vectorisation de {len(track_ids)} tracks")

    # Traitement en parallèle avec limite de concurrence
    semaphore = asyncio.Semaphore(10)  # Max 10 vectorisations simultanées

    async def vectorize_with_semaphore(track_id: int):
        async with semaphore:
            return await vectorize_single_track(track_id)

    # Lancer toutes les vectorisations
    tasks = [vectorize_with_semaphore(track_id) for track_id in track_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Traiter les résultats
    successful = 0
    failed = 0
    errors = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Exception pour track {track_ids[i]}: {str(result)}")
            failed += 1
            errors.append({"track_id": track_ids[i], "error": str(result)})
        elif result.get("status") == "success":
            successful += 1
        else:
            failed += 1
            errors.append(result)

    logger.info(f"Vectorisation terminée: {successful} succès, {failed} échecs")

    return {
        "total": len(track_ids),
        "successful": successful,
        "failed": failed,
        "errors": errors
    }


async def vectorize_and_store_batch(track_ids: List[int]) -> Dict[str, Any]:
    """
    Vectorise et stocke un batch de tracks en utilisant sqlite-vec.

    Args:
        track_ids: Liste des IDs de tracks à vectoriser

    Returns:
        Résultats de l'opération
    """
    logger.info(f"Démarrage vectorisation batch de {len(track_ids)} tracks")

    service = VectorizationService()
    successful = 0
    failed = 0
    errors = []

    # Collecter tous les vecteurs
    vectors_to_store = []

    for track_id in track_ids:
        try:
            # Récupération des données de la track
            track_data = await service.get_track_data(track_id)
            if not track_data:
                failed += 1
                errors.append({"track_id": track_id, "error": "track_not_found"})
                continue

            # Génération de l'embedding
            embedding = await service.generate_embedding(track_data)

            vectors_to_store.append({
                "track_id": track_id,
                "embedding": embedding
            })

        except Exception as e:
            logger.error(f"Erreur génération embedding pour track {track_id}: {str(e)}")
            failed += 1
            errors.append({"track_id": track_id, "error": str(e)})

    # Stocker en batch via l'API
    if vectors_to_store:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{service.api_url}/api/track-vectors/batch",
                    json=vectors_to_store
                )

                if response.status_code == 201:
                    successful = len(vectors_to_store)
                    logger.info(f"Batch stocké avec succès: {successful} vecteurs")
                else:
                    logger.error(f"Erreur stockage batch: {response.status_code} - {response.text}")
                    failed += len(vectors_to_store)
                    errors.extend([{"track_id": v["track_id"], "error": "storage_failed"} for v in vectors_to_store])

        except Exception as e:
            logger.error(f"Exception stockage batch: {str(e)}")
            failed += len(vectors_to_store)
            errors.extend([{"track_id": v["track_id"], "error": str(e)} for v in vectors_to_store])

    logger.info(f"Vectorisation batch terminée: {successful} succès, {failed} échecs")

    return {
        "total": len(track_ids),
        "successful": successful,
        "failed": failed,
        "errors": errors
    }


async def search_similar_tracks(query_track_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Recherche les tracks similaires à une track donnée.

    Args:
        query_track_id: ID de la track de référence
        limit: Nombre maximum de résultats

    Returns:
        Liste des tracks similaires avec leur distance
    """
    service = VectorizationService()

    try:
        # Récupérer le vecteur de la track de référence
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{service.api_url}/api/track-vectors/vec/{query_track_id}")

            if response.status_code != 200:
                logger.error(f"Vecteur non trouvé pour track {query_track_id}")
                return []

            vector_data = response.json()
            query_embedding = vector_data['embedding']

        # Effectuer la recherche
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_data = {
                "track_id": query_track_id,
                "embedding": query_embedding
            }

            response = await client.post(
                f"{service.api_url}/api/track-vectors/search?limit={limit}",
                json=search_data
            )

            if response.status_code == 200:
                results = response.json()
                logger.info(f"Recherche similaire trouvée {len(results)} résultats pour track {query_track_id}")
                return results
            else:
                logger.error(f"Erreur recherche similaire: {response.status_code} - {response.text}")
                return []

    except Exception as e:
        logger.error(f"Exception recherche similaire pour track {query_track_id}: {str(e)}")
        return []