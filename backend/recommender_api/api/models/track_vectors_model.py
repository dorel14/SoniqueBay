from __future__ import annotations
import sqlite3
from sqlalchemy import Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import TypeDecorator
import json
from backend.recommender_api.utils.database import Base
from backend.recommender_api.utils.sqlite_vec_init import get_vec_connection
import logging

logger = logging.getLogger(__name__)

TABLE_NAME = "track_vectors"
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


class VecTableMixin:
    TABLE_NAME = "track_vectors"

    @classmethod
    def execute(cls, sql, params=(), commit=False):
        conn = get_vec_connection()
        result = conn.execute(sql, params)
        if commit:
            conn.commit()
        return result


# Nouveau modèle pour sqlite-vec (table virtuelle)
class TrackVectorVirtual(VecTableMixin, Base):
    """
    Modèle pour la table virtuelle sqlite-vec track_vectors.
    Utilise vec0 pour le stockage optimisé des vecteurs.
    """
    __tablename__ = 'track_vectors'
    __table_args__ = {'extend_existing': True}

    track_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    embedding: Mapped[list] = mapped_column(MutableList.as_mutable(JSONList))  # Stockage JSON pour compatibilité

    def __repr__(self):
        return f"<TrackVectorVirtual(track_id='{self.track_id}', embedding_dim={len(self.embedding) if self.embedding else 0})>"

    @classmethod
    def insert_vector(cls, track_id: int, embedding: list):
        """
        Insère un vecteur dans la table virtuelle sqlite-vec.
        """
        assert isinstance(embedding, list), "embedding must be a list"
        if len(embedding) != 512:
            raise ValueError(f"embedding must have exactly 512 dimensions, got {len(embedding)}")
        # Pour sqlite-vec, on utilise la syntaxe FTS avec les valeurs JSON
        embedding_json = json.dumps(embedding)

        sql = f"""
            INSERT OR REPLACE INTO {cls.TABLE_NAME} (track_id, embedding)
            VALUES (?, ?)
        """

        try:
            cls.execute(sql, (track_id, embedding_json), commit=True)
        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de l'insertion du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec de l'insertion du vecteur: {str(e)}") from e
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'insertion du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec inattendu de l'insertion du vecteur: {str(e)}") from e

    @classmethod
    def search_similar(cls, query_embedding: list, limit: int = 10):
        """
        Recherche les vecteurs similaires en utilisant sqlite-vec.
        """
        # Utiliser la fonction vec_distance_cosine de sqlite-vec
        query_json = json.dumps(query_embedding)

        sql = """
            SELECT track_id, vec_distance_cosine(embedding, ?) as distance
            FROM track_vectors
            ORDER BY distance
            LIMIT ?
        """

        try:
            rows = cls.execute(sql, (query_json, limit)).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de la recherche de vecteurs similaires: {e}")
            raise RuntimeError(f"Échec de la recherche de vecteurs similaires: {str(e)}") from e
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la recherche de vecteurs similaires: {e}")
            raise RuntimeError(f"Échec inattendu de la recherche: {str(e)}") from e

        return [{'track_id': row[0], 'distance': float(row[1])} for row in rows]

    @classmethod
    def search_batch(cls, query_embeddings: list, limit: int = 10):
        """
        Recherche les vecteurs similaires pour plusieurs embeddings de requête à la fois.
        Utile pour du "bulk recommendation".
        Retourne une liste de listes de résultats, une par embedding.
        """
        results = []
        for query_embedding in query_embeddings:
            try:
                query_json = json.dumps(query_embedding)
                sql = """
                    SELECT track_id, vec_distance_cosine(embedding, ?) as distance
                    FROM track_vectors
                    ORDER BY distance
                    LIMIT ?
                """
                rows = cls.execute(sql, (query_json, limit)).fetchall()
                batch_results = [{'track_id': row[0], 'distance': float(row[1])} for row in rows]
                results.append(batch_results)
            except Exception as e:
                logger.error(f"Error in search_batch for embedding {query_embedding[:5]}...: {e}")
                results.append([])  # Retourner une liste vide en cas d'erreur pour cet embedding
        return results

    @classmethod
    def get_vector(cls, track_id: int):
        """
        Récupère un vecteur par track_id.
        """
        sql = """
            SELECT track_id, embedding
            FROM track_vectors
            WHERE track_id = ?
        """

        try:
            row = cls.execute(sql, (track_id,)).fetchone()
        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de la récupération du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec de la récupération du vecteur: {str(e)}") from e
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la récupération du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec inattendu de la récupération: {str(e)}") from e

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
        sql = """
            DELETE FROM track_vectors
            WHERE track_id = ?
        """

        try:
            cls.execute(sql, (track_id,), commit=True)
        except sqlite3.Error as e:
            logger.error(f"Erreur SQLite lors de la suppression du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec de la suppression du vecteur: {str(e)}") from e
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la suppression du vecteur pour track_id={track_id}: {e}")
            raise RuntimeError(f"Échec inattendu de la suppression: {str(e)}") from e