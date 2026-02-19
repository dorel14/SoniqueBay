# -*- coding: UTF-8 -*-
"""
Router pour les endpoints API du clustering GMM des artistes.

Ce router expose les endpoints pour:
- Déclencher le clustering complet des artistes
- Cluster un artiste spécifique
- Récupérer le cluster d'un artiste
- Récupérer les artistes similaires
- Rafraîchir les clusters anciens
- Obtenir le statut du clustering

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.gmm_schema import (
    ClusterResponse,
    SimilarArtistsResponse,
    ClusterStatusResponse,
    ClusteringTaskResponse,
    RefreshClustersResponse,
)

from backend.api.utils.database import get_async_session
from backend.api.utils.celery_app import celery_app
from backend.api.utils.logging import logger
from backend.api.services.artist_embedding_service import ArtistEmbeddingService
from backend.api.services.artist_service import ArtistService


# ============================================================================
# Router GMM
# ============================================================================

router = APIRouter(prefix="/api/gmm", tags=["GMM Clustering"])


# ============================================================================
# Helpers
# ============================================================================

async def _get_artist_by_id(
    artist_id: int, db: AsyncSession
) -> Optional[dict]:
    """Récupère les informations d'un artiste par son ID.

    Args:
        artist_id: Identifiant de l'artiste
        db: Session de base de données

    Returns:
        Dictionnaire avec les informations de l'artiste ou None
    """
    try:
        artist_service = ArtistService(db)
        artist = await artist_service.get_artist_by_id(artist_id)
        if artist:
            return {
                "id": artist.id,
                "name": artist.name,
            }
        return None
    except Exception as e:
        logger.error(f"[GMM] Erreur récupération artiste {artist_id}: {e}")
        return None


async def _get_artist_embedding_info(
    artist_id: int, db: AsyncSession
) -> Optional[dict]:
    """Récupère les informations de clustering d'un artiste.

    Args:
        artist_id: Identifiant de l'artiste
        db: Session de base de données

    Returns:
        Dictionnaire avec les informations de clustering ou None
    """
    try:
        embedding_service = ArtistEmbeddingService(db)
        artist = await _get_artist_by_id(artist_id, db)
        if not artist:
            return None

        embedding = await embedding_service.get_embedding_by_artist(artist["name"])
        if embedding:
            return {
                "artist_id": artist_id,
                "artist_name": artist["name"],
                "cluster": embedding.cluster,
                "cluster_probabilities": embedding.cluster_probabilities,
                "vector": embedding.vector,
            }
        return None
    except Exception as e:
        logger.error(f"[GMM] Erreur récupération embedding artiste {artist_id}: {e}")
        return None


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/cluster",
    response_model=ClusteringTaskResponse,
    summary="Déclencher le clustering complet",
    description="Lance le clustering GMM de tous les artistes via une tâche Celery.",
)
async def trigger_full_clustering(
    force_refresh: bool = False,
) -> ClusteringTaskResponse:
    """Déclenche le clustering de tous les artistes.

    Cette endpoint lance une tâche Celery asynchrone pour effectuer
    le clustering GMM complet de tous les artistes de la bibliothèque.

    Args:
        force_refresh: Force le reclustering même si récent
        background_tasks: Tâches de fond FastAPI

    Returns:
        Identifiant de la tâche Celery et message de confirmation

    Raises:
        HTTPException: Si l'envoi de la tâche échoue
    """
    try:
        logger.info(f"[GMM] Déclenchement clustering complet (force_refresh={force_refresh})")

        # Envoyer la tâche Celery
        task = celery_app.send_task(
            "gmm.cluster_all_artists",
            args=[force_refresh],
            queue="gmm",
            priority=5,
        )

        logger.info(f"[GMM] Tâche Celery créée: {task.id}")

        return ClusteringTaskResponse(
            task_id=task.id,
            message="Tâche de clustering GMM créée avec succès",
            status="pending",
        )

    except Exception as e:
        logger.error(f"[GMM] Erreur lors du déclenchement du clustering: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du déclenchement du clustering: {str(e)}",
        )


@router.post(
    "/cluster/{artist_id}",
    response_model=ClusterResponse,
    summary="Cluster un artiste spécifique",
    description="Cluster un artiste spécifique et retourne les informations de cluster.",
)
async def cluster_single_artist(
    artist_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> ClusterResponse:
    """Cluster un artiste spécifique.

    Récupère ou calcule le cluster GMM pour un artiste donné.

    Args:
        artist_id: Identifiant de l'artiste à clusteriser
        db: Session de base de données

    Returns:
        Informations de clustering de l'artiste

    Raises:
        HTTPException: Si l'artiste n'existe pas ou erreur de traitement
    """
    try:
        logger.info(f"[GMM] Clustering artiste {artist_id}")

        # Vérifier que l'artiste existe
        artist_info = await _get_artist_by_id(artist_id, db)
        if not artist_info:
            logger.warning(f"[GMM] Artiste {artist_id} non trouvé")
            raise HTTPException(
                status_code=404,
                detail=f"Artiste avec ID {artist_id} non trouvé",
            )

        # Récupérer les informations de clustering
        embedding_info = await _get_artist_embedding_info(artist_id, db)

        if embedding_info and embedding_info.get("cluster") is not None:
            # L'artiste a déjà un cluster
            cluster_label = embedding_info["cluster"]

            # Parser les probabilités
            cluster_probability = 0.0
            if embedding_info.get("cluster_probabilities"):
                import json

                try:
                    probs = json.loads(embedding_info["cluster_probabilities"])
                    if probs:
                        cluster_probability = max(probs.values())
                except (json.JSONDecodeError, ValueError):
                    pass

            logger.info(
                f"[GMM] Artiste {artist_id} ({artist_info['name']}) - cluster: {cluster_label}"
            )

            return ClusterResponse(
                artist_id=artist_id,
                artist_name=artist_info["name"],
                cluster_label=cluster_label,
                cluster_probability=cluster_probability,
                cluster_centroid=None,
            )

        else:
            # L'artiste n'a pas encore de cluster
            # On peut retourner une réponse partielle ou lancer le clustering
            logger.info(f"[GMM] Artiste {artist_id} ({artist_info['name']}) - pas encore clusterisé")

            return ClusterResponse(
                artist_id=artist_id,
                artist_name=artist_info["name"],
                cluster_label=-1,
                cluster_probability=0.0,
                cluster_centroid=None,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GMM] Erreur lors du clustering de l'artiste {artist_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du clustering: {str(e)}",
        )


@router.get(
    "/cluster/{artist_id}",
    response_model=ClusterResponse,
    summary="Récupérer le cluster d'un artiste",
    description="Retourne les informations de cluster pour un artiste donné.",
)
async def get_artist_cluster(
    artist_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> ClusterResponse:
    """Récupère le cluster d'un artiste.

    Args:
        artist_id: Identifiant de l'artiste
        db: Session de base de données

    Returns:
        Informations de clustering de l'artiste

    Raises:
        HTTPException: Si l'artiste n'existe pas ou n'a pas de cluster
    """
    try:
        logger.debug(f"[GMM] Récupération cluster artiste {artist_id}")

        # Vérifier que l'artiste existe
        artist_info = await _get_artist_by_id(artist_id, db)
        if not artist_info:
            raise HTTPException(
                status_code=404,
                detail=f"Artiste avec ID {artist_id} non trouvé",
            )

        # Récupérer les informations de clustering
        embedding_info = await _get_artist_embedding_info(artist_id, db)

        if not embedding_info or embedding_info.get("cluster") is None:
            raise HTTPException(
                status_code=404,
                detail=f"Artiste {artist_info['name']} n'a pas encore de cluster assigné",
            )

        import json

        cluster_probability = 0.0
        if embedding_info.get("cluster_probabilities"):
            try:
                probs = json.loads(embedding_info["cluster_probabilities"])
                if probs:
                    cluster_probability = max(probs.values())
            except (json.JSONDecodeError, ValueError):
                pass

        return ClusterResponse(
            artist_id=artist_id,
            artist_name=artist_info["name"],
            cluster_label=embedding_info["cluster"],
            cluster_probability=cluster_probability,
            cluster_centroid=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GMM] Erreur récupération cluster artiste {artist_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du cluster: {str(e)}",
        )


@router.get(
    "/similar/{artist_id}",
    response_model=SimilarArtistsResponse,
    summary="Récupérer les artistes similaires",
    description="Retourne les artistes similaires basés sur le clustering GMM.",
)
async def get_similar_artists(
    artist_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
) -> SimilarArtistsResponse:
    """Récupère les artistes similaires.

    Retourne les artistes similaires basés sur le clustering GMM
    en utilisant les probabilités de cluster.

    Args:
        artist_id: Identifiant de l'artiste de référence
        limit: Nombre maximum d'artistes similaires à retourner
        db: Session de base de données

    Returns:
        Liste des artistes similaires avec leurs scores de similarité

    Raises:
        HTTPException: Si l'artiste n'existe pas ou n'a pas de cluster
    """
    try:
        logger.info(f"[GMM] Recherche artistes similaires à {artist_id} (limit={limit})")

        # Vérifier que l'artiste existe
        artist_info = await _get_artist_by_id(artist_id, db)
        if not artist_info:
            raise HTTPException(
                status_code=404,
                detail=f"Artiste avec ID {artist_id} non trouvé",
            )

        # Récupérer les informations de clustering
        embedding_info = await _get_artist_embedding_info(artist_id, db)

        if not embedding_info or embedding_info.get("cluster") is None:
            raise HTTPException(
                status_code=404,
                detail=f"Artiste {artist_info['name']} n'a pas encore de cluster assigné",
            )

        embedding_service = ArtistEmbeddingService(db)
        similar_recommendation = await embedding_service.get_similar_artists(
            artist_info["name"], limit=limit
        )

        # Formater la réponse
        similar_artists = []
        for rec in similar_recommendation.similar_artists:
            similar_artists.append({
                "artist_name": rec.get("artist_name", ""),
                "cluster": rec.get("cluster"),
                "similarity_score": rec.get("similarity_score", 0.0),
            })

        cluster_id = embedding_info.get("cluster")

        return SimilarArtistsResponse(
            artist_id=artist_id,
            artist_name=artist_info["name"],
            cluster_id=cluster_id,
            similar_artists=similar_artists,
            total_similar=len(similar_artists),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GMM] Erreur récupération artistes similaires {artist_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des artistes similaires: {str(e)}",
        )


@router.post(
    "/refresh",
    response_model=RefreshClustersResponse,
    summary="Rafraîchir les clusters anciens",
    description="Rafraîchit les clusters qui sont plus anciens que max_age_hours.",
)
async def refresh_stale_clusters(
    max_age_hours: int = 24,
) -> RefreshClustersResponse:
    """Rafraîchit les clusters trop anciens.

    Lance une tâche Celery pour reclusteriser les artistes
    dont le cluster est plus ancien que max_age_hours.

    Args:
        max_age_hours: Âge maximum en heures avant rafraîchissement

    Returns:
        Nombre de clusters à rafraîchir

    Raises:
        HTTPException: Si l'envoi de la tâche échoue
    """
    try:
        logger.info(f"[GMM] Rafraîchissement clusters de plus de {max_age_hours}h")

        # Envoyer la tâche Celery
        task = celery_app.send_task(
            "gmm.refresh_stale_clusters",
            args=[max_age_hours],
            queue="gmm",
            priority=3,
        )

        logger.info(f"[GMM] Tâche de rafraîchissement créée: {task.id}")

        return RefreshClustersResponse(
            refreshed_count=0,  # Sera mis à jour par la tâche Celery
            message=f"Tâche de rafraîchissement créée (ID: {task.id})",
        )

    except Exception as e:
        logger.error(f"[GMM] Erreur lors du rafraîchissement des clusters: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du rafraîchissement: {str(e)}",
        )


@router.get(
    "/status",
    response_model=ClusterStatusResponse,
    summary="Obtenir le statut du clustering",
    description="Retourne les statistiques et le statut du clustering GMM.",
)
async def get_clustering_status(
    db: AsyncSession = Depends(get_async_session),
) -> ClusterStatusResponse:
    """Récupère le statut du clustering.

    Retourne les statistiques globales du clustering GMM :
    nombre d'artistes clusterisés, nombre de clusters, etc.

    Args:
        db: Session de base de données

    Returns:
        Statistiques du clustering
    """
    try:
        logger.debug("[GMM] Récupération statut du clustering")

        embedding_service = ArtistEmbeddingService(db)
        cluster_info = await embedding_service.get_cluster_info()

        if "error" in cluster_info:
            logger.warning(f"[GMM] Erreur récupération statut: {cluster_info['error']}")
            return ClusterStatusResponse(
                last_clustering=None,
                total_artists_clustered=0,
                total_clusters=0,
                model_type="unknown",
            )

        total_artists = cluster_info.get("total_artists", 0)
        clusters = cluster_info.get("clusters", {})
        total_clusters = cluster_info.get("n_clusters", len(clusters))
        gmm_model = cluster_info.get("gmm_model", {})

        # Déterminer le type de modèle
        n_components = gmm_model.get("n_components")
        model_type = "gmm" if n_components else "unknown"

        return ClusterStatusResponse(
            last_clustering=gmm_model.get("trained_at"),
            total_artists_clustered=total_artists,
            total_clusters=total_clusters,
            model_type=model_type,
            n_components=n_components,
            is_fitted=n_components is not None and n_components > 0,
        )

    except Exception as e:
        logger.error(f"[GMM] Erreur récupération statut: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération du statut: {str(e)}",
        )
