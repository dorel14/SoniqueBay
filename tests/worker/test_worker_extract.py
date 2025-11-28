"""
Tests pour Worker Extract - Extraction des métadonnées des fichiers individuels
"""

import pytest
from backend_worker.background_tasks.worker_extract import (
    extract_file_metadata_task,
    extract_batch_metadata_task,
    validate_extraction_quality_task
)


class TestWorkerExtract:
    """Tests pour le worker_extract."""

    @pytest.mark.asyncio
    async def test_extract_file_metadata_task_success(self):
        """Test extraction réussie des métadonnées d'un fichier."""
        file_path = "/valid/test_song.mp3"
        scan_config = {
            "base_directory": "/music",
            "template": "{artist}/{album}/{title}"
        }

        result = extract_file_metadata_task(file_path, scan_config, "normal")

        assert result["path"] == file_path
        assert result["title"] == "test_song"
        assert result["artist"] == "Test Artist"
        assert result["album"] == "Test Album"
        assert result["extraction_success"] is True
        assert "processed_at" in result
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_extract_file_metadata_task_invalid_path(self):
        """Test extraction avec chemin invalide."""
        file_path = "/invalid/path.mp3"
        scan_config = {"base_directory": "/music"}

        result = extract_file_metadata_task(file_path, scan_config, "normal")

        assert "error" in result
        assert result["file_path"] == file_path

    @pytest.mark.asyncio
    async def test_extract_batch_metadata_task_success(self):
        """Test extraction par lot réussie."""
        file_paths = ["/valid/song1.mp3", "/valid/song2.mp3", "/valid/song3.mp3"]
        scan_config = {
            "base_directory": "/music",
            "template": "{artist}/{album}/{title}"
        }

        result = extract_batch_metadata_task(file_paths, scan_config, "normal")

        assert result["total_files"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert len(result["results"]) == 3
        assert result["priority"] == "normal"

        # Vérifier que chaque résultat contient les métadonnées attendues
        for res in result["results"]:
            assert res["extraction_success"] is True
            assert "quality_score" in res

    @pytest.mark.asyncio
    async def test_extract_batch_metadata_task_empty_list(self):
        """Test extraction par lot avec liste vide."""
        result = extract_batch_metadata_task([], {}, "normal")

        assert "error" in result
        assert result["error"] == "Aucune fichier à traiter"

    @pytest.mark.asyncio
    async def test_extract_batch_metadata_task_mixed_results(self):
        """Test extraction par lot avec résultats mixtes."""
        file_paths = ["/valid/song1.mp3", "/invalid/song2.mp3", "/valid/song3.mp3"]
        scan_config = {"base_directory": "/music"}

        result = extract_batch_metadata_task(file_paths, scan_config, "high")

        assert result["total_files"] == 3
        assert result["successful"] == 2  # 2 fichiers valides
        assert result["failed"] == 1     # 1 fichier invalide
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_validate_extraction_quality_task_success(self):
        """Test validation de la qualité des extractions."""
        metadata_list = [
            {
                "path": "/music/song1.mp3",
                "title": "Song 1",
                "artist": "Artist 1",
                "album": "Album 1",
                "duration": 180.0,
                "bitrate": 320,
                "file_type": "audio/mpeg",
                "genre": "Rock",
                "year": "2023",
                "track_number": 1
            },
            {
                "path": "/music/song2.mp3",
                "title": "Song 2",
                "artist": "Artist 2",
                "album": "Album 2",
                "duration": 200.0,
                "bitrate": 256,
                "file_type": "audio/mpeg"
            }
        ]

        result = validate_extraction_quality_task(metadata_list, 0.7)

        assert result["total_validated"] == 2
        assert "average_quality" in result
        assert "high_quality_count" in result
        assert "low_quality_count" in result
        assert result["quality_threshold"] == 0.7
        assert result["validation_passed"] is True
        assert len(result["details"]) == 2

        # Vérifier les détails de qualité
        for detail in result["details"]:
            assert "quality_score" in detail
            assert "details" in detail
            assert detail["quality_score"] >= 0.0
            assert detail["quality_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_validate_extraction_quality_task_empty_list(self):
        """Test validation de qualité avec liste vide."""
        result = validate_extraction_quality_task([], 0.8)

        assert "error" in result
        assert result["error"] == "Aucune métadonnée à valider"

    @pytest.mark.asyncio
    async def test_validate_extraction_quality_task_low_quality(self):
        """Test validation de qualité avec métadonnées de faible qualité."""
        metadata_list = [
            {
                "path": "/music/song.mp3",
                "title": "Song",
                # Métadonnées minimales seulement
            }
        ]

        result = validate_extraction_quality_task(metadata_list, 0.9)

        assert result["total_validated"] == 1
        assert result["average_quality"] < 0.9
        assert result["validation_passed"] is False
        assert result["high_quality_count"] == 0
        assert result["low_quality_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_file_metadata_task_different_priorities(self):
        """Test extraction avec différentes priorités."""
        file_path = "/valid/test.mp3"
        scan_config = {"base_directory": "/music"}

        # Test priorité high
        result_high = extract_file_metadata_task(file_path, scan_config, "high")
        assert result_high["extraction_success"] is True

        # Test priorité normal
        result_normal = extract_file_metadata_task(file_path, scan_config, "normal")
        assert result_normal["extraction_success"] is True

        # Test priorité low
        result_low = extract_file_metadata_task(file_path, scan_config, "low")
        assert result_low["extraction_success"] is True

    @pytest.mark.asyncio
    async def test_extract_batch_metadata_task_large_batch(self):
        """Test extraction par lot avec un gros batch."""
        # Créer un batch de 150 fichiers
        file_paths = [f"/valid/song{i}.mp3" for i in range(150)]
        scan_config = {"base_directory": "/music"}

        result = extract_batch_metadata_task(file_paths, scan_config, "normal")

        assert result["total_files"] == 150
        assert result["successful"] == 150
        assert result["failed"] == 0
        assert len(result["results"]) == 150

    @pytest.mark.asyncio
    async def test_quality_calculation_comprehensive_metadata(self):
        """Test calcul de qualité avec métadonnées complètes."""
        metadata = {
            "path": "/music/complete_song.mp3",
            "title": "Complete Song",
            "artist": "Complete Artist",
            "album": "Complete Album",
            "duration": 240.0,
            "bitrate": 320,
            "file_type": "audio/mpeg",
            "genre": "Rock",
            "year": "2023",
            "track_number": 5,
            "disc_number": 1
        }

        from backend_worker.background_tasks.worker_extract import _calculate_metadata_quality

        score, details = _calculate_metadata_quality(metadata)

        assert score > 0.8  # Score élevé pour métadonnées complètes
        assert details["basic_fields"] == "3/3"
        assert details["technical_fields"] == "3/3"
        assert details["advanced_fields"] == "3/3"

    @pytest.mark.asyncio
    async def test_quality_calculation_minimal_metadata(self):
        """Test calcul de qualité avec métadonnées minimales."""
        metadata = {
            "path": "/music/minimal_song.mp3",
            "title": "Minimal Song"
            # Pas d'autres champs
        }

        from backend_worker.background_tasks.worker_extract import _calculate_metadata_quality

        score, details = _calculate_metadata_quality(metadata)

        assert score < 0.5  # Score faible pour métadonnées minimales
        assert details["basic_fields"] == "1/3"
        assert details["technical_fields"] == "0/3"
        assert details["advanced_fields"] == "0/3"

    @pytest.mark.asyncio
    async def test_enrich_extracted_metadata(self):
        """Test enrichissement des métadonnées extraites."""
        metadata = {
            "path": "/music/test.mp3",
            "title": "  Test Song  ",
            "artist": "Test Artist",
            "album": "Test Album",
            "duration": 180.0
        }

        scan_config = {"template": "{artist}/{album}/{title}"}

        from backend_worker.background_tasks.worker_extract import _enrich_extracted_metadata

        enriched = _enrich_extracted_metadata(metadata, scan_config)

        assert enriched["title"] == "Test Song"  # Espaces supprimés
        assert enriched["artist"] == "Test Artist"
        assert "processed_at" in enriched
        assert "processor" in enriched
        assert enriched["processor"] == "worker_extract"
        assert "quality_score" in enriched
        assert enriched["scan_template"] == "{artist}/{album}/{title}"

    @pytest.mark.asyncio
    async def test_validate_extracted_metadata_valid(self):
        """Test validation de métadonnées valides."""
        metadata = {
            "path": "/music/valid.mp3",
            "title": "Valid Song",
            "extraction_success": True,
            "duration": 180.0,
            "bitrate": 320
        }

        from backend_worker.background_tasks.worker_extract import _validate_extracted_metadata

        assert _validate_extracted_metadata(metadata) is True

    @pytest.mark.asyncio
    async def test_validate_extracted_metadata_invalid(self):
        """Test validation de métadonnées invalides."""
        # Métadonnées sans titre
        metadata_no_title = {
            "path": "/music/invalid.mp3",
            "extraction_success": True
        }

        # Métadonnées sans succès d'extraction
        metadata_no_success = {
            "path": "/music/invalid.mp3",
            "title": "Invalid Song"
        }

        # Métadonnées avec durée invalide
        metadata_invalid_duration = {
            "path": "/music/invalid.mp3",
            "title": "Invalid Song",
            "extraction_success": True,
            "duration": "invalid"
        }

        from backend_worker.background_tasks.worker_extract import _validate_extracted_metadata

        assert _validate_extracted_metadata(metadata_no_title) is False
        assert _validate_extracted_metadata(metadata_no_success) is False
        assert _validate_extracted_metadata(metadata_invalid_duration) is False