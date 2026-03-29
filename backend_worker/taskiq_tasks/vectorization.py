"""Tâches TaskIQ pour la vectorisation.
Migration de celery_tasks.py vers TaskIQ.
"""
import asyncio
from typing import List, Dict, Any, Optional
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger
import os

# Note: We are using asyncio.to_thread for CPU-bound operations (sentence-transformers)
# and httpx.AsyncClient for async HTTP requests.

@broker.task
async def calculate_vector_task(track_id: int, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calcule le vecteur d'une track via sentence-transformers.
    Converti en async pour TaskIQ.

    Pipeline:
        1. Récupère les données de la track via l'API (async)
        2. Génère l'embedding avec sentence-transformers (CPU-bound, via asyncio.to_thread)
        3. Stocke le vecteur via l'API backend (async)

    Args:
        track_id: ID de la track
        metadata: Métadonnées optionnelles de la track

    Returns:
        Résultat du calcul avec statut et métadonnées
    """
    logger.info(f"[TASKIQ|VECTOR] Démarrage calcul vecteur: track_id={track_id}")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Import de sentence-transformers et httpx
        from sentence_transformers import SentenceTransformer
        import httpx
        
        # Chargement du modèle (we load it once per worker? but for simplicity, we load it each time in a thread)
        # In a production setting, we might want to cache the model, but for now we load it in the thread.
        EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Same as in celery_tasks.py
        
        # Récupérer les métadonnées de la track via l'API si non fournies
        track_metadata = metadata or {}
        if not track_metadata:
            api_url = os.getenv("API_URL", "http://api:8001")
            async with httpx.AsyncClient(timeout=30) as client:
                try:
                    response = await client.get(f"{api_url}/api/tracks/{track_id}")
                    if response.status_code == 200:
                        track_metadata = response.json()
                except Exception as e:
                    logger.warning(f"[TASKIQ|VECTOR] Impossible de récupérer les métadonnées: {e}")
        
        # Construire le texte à vectoriser à partir des métadonnées
        text_parts = []
        if track_metadata.get('title'):
            text_parts.append(track_metadata['title'])
        if track_metadata.get('artist'):
            text_parts.append(track_metadata['artist'])
        if track_metadata.get('album'):
            text_parts.append(track_metadata['album'])
        if track_metadata.get('genre'):
            text_parts.append(track_metadata['genre'])
        
        text_to_embed = " - ".join(text_parts) if text_parts else f"track_{track_id}"
        
        # Générer l'embedding in a thread to avoid blocking the event loop
        def _encode_text(text: str) -> List[float]:
            model = SentenceTransformer(EMBEDDING_MODEL)
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        
        embedding_list = await asyncio.to_thread(_encode_text, text_to_embed)
        
        # Stocker le vecteur via l'API
        api_url = os.getenv("API_URL", "http://api:8001")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{api_url}/api/tracks/{track_id}/vector",
                json={"vector": embedding_list, "model": EMBEDDING_MODEL}
            )
            if response.status_code not in (200, 201):
                raise Exception(f"Erreur stockage vecteur: {response.status_code}")
        
        calculation_time = asyncio.get_event_loop().time() - start_time
        
        logger.info(
            f"[TASKIQ|VECTOR] Vecteur calculé et stocké: track_id={track_id}, "
            f"dimensions={len(embedding_list)}, time={calculation_time:.2f}s"
        )
        
        return {
            'task_id': None,  # TaskIQ doesn't provide task_id in the same way
            'track_id': track_id,
            'status': 'success',
            'embedding_model': EMBEDDING_MODEL,
            'dimensions': len(embedding_list),
            'calculation_time': calculation_time
        }
        
    except Exception as e:
        calculation_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"[TASKIQ|VECTOR] Erreur vectorisation: {str(e)}")
        return {
            'task_id': None,
            'track_id': track_id,
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__,
            'calculation_time': calculation_time,
            'embedding_model': EMBEDDING_MODEL if 'EMBEDDING_MODEL' in locals() else 'unknown'
        }


@broker.task
async def calculate_vector_batch_task(track_ids: List[int]) -> Dict[str, Any]:
    """
    Calcule les vecteurs d'un batch de tracks via sentence-transformers.
    Converti en async pour TaskIQ.

    Args:
        track_ids: Liste des IDs de tracks
        
    Returns:
        Résultat du calcul batch
    """
    logger.info(f"[TASKIQ|VECTOR] Démarrage batch: {len(track_ids)} tracks")
    
    start_time = asyncio.get_event_loop().time()
    
    successful = 0
    failed = 0
    errors = []
    
    try:
        # Import de sentence-transformers et httpx
        from sentence_transformers import SentenceTransformer
        import httpx
        
        # Chargement du modèle (we load it once per batch in a thread to avoid blocking)
        EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Same as in celery_tasks.py
        api_url = os.getenv("API_URL", "http://api:8001")
        
        # We'll process each track in parallel but limit concurrency to avoid overloading
        # We'll use a semaphore to limit the number of concurrent HTTP requests and model encodings.
        # However, note that the model encoding is CPU-bound and we are using asyncio.to_thread.
        # We'll create a semaphore for the number of concurrent tracks we process.
        # We'll set it to 2 as in the original Celery implementation for metadata extraction.
        semaphore = asyncio.Semaphore(2)
        
        async def process_single_track(track_id: int) -> None:
            nonlocal successful, failed, errors
            async with semaphore:
                try:
                    # Récupérer les métadonnées
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.get(f"{api_url}/api/tracks/{track_id}")
                        if response.status_code != 200:
                            failed += 1
                            errors.append(f"Track {track_id}: non trouvé")
                            return
                        
                        track_metadata = response.json()
                        
                        # Construire le texte à vectoriser
                        text_parts = []
                        if track_metadata.get('title'):
                            text_parts.append(track_metadata['title'])
                        if track_metadata.get('artist'):
                            text_parts.append(track_metadata['artist'])
                        if track_metadata.get('album'):
                            text_parts.append(track_metadata['album'])
                        if track_metadata.get('genre'):
                            text_parts.append(track_metadata['genre'])
                        
                        text_to_embed = " - ".join(text_parts) if text_parts else f"track_{track_id}"
                        
                        # Générer l'embedding in a thread
                        def _encode_text(text: str) -> List[float]:
                            model = SentenceTransformer(EMBEDDING_MODEL)
                            embedding = model.encode(text, convert_to_numpy=True)
                            return embedding.tolist()
                        
                        embedding_list = await asyncio.to_thread(_encode_text, text_to_embed)
                        
                        # Stocker le vecteur
                        async with httpx.AsyncClient(timeout=30) as client:
                            store_response = await client.post(
                                f"{api_url}/api/tracks/{track_id}/vector",
                                json={"vector": embedding_list, "model": EMBEDDING_MODEL}
                            )
                            
                            if store_response.status_code in (200, 201):
                                successful += 1
                            else:
                                failed += 1
                                errors.append(f"Track {track_id}: erreur stockage {store_response.status_code}")
                                
                except Exception as e:
                    failed += 1
                    errors.append(f"Track {track_id}: {str(e)}")
        
        # Create tasks for each track
        tasks = [process_single_track(track_id) for track_id in track_ids]
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        calculation_time = asyncio.get_event_loop().time() - start_time
        
        logger.info(
            f"[TASKIQ|VECTOR] Batch terminé: {successful} succès, "
            f"{failed} échecs en {calculation_time:.2f}s"
        )
        
        return {
            'task_id': None,
            'status': 'success' if failed == 0 else 'partial',
            'successful': successful,
            'failed': failed,
            'errors': errors[:10],  # Limiter le nombre d'erreurs retournées
            'calculation_time': calculation_time,
            'embedding_model': EMBEDDING_MODEL
        }
        
    except Exception as e:
        calculation_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"[TASKIQ|VECTOR] Erreur batch: {str(e)}")
        return {
            'task_id': None,
            'status': 'error',
            'message': str(e),
            'calculation_time': calculation_time,
            'embedding_model': EMBEDDING_MODEL if 'EMBEDDING_MODEL' in locals() else 'unknown'
        }