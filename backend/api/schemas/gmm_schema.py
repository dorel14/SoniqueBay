# -*- coding: UTF-8 -*-
"""
Schémas Pydantic pour les réponses du clustering GMM des artistes.

Ce module contient les modèles Pydantic utilisés par le router GMM
pour valider et serializer les réponses API.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional

from pydantic import BaseModel, Field


class ClusterResponse(BaseModel):
    """Réponse du clustering pour un artiste."""

    artist_id: int = Field(..., description="Identifiant de l'artiste")
    artist_name: str = Field(..., description="Nom de l'artiste")
    cluster_label: int = Field(..., description="Label du cluster assigné")
    cluster_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Probabilité d'appartenance au cluster"
    )
    cluster_centroid: Optional[list[float]] = Field(
        None, description="Centroïde du cluster si disponible"
    )


class SimilarArtistsResponse(BaseModel):
    """Réponse pour les artistes similaires."""

    artist_id: int = Field(..., description="Identifiant de l'artiste de référence")
    artist_name: str = Field(..., description="Nom de l'artiste de référence")
    cluster_id: Optional[int] = Field(
        None, description="Cluster de l'artiste de référence"
    )
    similar_artists: list[dict] = Field(
        default_factory=list, description="Liste des artistes similaires"
    )
    total_similar: int = Field(0, description="Nombre d'artistes similaires")


class ClusterStatusResponse(BaseModel):
    """Réponse du statut du clustering."""

    last_clustering: Optional[str] = Field(
        None, description="Date du dernier clustering au format ISO"
    )
    total_artists_clustered: int = Field(0, description="Nombre d'artistes clusterisés")
    total_clusters: int = Field(0, description="Nombre total de clusters")
    model_type: str = Field("unknown", description="Type de modèle (gmm ou kmeans_fallback)")
    n_components: Optional[int] = Field(
        None, description="Nombre de composants du modèle GMM"
    )
    is_fitted: bool = Field(False, description="Si un modèle est entraîné")


class ClusteringTaskResponse(BaseModel):
    """Réponse lors du déclenchement d'une tâche de clustering."""

    task_id: str = Field(default='...', description="Identifiant de la tâche Celery")
    message: str = Field('...', description="Message de confirmation")
    status: str = Field('...', description="Statut de la tâche")


class RefreshClustersResponse(BaseModel):
    """Réponse du rafraîchissement des clusters."""

    refreshed_count: int = Field(0, description="Nombre de clusters rafraîchis")
    message: str = Field(..., description="Message de confirmation")
