"""
Service métier pour la gestion des vecteurs de tracks.
Déplace toute la logique métier depuis track_vectors_api.py ici.
Auteur : Kilo Code
Dépendances : backend.api.models.track_vectors_model, backend.api.schemas.track_vectors_schema
"""
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.api.models.track_vectors_model import TrackVector, TrackVectorVirtual
from backend.api.schemas.track_vectors_schema import TrackVectorCreate, TrackVectorResponse, TrackVectorIn, TrackVectorOut
from backend.utils.logging import logger


class TrackVectorService:
    def __init__(self, db: Optional[SQLAlchemySession] = None):
        self.session = db

    def create_or_update_vector(self, vector_data: TrackVectorCreate) -> TrackVectorResponse:
        """
        Crée ou met à jour un vecteur pour une track.

        Args:
            vector_data: Données du vecteur à créer

        Returns:
            Le vecteur créé ou mis à jour

        Raises:
            ValueError: Si la track n'existe pas
        """
        # Vérifier que la track existe
        from backend.api.models.tracks_model import Track
        track = self.session.query(Track).filter(Track.id == vector_data.track_id).first()
        if not track:
            raise ValueError(f"Track with id {vector_data.track_id} not found")

        # Vérifier si un vecteur existe déjà pour cette track
        existing_vector = self.session.query(TrackVector).filter(
            TrackVector.track_id == vector_data.track_id
        ).first()

        if existing_vector:
            # Mettre à jour le vecteur existant
            existing_vector.vector_data = vector_data.vector_data
            self.session.commit()
            self.session.refresh(existing_vector)
            logger.info(f"Vecteur mis à jour pour track {vector_data.track_id}")
            return TrackVectorResponse(
                id=existing_vector.id,
                track_id=existing_vector.track_id,
                vector_data=existing_vector.vector_data
            )
        else:
            # Créer un nouveau vecteur
            new_vector = TrackVector(
                track_id=vector_data.track_id,
                vector_data=vector_data.vector_data
            )
            self.session.add(new_vector)
            self.session.commit()
            self.session.refresh(new_vector)
            logger.info(f"Nouveau vecteur créé pour track {vector_data.track_id}")
            return TrackVectorResponse(
                id=new_vector.id,
                track_id=new_vector.track_id,
                vector_data=new_vector.vector_data
            )

    def get_vector(self, track_id: int) -> TrackVectorResponse:
        """
        Récupère le vecteur d'une track.

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        vector = self.session.query(TrackVector).filter(TrackVector.track_id == track_id).first()
        if not vector:
            raise ValueError(f"Vector not found for track {track_id}")

        return TrackVectorResponse(
            id=vector.id,
            track_id=vector.track_id,
            vector_data=vector.vector_data
        )

    def delete_vector(self, track_id: int):
        """
        Supprime le vecteur d'une track.

        Args:
            track_id: ID de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        vector = self.session.query(TrackVector).filter(TrackVector.track_id == track_id).first()
        if not vector:
            raise ValueError(f"Vector not found for track {track_id}")

        self.session.delete(vector)
        self.session.commit()
        logger.info(f"Vecteur supprimé pour track {track_id}")

    def list_vectors(self, skip: int = 0, limit: int = 100) -> List[TrackVectorResponse]:
        """
        Liste les vecteurs de tracks avec pagination.

        Args:
            skip: Nombre d'éléments à sauter
            limit: Nombre maximum d'éléments à retourner

        Returns:
            Liste des vecteurs
        """
        vectors = self.session.query(TrackVector).offset(skip).limit(limit).all()

        return [
            TrackVectorResponse(
                id=vector.id,
                track_id=vector.track_id,
                vector_data=vector.vector_data
            )
            for vector in vectors
        ]

    def search_similar_vectors(self, query_vector: TrackVectorIn, limit: int = 10) -> List[TrackVectorOut]:
        """
        Recherche les vecteurs similaires à un vecteur de requête.

        Args:
            query_vector: Vecteur de requête avec track_id et embedding
            limit: Nombre maximum de résultats

        Returns:
            Liste des vecteurs similaires avec leur distance
        """
        results = TrackVectorVirtual.search_similar(
            query_embedding=query_vector.embedding,
            limit=limit
        )

        return [TrackVectorOut(track_id=result['track_id'], distance=result['distance']) for result in results]

    def create_vectors_batch(self, vectors: List[TrackVectorIn]):
        """
        Crée ou met à jour plusieurs vecteurs en batch.

        Args:
            vectors: Liste des vecteurs à créer
        """
        for vector in vectors:
            TrackVectorVirtual.insert_vector(
                track_id=vector.track_id,
                embedding=vector.embedding
            )

        logger.info(f"Batch créé avec {len(vectors)} vecteurs")

    def get_vector_virtual(self, track_id: int):
        """
        Récupère un vecteur par track_id (version sqlite-vec).

        Args:
            track_id: ID de la track

        Returns:
            Le vecteur de la track

        Raises:
            ValueError: Si le vecteur n'existe pas
        """
        result = TrackVectorVirtual.get_vector(track_id=track_id)
        if not result:
            raise ValueError(f"Vector not found for track {track_id}")

        return result

    def delete_vector_virtual(self, track_id: int):
        """
        Supprime un vecteur par track_id (version sqlite-vec).

        Args:
            track_id: ID de la track
        """
        TrackVectorVirtual.delete_vector(track_id=track_id)
        logger.info(f"Vecteur supprimé pour track {track_id}")