"""
Tests pour sqlite-vec dans SoniqueBay.
"""
from unittest.mock import patch, MagicMock
import json
import sqlite3

from backend.recommender_api.api.models.track_vectors_model import TrackVectorVirtual
from backend.recommender_api.api.schemas.track_vectors_schema import TrackVectorIn, TrackVectorOut
from backend.recommender_api.utils.sqlite_vec_init import initialize_sqlite_vec


def test_initialize_sqlite_vec_system_path_success():
    """Test l'initialisation réussie de sqlite-vec depuis le chemin système."""
    with patch('backend.recommender_api.utils.sqlite_vec_init.get_vec_connection') as mock_get_conn, \
         patch('backend.recommender_api.utils.sqlite_vec_init.get_database_url', return_value='sqlite:///test.db'):
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock des fonctions sqlite-vec
        mock_cursor.execute.side_effect = [
            None,  # SELECT sqlite_version()
            None,  # DROP TABLE IF EXISTS
            None   # CREATE VIRTUAL TABLE
        ]
        mock_cursor.fetchone.return_value = ("3.40.0",)

        result = initialize_sqlite_vec()

        assert result is True
        assert mock_cursor.execute.call_count == 3
        
        # Vérifier les appels spécifiques
        calls = mock_cursor.execute.call_args_list
        assert "DROP TABLE IF EXISTS track_vectors" in str(calls[1])
        assert "CREATE VIRTUAL TABLE track_vectors" in str(calls[2])


def test_initialize_sqlite_vec_pip_success():
    """Test l'initialisation réussie de sqlite-vec depuis le package pip."""
    with patch('backend.recommender_api.utils.sqlite_vec_init.get_vec_connection') as mock_get_conn, \
         patch('backend.recommender_api.utils.sqlite_vec_init.get_database_url', return_value='sqlite:///test.db'), \
         patch('sqlite3.connect'):
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn
        
        # Mock l'échec du chargement système pour tester le fallback pip
        def mock_load_extension(path):
            if '/usr/local/lib' in str(path):
                raise sqlite3.OperationalError("not found")
            return None
            
        mock_conn.load_extension = MagicMock(side_effect=mock_load_extension)

        # Mock des fonctions sqlite-vec
        mock_cursor.execute.side_effect = [
            None,  # SELECT sqlite_version()
            None,  # DROP TABLE IF EXISTS
            None   # CREATE VIRTUAL TABLE
        ]
        mock_cursor.fetchone.return_value = ("3.40.0",)

        result = initialize_sqlite_vec()

        assert result is True
        assert mock_cursor.execute.call_count == 3
        
        # Vérifier les appels spécifiques
        calls = mock_cursor.execute.call_args_list
        assert "DROP TABLE IF EXISTS track_vectors" in str(calls[1])
        assert "CREATE VIRTUAL TABLE track_vectors" in str(calls[2])


def test_initialize_sqlite_vec_failure():
    """Test l'initialisation quand sqlite-vec n'est pas disponible."""
    with patch('backend.recommender_api.utils.sqlite_vec_init.get_vec_connection') as mock_get_conn, \
         patch('backend.recommender_api.utils.sqlite_vec_init.get_database_url', return_value='sqlite:///test.db'), \
         patch('sqlite3.connect'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock l'échec du chargement de l'extension
        def mock_load_extension(path):
            raise sqlite3.OperationalError("not found")
            
        mock_conn.load_extension = MagicMock(side_effect=mock_load_extension)
        
        # Mock version SQLite
        mock_cursor.execute.side_effect = [None]  # Juste pour SELECT sqlite_version()
        mock_cursor.fetchone.return_value = ("3.40.0",)

        result = initialize_sqlite_vec()

        assert result is False


def test_track_vector_virtual_insert():
    """Test l'insertion d'un vecteur dans la table virtuelle."""
    with patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        test_embedding = [0.1] * 512  # 512 dimensions
        test_track_id = 1

        TrackVectorVirtual.insert_vector(
            track_id=test_track_id,
            embedding=test_embedding
        )

        # Vérifier que execute a été appelé
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args

        # Vérifier le SQL et les paramètres
        sql_text = call_args[0][0]
        assert "INSERT OR REPLACE INTO track_vectors" in sql_text
        assert call_args[0][1] == (test_track_id, json.dumps(test_embedding))


def test_track_vector_virtual_search_similar():
    """Test la recherche de vecteurs similaires."""
    with patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_get_conn.return_value = mock_conn

        # Mock des résultats de recherche
        mock_row1 = (1, 0.1)
        mock_row2 = (2, 0.2)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_conn.execute.return_value = mock_result

        query_embedding = [0.1, 0.2, 0.3]
        results = TrackVectorVirtual.search_similar(
            query_embedding=query_embedding,
            limit=5
        )

        assert len(results) == 2
        assert results[0]['track_id'] == 1
        assert results[0]['distance'] == 0.1
        assert results[1]['track_id'] == 2
        assert results[1]['distance'] == 0.2

        # Vérifier que execute a été appelé avec les bons paramètres
        call_args = mock_conn.execute.call_args
        sql_text = call_args[0][0]
        assert "vec_distance_cosine" in sql_text
        assert "ORDER BY distance" in sql_text
        assert call_args[0][1] == (json.dumps(query_embedding), 5)


def test_track_vector_virtual_get_vector():
    """Test la récupération d'un vecteur."""
    with patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_get_conn.return_value = mock_conn

        test_embedding = [0.1, 0.2, 0.3]
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1, json.dumps(test_embedding))
        mock_conn.execute.return_value = mock_result

        result = TrackVectorVirtual.get_vector(track_id=1)

        assert result is not None
        assert result['track_id'] == 1
        assert result['embedding'] == test_embedding


def test_track_vector_virtual_get_vector_not_found():
    """Test la récupération d'un vecteur inexistant."""
    with patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_get_conn.return_value = mock_conn

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        result = TrackVectorVirtual.get_vector(track_id=999)

        assert result is None


def test_track_vector_virtual_delete_vector():
    """Test la suppression d'un vecteur."""
    with patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_get_conn.return_value = mock_conn

        TrackVectorVirtual.delete_vector(track_id=1)

        # Vérifier que execute a été appelé
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args

        sql_text = call_args[0][0]
        assert "DELETE FROM track_vectors" in sql_text
        assert call_args[0][1] == (1,)


def test_track_vector_in_schema():
    """Test le schéma Pydantic TrackVectorIn."""
    vector_data = TrackVectorIn(track_id=1, embedding=[0.1, 0.2, 0.3])

    assert vector_data.track_id == 1
    assert vector_data.embedding == [0.1, 0.2, 0.3]


def test_track_vector_out_schema():
    """Test le schéma Pydantic TrackVectorOut."""
    result = TrackVectorOut(track_id=2, distance=0.15)

    assert result.track_id == 2
    assert result.distance == 0.15