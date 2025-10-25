"""
TÂCHES D'INSERTION OPTIMISÉES POUR HAUTE PERFORMANCE

Insertion directe en base de données avec SQLAlchemy Core
pour éviter les goulots d'étranglement HTTP.
"""

import time
from typing import List, Dict, Any
import os

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event



@celery.task(name='insert_batch_direct', queue='insert', bind=True)
def insert_batch_direct(self, insertion_data: Dict[str, Any]):
    """
    Insère en base de données via l'API HTTP uniquement (pas d'accès direct BDD).

    Utilise des connexions HTTP persistantes et des batches volumineux
    pour maximiser les performances tout en respectant l'architecture.

    Args:
        insertion_data: Données groupées prêtes pour insertion

    Returns:
        Résultat de l'insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[INSERT_DIRECT] Démarrage insertion directe: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} pistes")
        logger.info(f"[INSERT_DIRECT] Task ID: {task_id}")

        # Récupérer les données
        artists_data = insertion_data.get('artists', [])
        albums_data = insertion_data.get('albums', [])
        tracks_data = insertion_data.get('tracks', [])

        if not tracks_data and not artists_data and not albums_data:
            logger.warning("[INSERT_DIRECT] Aucune donnée à insérer")
            return {
                'task_id': task_id,
                'success': True,
                'artists_inserted': 0,
                'albums_inserted': 0,
                'tracks_inserted': 0
            }

        # Utiliser httpx pour des connexions HTTP optimisées
        import httpx

        # Configuration client HTTP haute performance
        with httpx.Client(
            base_url="http://backend:8001",
            timeout=httpx.Timeout(300.0),  # 5 minutes timeout
            limits=httpx.Limits(
                max_keepalive_connections=50,
                max_connections=100,
                keepalive_expiry=300.0
            )
        ) as client:

            inserted_counts = {
                'artists': 0,
                'albums': 0,
                'tracks': 0
            }

            # Étape 1: Insertion des artistes par batches
            if artists_data:
                logger.info(f"[INSERT_DIRECT] Insertion de {len(artists_data)} artistes en batches")

                # Diviser en batches de 500 artistes
                batch_size = 500
                for i in range(0, len(artists_data), batch_size):
                    batch = artists_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/artists/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['artists'] += len(result)
                            logger.debug(f"[INSERT_DIRECT] Batch artistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT_DIRECT] Erreur batch artistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT_DIRECT] Exception batch artistes: {e}")

            # Étape 2: Insertion des albums par batches
            if albums_data:
                logger.info(f"[INSERT_DIRECT] Insertion de {len(albums_data)} albums en batches")

                # Diviser en batches de 300 albums
                batch_size = 300
                for i in range(0, len(albums_data), batch_size):
                    batch = albums_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/albums/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['albums'] += len(result)
                            logger.debug(f"[INSERT_DIRECT] Batch albums {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT_DIRECT] Erreur batch albums: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT_DIRECT] Exception batch albums: {e}")

            # Étape 3: Insertion des pistes par batches
            if tracks_data:
                logger.info(f"[INSERT_DIRECT] Insertion de {len(tracks_data)} pistes en batches")

                # Diviser en batches de 1000 pistes (taille optimale)
                batch_size = 1000
                for i in range(0, len(tracks_data), batch_size):
                    batch = tracks_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/tracks/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['tracks'] += len(result)
                            logger.debug(f"[INSERT_DIRECT] Batch pistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT_DIRECT] Erreur batch pistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT_DIRECT] Exception batch pistes: {e}")

            # Métriques finales
            total_time = time.time() - start_time

            logger.info(f"[INSERT_DIRECT] Insertion terminée: {inserted_counts} en {total_time:.2f}s")

            # Publier les métriques
            publish_event("insert_progress", {
                "task_id": task_id,
                "artists_inserted": inserted_counts['artists'],
                "albums_inserted": inserted_counts['albums'],
                "tracks_inserted": inserted_counts['tracks'],
                "insertion_time": total_time,
                "insertions_per_second": sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            })

            result = {
                'task_id': task_id,
                'success': True,
                **inserted_counts,
                'insertion_time': total_time,
                'insertions_per_second': sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }

            return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[INSERT_DIRECT] Erreur insertion après {error_time:.2f}s: {str(e)}")

        # Publier l'erreur
        publish_event("insert_error", {
            "task_id": task_id,
            "error": str(e),
            "duration": error_time
        })

        raise


@celery.task(name='insert_batch_optimized', queue='insert', bind=True)
def insert_batch_optimized(self, insertion_data: Dict[str, Any]):
    """
    Insère en base de données via l'API HTTP de manière optimisée.

    Utilise des connexions HTTP persistantes et des batches volumineux
    pour maximiser les performances tout en respectant l'architecture.

    Args:
        insertion_data: Données groupées prêtes pour insertion

    Returns:
        Résultat de l'insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[INSERT] Démarrage insertion optimisée: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} pistes")
        logger.info(f"[INSERT] Task ID: {task_id}")

        # Récupérer les données
        artists_data = insertion_data.get('artists', [])
        albums_data = insertion_data.get('albums', [])
        tracks_data = insertion_data.get('tracks', [])

        if not tracks_data:
            logger.warning("[INSERT] Aucun piste à insérer")
            return {
                'task_id': task_id,
                'success': True,
                'artists_inserted': 0,
                'albums_inserted': 0,
                'tracks_inserted': 0
            }

        # Utiliser httpx pour des connexions HTTP optimisées
        import httpx

        # Configuration client HTTP haute performance
        with httpx.Client(
            base_url= os.getenv("API_URL", "http://backend:8001"),
            timeout=httpx.Timeout(300.0),  # 5 minutes timeout
            limits=httpx.Limits(
                max_keepalive_connections=50,
                max_connections=100,
                keepalive_expiry=300.0
            )
        ) as client:

            inserted_counts = {
                'artists': 0,
                'albums': 0,
                'tracks': 0
            }

            # Étape 1: Insertion des artistes par batches
            if artists_data:
                logger.info(f"[INSERT] Insertion de {len(artists_data)} artistes en batches")

                # Diviser en batches de 500 artistes
                batch_size = 500
                for i in range(0, len(artists_data), batch_size):
                    batch = artists_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/artists/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['artists'] += len(result)
                            logger.debug(f"[INSERT] Batch artistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch artistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch artistes: {e}")

            # Étape 2: Insertion des albums par batches
            if albums_data:
                logger.info(f"[INSERT] Insertion de {len(albums_data)} albums en batches")

                # Diviser en batches de 300 albums
                batch_size = 300
                for i in range(0, len(albums_data), batch_size):
                    batch = albums_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/albums/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['albums'] += len(result)
                            logger.debug(f"[INSERT] Batch albums {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch albums: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch albums: {e}")

            # Étape 3: Insertion des pistes par batches
            if tracks_data:
                logger.info(f"[INSERT] Insertion de {len(tracks_data)} pistes en batches")

                # Diviser en batches de 1000 pistes (taille optimale)
                batch_size = 1000
                for i in range(0, len(tracks_data), batch_size):
                    batch = tracks_data[i:i + batch_size]

                    try:
                        response = client.post(
                            "/api/tracks/batch",
                            json=batch,
                            headers={'Content-Type': 'application/json'}
                        )

                        if response.status_code in (200, 201):
                            result = response.json()
                            inserted_counts['tracks'] += len(result)
                            logger.debug(f"[INSERT] Batch pistes {i//batch_size + 1}: {len(result)} insérés")
                        else:
                            logger.error(f"[INSERT] Erreur batch pistes: {response.status_code} - {response.text}")

                    except Exception as e:
                        logger.error(f"[INSERT] Exception batch pistes: {e}")

            # Métriques finales
            total_time = time.time() - start_time

            logger.info(f"[INSERT] Insertion terminée: {inserted_counts} en {total_time:.2f}s")

            # Publier les métriques
            publish_event("insert_progress", {
                "task_id": task_id,
                "artists_inserted": inserted_counts['artists'],
                "albums_inserted": inserted_counts['albums'],
                "tracks_inserted": inserted_counts['tracks'],
                "insertion_time": total_time,
                "insertions_per_second": sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            })

            result = {
                'task_id': task_id,
                'success': True,
                **inserted_counts,
                'insertion_time': total_time,
                'insertions_per_second': sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }

            return result

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[INSERT] Erreur insertion après {error_time:.2f}s: {str(e)}")

        # Publier l'erreur
        publish_event("insert_error", {
            "task_id": task_id,
            "error": str(e),
            "duration": error_time
        })

        raise

