# -*- coding: UTF-8 -*-
"""
Artist GMM Worker

Celery worker for training Gaussian Mixture Models on artist embeddings
and managing artist similarity recommendations.
"""

import asyncio
from typing import List, Dict, Optional, Any
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
import httpx


@celery.task(name="artist_gmm.train_model", queue="deferred", bind=True)
def train_artist_gmm(self, n_components: int = 10, max_iterations: int = 100) -> Dict[str, Any]:
    """
    Train a Gaussian Mixture Model on artist embeddings via API call.

    Args:
        n_components: Number of clusters for the GMM
        max_iterations: Maximum training iterations

    Returns:
        Training results
    """
    try:
        task_id = self.request.id
        logger.info(f"[ARTIST GMM] Starting GMM training: {n_components} components, task_id={task_id}")

        # Make API call to recommender service
        recommender_url = "http://recommender:8002"  # Docker service name

        async def make_api_call():
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
                response = await client.post(
                    f"{recommender_url}/api/artist-embeddings/train-gmm",
                    json={
                        "n_components": n_components,
                        "max_iterations": max_iterations
                    }
                )
                return response

        # Run async call in sync context
        response = asyncio.run(make_api_call())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[ARTIST GMM] Training completed: {result.get('message', 'Success')}")
            return {
                "task_id": task_id,
                **result
            }
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            logger.error(f"[ARTIST GMM] {error_msg}")
            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[ARTIST GMM] Training failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }


@celery.task(name="artist_gmm.generate_embeddings", queue="deferred", bind=True)
def generate_artist_embeddings(self, artist_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate embeddings for artists via API call.

    Args:
        artist_names: List of artist names to process (None = all artists)

    Returns:
        Generation results
    """
    try:
        task_id = self.request.id
        logger.info(f"[ARTIST GMM] Starting embedding generation, task_id={task_id}")

        # Make API call to recommender service
        recommender_url = "http://recommender:8002"  # Docker service name

        async def make_api_call():
            async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutes timeout
                payload = {"artist_names": artist_names} if artist_names else {}
                response = await client.post(
                    f"{recommender_url}/api/artist-embeddings/generate-embeddings",
                    json=payload
                )
                return response

        # Run async call in sync context
        response = asyncio.run(make_api_call())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[ARTIST GMM] Embedding generation completed: {result}")
            return {
                "task_id": task_id,
                **result
            }
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            logger.error(f"[ARTIST GMM] {error_msg}")
            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[ARTIST GMM] Embedding generation failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }




@celery.task(name="artist_gmm.update_clusters", queue="deferred", bind=True)
def update_artist_clusters(self) -> Dict[str, Any]:
    """
    Update cluster assignments for all artist embeddings via API call.

    This task should be run after GMM training to ensure all embeddings
    have correct cluster assignments based on the latest model.
    """
    try:
        task_id = self.request.id
        logger.info(f"[ARTIST GMM] Starting cluster updates, task_id={task_id}")

        # Make API call to recommender service
        recommender_url = "http://recommender:8002"  # Docker service name

        async def make_api_call():
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes timeout
                response = await client.post(
                    f"{recommender_url}/api/artist-embeddings/update-clusters"
                )
                return response

        # Run async call in sync context
        response = asyncio.run(make_api_call())

        if response.status_code == 200:
            result = response.json()
            logger.info(f"[ARTIST GMM] Cluster updates completed: {result}")
            return {
                "task_id": task_id,
                **result
            }
        else:
            error_msg = f"API call failed with status {response.status_code}: {response.text}"
            logger.error(f"[ARTIST GMM] {error_msg}")
            return {
                "task_id": task_id,
                "success": False,
                "error": error_msg
            }

    except Exception as e:
        logger.error(f"[ARTIST GMM] Cluster update failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }


def _generate_artist_embedding(artist, db) -> Optional[List[float]]:
    """
    Generate embedding vector for an artist based on their tracks.
    
    Args:
        artist: Artist object with tracks
        db: Database session
        
    Returns:
        List of floats representing the embedding, or None if no tracks
    """
    if not artist.tracks or len(artist.tracks) == 0:
        return None
    
    # Extract features from tracks
    features = []
    for track in artist.tracks:
        # Basic audio features
        bpm = getattr(track, 'bpm', 120) or 120
        danceability = getattr(track, 'danceability', 0.5) or 0.5
        duration = getattr(track, 'duration', 180) or 180
        
        # Normalize features
        features.extend([
            (bpm - 120) / 60,  # Normalize BPM around 120
            (danceability - 0.5) * 2,  # Normalize danceability to [-1, 1]
            (duration - 180) / 120,  # Normalize duration around 3 minutes
        ])
    
    # Calculate statistics
    if len(features) >= 3:
        # Return mean of each feature type
        n_tracks = len(artist.tracks)
        bpm_mean = sum(features[::3]) / n_tracks
        dance_mean = sum(features[1::3]) / n_tracks
        duration_mean = sum(features[2::3]) / n_tracks
        
        # Add variance as additional features
        bpm_var = sum((f - bpm_mean) ** 2 for f in features[::3]) / n_tracks if n_tracks > 1 else 0
        dance_var = sum((f - dance_mean) ** 2 for f in features[1::3]) / n_tracks if n_tracks > 1 else 0
        
        embedding = [
            bpm_mean, dance_mean, duration_mean,
            bpm_var, dance_var,
            float(n_tracks) / 100.0,  # Normalized track count
        ]
        
        return embedding
    
    return None
