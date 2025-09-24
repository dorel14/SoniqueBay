from __future__ import annotations
from sqlalchemy import Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import TypeDecorator
import json
from backend.utils.database import Base
from backend.utils.sqlite_vec_init import get_vec_connection

class JSONList(TypeDecorator):
    impl = Text
    cache_ok = True  # nécessaire pour éviter les warnings SQLAlchemy

    @property
    def python_type(self):
        return list  # ✅ <- ceci évite l'erreur de Strawchemy

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        return json.loads(value)


# Ancien modèle pour compatibilité (sera supprimé)
class TrackVector(Base):
    __tablename__ = 'track_vectors'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[int] = mapped_column(Integer, ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False)
    vector_data: Mapped[list] = mapped_column(MutableList.as_mutable(JSONList))  # Stocke sous forme de liste JSON
    # Relations
    # track: Mapped["Track"] = relationship("Track", back_populates="vectors")  # type: ignore # noqa: F821

    __table_args__ = (
        # Index pour les lookups rapides par track_id
        Index('idx_track_vectors_track_id', 'track_id'),
    )

    def __repr__(self):
        return f"<TrackVector(track_id='{self.track_id}', vector_data='{self.vector_data[:20]}...')>"  # Display first 20 characters of vector data


# Nouveau modèle pour sqlite-vec (table virtuelle)
class TrackVectorVirtual(Base):
    """
    Modèle pour la table virtuelle sqlite-vec track_vectors.
    Utilise vec0 pour le stockage optimisé des vecteurs.
    """
    __tablename__ = 'track_vectors_virtual'

    track_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    embedding: Mapped[list] = mapped_column(MutableList.as_mutable(JSONList))  # Stockage JSON pour compatibilité

    def __repr__(self):
        return f"<TrackVectorVirtual(track_id='{self.track_id}', embedding_dim={len(self.embedding) if self.embedding else 0})>"

    @classmethod
    def insert_vector(cls, track_id: int, embedding: list):
        """
        Insère un vecteur dans la table virtuelle sqlite-vec.
        """
        conn = get_vec_connection()
        cursor = conn.cursor()

        # Pour sqlite-vec, on utilise la syntaxe FTS avec les valeurs JSON
        embedding_json = json.dumps(embedding)

        sql = """
            INSERT OR REPLACE INTO track_vectors (track_id, embedding)
            VALUES (?, ?)
        """

        cursor.execute(sql, (track_id, embedding_json))
        conn.commit()

    @classmethod
    def search_similar(cls, query_embedding: list, limit: int = 10):
        """
        Recherche les vecteurs similaires en utilisant sqlite-vec.
        """
        conn = get_vec_connection()
        cursor = conn.cursor()

        # Utiliser la fonction vec_distance_cosine de sqlite-vec
        query_json = json.dumps(query_embedding)

        sql = """
            SELECT track_id, vec_distance_cosine(embedding, ?) as distance
            FROM track_vectors
            ORDER BY distance
            LIMIT ?
        """

        cursor.execute(sql, (query_json, limit))
        rows = cursor.fetchall()

        return [{'track_id': row[0], 'distance': float(row[1])} for row in rows]

    @classmethod
    def get_vector(cls, track_id: int):
        """
        Récupère un vecteur par track_id.
        """
        conn = get_vec_connection()
        cursor = conn.cursor()

        sql = """
            SELECT track_id, embedding
            FROM track_vectors
            WHERE track_id = ?
        """

        cursor.execute(sql, (track_id,))
        row = cursor.fetchone()

        if row:
            return {
                'track_id': row[0],
                'embedding': json.loads(row[1])
            }
        return None

    @classmethod
    def delete_vector(cls, track_id: int):
        """
        Supprime un vecteur par track_id.
        """
        conn = get_vec_connection()
        cursor = conn.cursor()

        sql = """
            DELETE FROM track_vectors
            WHERE track_id = ?
        """

        cursor.execute(sql, (track_id,))
        conn.commit()