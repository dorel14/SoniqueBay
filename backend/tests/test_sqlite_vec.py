"""
Tests pour sqlite-vec dans SoniqueBay.
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from backend.api.models.track_vectors_model import TrackVectorVirtual
from backend.api.schemas.track_vectors_schema import TrackVectorIn, TrackVectorOut
from backend.utils.sqlite_vec_init import initialize_sqlite_vec


@pytest.mark.asyncio
async def test_initialize_sqlite_vec_success():
    """Test l'initialisation réussie de sqlite-vec."""
    with patch('backend.utils.sqlite_vec_init.get_vec_connection') as mock_get_conn, \
         patch('backend.utils.sqlite_vec_init.get_database_url', return_value='sqlite:///test.db'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock des fonctions sqlite-vec
        mock_cursor.execute.side_effect = [
            None,  # SELECT sqlite_version()
            None,  # load_extension
            None   # CREATE VIRTUAL TABLE
        ]
        mock_cursor.fetchone.return_value = ("3.40.0",)

        result = initialize_sqlite_vec()

        assert result is True
        assert mock_cursor.execute.call_count >= 2


@pytest.mark.asyncio
async def test_initialize_sqlite_vec_no_vec():
    """Test l'initialisation quand sqlite-vec n'est pas disponible."""
    with patch('backend.utils.sqlite_vec_init.get_vec_connection') as mock_get_conn, \
         patch('backend.utils.sqlite_vec_init.get_database_url', return_value='sqlite:///test.db'):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock version SQLite OK mais CREATE VIRTUAL TABLE échoue
        mock_cursor.execute.side_effect = [
            None,  # SELECT sqlite_version()
            Exception("CREATE VIRTUAL TABLE failed")  # CREATE échoue
        ]
        mock_cursor.fetchone.return_value = ("3.40.0",)

        result = initialize_sqlite_vec()

        assert result is False


@pytest.mark.asyncio
async def test_track_vector_virtual_insert():
    """Test l'insertion d'un vecteur dans la table virtuelle."""
    with patch('backend.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        test_embedding = [0.1, 0.2, 0.3, 0.4]
        test_track_id = 1

        TrackVectorVirtual.insert_vector(
            track_id=test_track_id,
            embedding=test_embedding
        )

        # Vérifier que execute a été appelé
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args

        # Vérifier le SQL et les paramètres
        sql_text = call_args[0][0]
        assert "INSERT OR REPLACE INTO track_vectors" in sql_text
        assert call_args[0][1] == (test_track_id, json.dumps(test_embedding))


@pytest.mark.asyncio
async def test_track_vector_virtual_search_similar():
    """Test la recherche de vecteurs similaires."""
    with patch('backend.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Mock des résultats de recherche
        mock_row1 = (1, 0.1)
        mock_row2 = (2, 0.2)
        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]

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
        call_args = mock_cursor.execute.call_args
        sql_text = call_args[0][0]
        assert "vec_distance_cosine" in sql_text
        assert "ORDER BY distance" in sql_text
        assert call_args[0][1] == (json.dumps(query_embedding), 5)


@pytest.mark.asyncio
async def test_track_vector_virtual_get_vector():
    """Test la récupération d'un vecteur."""
    with patch('backend.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        test_embedding = [0.1, 0.2, 0.3]
        mock_cursor.fetchone.return_value = (1, json.dumps(test_embedding))

        result = TrackVectorVirtual.get_vector(track_id=1)

        assert result is not None
        assert result['track_id'] == 1
        assert result['embedding'] == test_embedding


@pytest.mark.asyncio
async def test_track_vector_virtual_get_vector_not_found():
    """Test la récupération d'un vecteur inexistant."""
    with patch('backend.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.return_value = None

        result = TrackVectorVirtual.get_vector(track_id=999)

        assert result is None


@pytest.mark.asyncio
async def test_track_vector_virtual_delete_vector():
    """Test la suppression d'un vecteur."""
    with patch('backend.api.models.track_vectors_model.get_vec_connection') as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        TrackVectorVirtual.delete_vector(track_id=1)

        # Vérifier que execute a été appelé
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args

        sql_text = call_args[0][0]
        assert "DELETE FROM track_vectors" in sql_text
        assert call_args[0][1] == (1,)


@pytest.mark.asyncio
async def test_track_vector_in_schema():
    """Test le schéma Pydantic TrackVectorIn."""
    vector_data = TrackVectorIn(track_id=1, embedding=[0.1, 0.2, 0.3])

    assert vector_data.track_id == 1
    assert vector_data.embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_track_vector_out_schema():
    """Test le schéma Pydantic TrackVectorOut."""
    result = TrackVectorOut(track_id=2, distance=0.15)

    assert result.track_id == 2
    assert result.distance == 0.15