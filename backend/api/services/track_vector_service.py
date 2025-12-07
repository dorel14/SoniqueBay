"""
Service métier pour la gestion des vecteurs de tracks.
Déplace toute la logique métier depuis track_vectors_api.py ici.
Auteur : Kilo Code
Dépendances : backend.api.models.track_vectors_model, backend.api.schemas.track_vectors_schema
"""
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
# TrackVectorVirtual removed - using PostgreSQL instead
from backend.api.schemas.track_vectors_schema import TrackVectorCreate, TrackVectorResponse


class TrackVectorService:
    def __init__(self, db: Optional[SQLAlchemySession] = None):
        self.session = db

    def create_or_update_vector(self, vector_data: TrackVectorCreate) -> TrackVectorResponse:
        """
        Crée ou met à jour un vecteur pour une track.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            vector_data: Données du vecteur à créer

        Returns:
            Le vecteur créé ou mis à jour

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def get_vector(self, track_id: int) -> TrackVectorResponse:
        """
        Récupère le vecteur d'une track.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def delete_vector(self, track_id: int):
        """
        Supprime le vecteur d'une track.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            track_id: ID de la track

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def list_vectors(self, skip: int = 0, limit: int = 100) -> List[TrackVectorResponse]:
        """
        Liste les vecteurs de tracks.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            skip: Nombre d'éléments à sauter
            limit: Nombre maximum d'éléments à retourner

        Returns:
            Liste des vecteurs

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def search_similar_vectors(self, query_vector, limit: int = 10):
        """
        Recherche les vecteurs similaires à un vecteur de requête.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            query_vector: Vecteur de requête avec track_id et embedding
            limit: Nombre maximum de résultats

        Returns:
            Liste des vecteurs similaires avec leur distance

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def create_vectors_batch(self, vectors):
        """
        Crée ou met à jour plusieurs vecteurs en batch.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            vectors: Liste des vecteurs à créer

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def get_vector_virtual(self, track_id: int):
        """
        Récupère un vecteur par track_id.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")

    def delete_vector_virtual(self, track_id: int):
        """
        Supprime un vecteur par track_id.

        DEPRECATED: Vectorisation gérée par les workers Celery.

        Args:
            track_id: ID de la track

        Raises:
            NotImplementedError: Méthode dépréciée
        """
        raise NotImplementedError("Vectorisation gérée par les workers Celery")