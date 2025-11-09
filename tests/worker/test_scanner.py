import pytest
from unittest.mock import patch

from backend_worker.services.scanner import count_music_files

@pytest.mark.asyncio
async def test_count_music_files():
    """Test le comptage des fichiers musicaux."""
    # Créer un mock pour async_walk
    with patch('backend_worker.services.scanner.async_walk') as mock_walk:
        # Configurer le mock
        mock_walk.return_value.__aiter__.return_value = [
            b"/path/to/track1.mp3",
            b"/path/to/track2.flac",
            b"/path/to/file.txt"
        ]

        # Appeler la fonction
        result = await count_music_files("/path/to/music", {b'.mp3', b'.flac'})

        # Vérifier le résultat
        assert result == 2

@pytest.mark.asyncio
async def test_count_music_files_empty():
    """Test le comptage avec aucun fichier musical."""
    with patch('backend_worker.services.scanner.async_walk') as mock_walk:
        # Configurer le mock avec seulement des fichiers non musicaux
        mock_walk.return_value.__aiter__.return_value = [
            b"/path/to/file.txt",
            b"/path/to/document.pdf"
        ]

        # Appeler la fonction
        result = await count_music_files("/path/to/music", {b'.mp3', b'.flac'})

        # Vérifier le résultat
        assert result == 0