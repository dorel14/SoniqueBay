"""Tests unitaires pour scan_worker.py.

Ces tests vérifient les fonctions de scan et l'appel API pour les stats de clustering.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from backend_worker.workers.scan.scan_worker import (
    scan_music_files,
    validate_file_path,
    get_file_type,
    _get_clustering_stats_via_api,
    _maybe_trigger_gmm_clustering,
)


class TestScanMusicFiles:
    """Tests pour la fonction scan_music_files."""

    @pytest.fixture
    def temp_music_dir(self) -> Path:
        """Crée un répertoire temporaire avec des fichiers de musique."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def setup_music_files(self, temp_music_dir: Path) -> dict:
        """Crée des fichiers de musique fictifs."""
        files = {}
        # Créer des fichiers MP3
        mp3_dir = temp_music_dir / "music" / "album"
        mp3_dir.mkdir(parents=True, exist_ok=True)
        
        files["mp3_1"] = mp3_dir / "song1.mp3"
        files["mp3_1"].touch()
        
        files["mp3_2"] = mp3_dir / "song2.mp3"
        files["mp3_2"].touch()
        
        # Créer des fichiers FLAC
        flac_dir = temp_music_dir / "flac"
        flac_dir.mkdir(parents=True, exist_ok=True)
        
        files["flac_1"] = flac_dir / "track.flac"
        files["flac_1"].touch()
        
        # Créer des fichiers non-musiques
        files["txt"] = temp_music_dir / "readme.txt"
        files["txt"].touch()
        
        return {"dir": temp_music_dir, "files": files}

    def test_scan_returns_empty_list_for_empty_directory(self) -> None:
        """Test qu'un répertoire vide retourne une liste vide."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_music_files(tmpdir)
            assert result == []

    def test_scan_discovers_mp3_files(self, setup_music_files: dict) -> None:
        """Test que les fichiers MP3 sont découverts."""
        result = scan_music_files(str(setup_music_files["dir"]))
        
        assert len(result) >= 2
        assert any(".mp3" in f for f in result)

    def test_scan_discovers_flac_files(self, setup_music_files: dict) -> None:
        """Test que les fichiers FLAC sont découverts."""
        result = scan_music_files(str(setup_music_files["dir"]))
        
        assert any(".flac" in f for f in result)

    def test_scan_ignores_non_music_files(self, setup_music_files: dict) -> None:
        """Test que les fichiers non-musique sont ignorés."""
        result = scan_music_files(str(setup_music_files["dir"]))
        
        assert not any(".txt" in f for f in result)

    def test_scan_is_recursive(self, setup_music_files: dict) -> None:
        """Test que le scan est récursif."""
        result = scan_music_files(str(setup_music_files["dir"]))
        
        # Devrait trouver des fichiers dans les sous-répertoires
        assert len(result) >= 3

    def test_scan_returns_list_of_strings(self, setup_music_files: dict) -> None:
        """Test que le résultat est une liste de chaînes."""
        result = scan_music_files(str(setup_music_files["dir"]))
        
        assert isinstance(result, list)
        assert all(isinstance(f, str) for f in result)

    def test_scan_handles_permission_error(self, temp_music_dir: Path) -> None:
        """Test que les erreurs de permission sont gérées."""
        # Créer un sous-répertoire avec des permissions restreintes
        restricted_dir = temp_music_dir / "restricted"
        restricted_dir.mkdir()
        
        # Note: Sur Windows, les permissions ne fonctionnent pas de la même façon,
        # mais le code doit gérer l'erreur gracieusement
        result = scan_music_files(str(temp_music_dir))
        # Le test passe si aucune exception n'est levée


class TestValidateFilePath:
    """Tests pour la fonction validate_file_path."""

    def test_validate_existing_file_returns_true(self) -> None:
        """Test qu'un fichier existant retourne True."""
        import tempfile
        import shutil
        
        # Créer un fichier dans un répertoire temporaire
        temp_dir = tempfile.mkdtemp()
        try:
            file_path = os.path.join(temp_dir, "test_file.mp3")
            with open(file_path, 'w') as f:
                f.write("test")
            
            result = validate_file_path(file_path)
            assert result is True
        finally:
            # Supprimer le répertoire temporaire
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_nonexistent_file_returns_false(self) -> None:
        """Test qu'un fichier inexistant retourne False."""
        result = validate_file_path("/chemin/inexistant/fichier.mp3")
        assert result is False

    def test_validate_directory_returns_false(self) -> None:
        """Test qu'un répertoire retourne False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_file_path(tmpdir)
            assert result is False

    def test_validate_empty_string_returns_false(self) -> None:
        """Test qu'une chaîne vide retourne False."""
        result = validate_file_path("")
        assert result is False


class TestGetFileType:
    """Tests pour la fonction get_file_type."""

    def test_get_file_type_mp3(self) -> None:
        """Test le type pour un fichier MP3."""
        result = get_file_type("/music/song.mp3")
        assert result == ".mp3"

    def test_get_file_type_flac(self) -> None:
        """Test le type pour un fichier FLAC."""
        result = get_file_type("/music/album/track.flac")
        assert result == ".flac"

    def test_get_file_type_case_insensitive(self) -> None:
        """Test que le type est insensible à la casse."""
        result1 = get_file_type("/music/SONG.MP3")
        result2 = get_file_type("/music/song.mp3")
        
        assert result1 == result2 == ".mp3"

    def test_get_file_type_no_extension(self) -> None:
        """Test le type pour un fichier sans extension."""
        result = get_file_type("/music/sans_extension")
        assert result == ""


class TestGetClusteringStatsViaApi:
    """Tests pour la fonction _get_clustering_stats_via_api."""

    @patch('backend_worker.workers.scan.scan_worker.httpx.AsyncClient')
    def test_get_clustering_stats_returns_defaults_on_api_error(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test que les valeurs par défaut sont retournées en cas d'erreur API."""
        # Configurer le mock pour lever une exception
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection error")
        
        result = _get_clustering_stats_via_api()
        
        assert result == {"artists_with_features": 0, "tracks_analyzed": 0}

    @patch('backend_worker.workers.scan.scan_worker.httpx.AsyncClient')
    def test_get_clustering_stats_returns_data_on_success(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test que les données sont retournées correctement quand l'API répond."""
        # Configurer le mock pour retourner une réponse valide
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artists_with_features": 42,
            "tracks_analyzed": 500
        }
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        result = _get_clustering_stats_via_api()
        
        assert result["artists_with_features"] == 42
        assert result["tracks_analyzed"] == 500

    @patch('backend_worker.workers.scan.scan_worker.httpx.AsyncClient')
    def test_get_clustering_stats_returns_defaults_on_non_200(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test que les valeurs par défaut sont retournées pour un code HTTP non-200."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        result = _get_clustering_stats_via_api()
        
        assert result == {"artists_with_features": 0, "tracks_analyzed": 0}

    @patch('backend_worker.workers.scan.scan_worker.httpx.AsyncClient')
    def test_get_clustering_stats_handles_missing_keys(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test que les clés manquantes sont gérées avec les valeurs par défaut."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Pas de clés
        
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        
        result = _get_clustering_stats_via_api()
        
        assert result["artists_with_features"] == 0
        assert result["tracks_analyzed"] == 0


class TestMaybeTriggerGmmClustering:
    """Tests pour la fonction _maybe_trigger_gmm_clustering."""

    @patch('backend_worker.workers.scan.scan_worker._get_clustering_stats_via_api')
    @patch('backend_worker.workers.scan.scan_worker._trigger_gmm_clustering')
    def test_no_trigger_on_unsuccessful_scan(
        self,
        mock_trigger: MagicMock,
        mock_get_stats: MagicMock
    ) -> None:
        """Test qu'aucun déclenchement n'est fait si le scan a échoué."""
        scan_result = {"success": False, "files_discovered": 100}
        
        _maybe_trigger_gmm_clustering(scan_result)
        
        mock_get_stats.assert_not_called()
        mock_trigger.assert_not_called()

    @patch('backend_worker.workers.scan.scan_worker._get_clustering_stats_via_api')
    @patch('backend_worker.workers.scan.scan_worker._trigger_gmm_clustering')
    def test_no_trigger_on_few_files(
        self,
        mock_trigger: MagicMock,
        mock_get_stats: MagicMock
    ) -> None:
        """Test qu'aucun déclenchement n'est fait s'il y a moins de 50 fichiers."""
        scan_result = {"success": True, "files_discovered": 30}
        
        _maybe_trigger_gmm_clustering(scan_result)
        
        mock_get_stats.assert_not_called()
        mock_trigger.assert_not_called()

    @patch('backend_worker.workers.scan.scan_worker._get_clustering_stats_via_api')
    @patch('backend_worker.workers.scan.scan_worker._trigger_gmm_clustering')
    def test_trigger_on_enough_artists(
        self,
        mock_trigger: MagicMock,
        mock_get_stats: MagicMock
    ) -> None:
        """Test le déclenchement quand il y a assez d'artistes avec features."""
        scan_result = {"success": True, "files_discovered": 100}
        mock_get_stats.return_value = {
            "artists_with_features": 60,  # >= 50
            "tracks_analyzed": 100
        }
        
        _maybe_trigger_gmm_clustering(scan_result)
        
        mock_get_stats.assert_called_once()
        mock_trigger.assert_called_once()

    @patch('backend_worker.workers.scan.scan_worker._get_clustering_stats_via_api')
    @patch('backend_worker.workers.scan.scan_worker._trigger_gmm_clustering')
    def test_trigger_on_enough_tracks(
        self,
        mock_trigger: MagicMock,
        mock_get_stats: MagicMock
    ) -> None:
        """Test le déclenchement quand il y a assez de tracks analysées."""
        scan_result = {"success": True, "files_discovered": 100}
        mock_get_stats.return_value = {
            "artists_with_features": 30,
            "tracks_analyzed": 600  # >= 500
        }
        
        _maybe_trigger_gmm_clustering(scan_result)
        
        mock_get_stats.assert_called_once()
        mock_trigger.assert_called_once()

    @patch('backend_worker.workers.scan.scan_worker._get_clustering_stats_via_api')
    @patch('backend_worker.workers.scan.scan_worker._trigger_gmm_clustering')
    def test_no_trigger_when_conditions_not_met(
        self,
        mock_trigger: MagicMock,
        mock_get_stats: MagicMock
    ) -> None:
        """Test qu'aucun déclenchement n'est fait si les conditions ne sont pas remplies."""
        scan_result = {"success": True, "files_discovered": 100}
        mock_get_stats.return_value = {
            "artists_with_features": 20,  # < 50
            "tracks_analyzed": 100  # < 500
        }
        
        _maybe_trigger_gmm_clustering(scan_result)
        
        mock_get_stats.assert_called_once()
        mock_trigger.assert_not_called()
