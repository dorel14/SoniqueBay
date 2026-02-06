# -*- coding: utf-8 -*-
"""
Types GraphQL Strawberry pour les embeddings vectoriels des pistes.

Rôle:
    Définit les types GraphQL pour TrackEmbeddings, incluant le type
    de sortie, les inputs pour mutations et la recherche vectorielle.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List

import strawberry

from backend.api.utils.logging import logger


@strawberry.type
class TrackEmbeddingsType:
    """
    Type GraphQL pour les embeddings vectoriels d'une piste.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        embedding_type: Type d'embedding (semantic, audio, text, etc.)
        embedding_source: Source de vectorisation (ollama, huggingface, etc.)
        embedding_model: Modèle utilisé (nomic-embed-text, all-MiniLM-L6-v2, etc.)
        created_at: Date de création de l'embedding
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    embedding_type: str
    embedding_source: Optional[str] = None
    embedding_model: Optional[str] = None
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None

    # Le vecteur n'est pas exposé directement pour des raisons de performance
    # Utiliser les queries de similarité à la place


@strawberry.type
class SimilarTrackResult:
    """
    Type GraphQL pour un résultat de recherche par similarité.

    Attributes:
        embedding: L'embedding trouvé
        distance: Distance euclidienne (plus petit = plus similaire)
        similarity_score: Score de similarité (0-1, plus grand = plus similaire)
    """

    embedding: TrackEmbeddingsType
    distance: float
    similarity_score: float


@strawberry.input
class TrackEmbeddingsInput:
    """
    Input GraphQL pour créer un embedding.

    Attributes:
        track_id: ID de la piste (obligatoire)
        vector: Vecteur d'embedding (512 dimensions)
        embedding_type: Type d'embedding (défaut: 'semantic')
        embedding_source: Source de vectorisation
        embedding_model: Modèle utilisé
    """

    track_id: int
    vector: List[float]
    embedding_type: str = "semantic"
    embedding_source: Optional[str] = None
    embedding_model: Optional[str] = None


@strawberry.input
class TrackEmbeddingsUpdateInput:
    """
    Input GraphQL pour mettre à jour un embedding.

    Attributes:
        track_id: ID de la piste (obligatoire)
        embedding_type: Type d'embedding à mettre à jour (obligatoire)
        vector: Nouveau vecteur (512 dimensions)
        embedding_source: Nouvelle source
        embedding_model: Nouveau modèle
    """

    track_id: int
    embedding_type: str
    vector: Optional[List[float]] = None
    embedding_source: Optional[str] = None
    embedding_model: Optional[str] = None


@strawberry.input
class TrackEmbeddingsSearchInput:
    """
    Input GraphQL pour la recherche vectorielle.

    Attributes:
        query_vector: Vecteur de recherche (512 dimensions)
        embedding_type: Type d'embedding à rechercher (défaut: 'semantic')
        limit: Nombre maximum de résultats
        min_similarity: Similarité minimale (0-1)
        exclude_track_ids: IDs de pistes à exclure
    """

    query_vector: List[float]
    embedding_type: str = "semantic"
    limit: int = 10
    min_similarity: Optional[float] = None
    exclude_track_ids: Optional[List[int]] = None


@strawberry.input
class TrackEmbeddingsSimilarityInput:
    """
    Input GraphQL pour trouver des pistes similaires à une piste de référence.

    Attributes:
        track_id: ID de la piste de référence
        embedding_type: Type d'embedding à utiliser (défaut: 'semantic')
        limit: Nombre maximum de résultats
        exclude_self: Exclure la piste de référence des résultats
    """

    track_id: int
    embedding_type: str = "semantic"
    limit: int = 10
    exclude_self: bool = True
