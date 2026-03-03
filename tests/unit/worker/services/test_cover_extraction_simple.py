# -*- coding: utf-8 -*-
"""
Test simple pour vérifier que l'extraction des covers fonctionne dans enrichment_worker.py
"""

from unittest.mock import patch, MagicMock
from backend_worker.workers.metadata.enrichment_worker import extract_single_file_metadata

def test_cover_extraction_logic():
    """Test simple pour vérifier la logique d'extraction des covers"""

    # Créer un mock pour l'objet audio avec une cover MP3
    mock_audio = MagicMock()
    mock_audio.info.length = 180
    mock_audio.info.bitrate = 192000

    # Créer une cover mock
    mock_apic = MagicMock()
    mock_apic.mime = 'image/jpeg'
    mock_apic.data = b'fake_image_data'

    # Configurer le mock pour retourner la cover quand on demande 'APIC:'
    def mock_getitem(key):
        if key == 'APIC:':
            return mock_apic
        elif key == 'TIT2':
            return 'Test Song'
        elif key == 'TPE1':
            return 'Test Artist'
        elif key == 'TALB':
            return 'Test Album'
        return None

    mock_audio.__getitem__ = mock_getitem

    # Configurer le mock pour les appels get()
    def mock_get(key, default=None):
        if key == 'title':
            return 'Test Song'
        elif key == 'artist':
            return 'Test Artist'
        elif key == 'album':
            return 'Test Album'
        elif key == 'genre':
            return 'Rock'
        elif key == 'date':
            return '2023'
        elif key == 'tracknumber':
            return '1'
        return default

    mock_audio.get = mock_get

    # Mock des fonctions importées
    with patch('backend_worker.workers.metadata.enrichment_worker.File') as mock_file, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_tag') as mock_get_tag, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_file_type') as mock_get_file_type, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_musicbrainz_tags') as mock_get_musicbrainz, \
         patch('backend_worker.workers.metadata.enrichment_worker.sanitize_path') as mock_sanitize_path:

        # Configurer les mocks
        mock_file.return_value = mock_audio
        mock_get_tag.side_effect = mock_get
        mock_get_file_type.return_value = 'audio/mpeg'
        mock_get_musicbrainz.return_value = {
            'musicbrainz_artistid': '12345',
            'musicbrainz_albumid': '67890',
            'musicbrainz_id': 'abcde',
            'acoustid_fingerprint': None
        }
        mock_sanitize_path.return_value = '/fake/path/test.mp3'

        # Appeler la fonction avec un chemin fictif
        result = extract_single_file_metadata('/fake/path/test.mp3')

        # Vérifier que les métadonnées de base sont présentes
        assert result is not None
        assert result['title'] == 'Test Song'
        assert result['artist'] == 'Test Artist'
        assert result['album'] == 'Test Album'
        assert result['genre'] == 'Rock'
        assert result['year'] == '2023'
        assert result['track_number'] == '1'
        assert result['duration'] == 180
        assert result['bitrate'] == 192
        assert result['file_type'] == 'audio/mpeg'

        # Vérifier que la cover a été extraite
        assert 'cover_data' in result
        assert 'cover_mime_type' in result
        assert result['cover_mime_type'] == 'image/jpeg'
        assert 'data:image/jpeg;base64,' in result['cover_data']
        assert 'fake_image_data' in result['cover_data']

        # Vérifier que les IDs MusicBrainz sont présents
        assert result['musicbrainz_artistid'] == '12345'
        assert result['musicbrainz_albumid'] == '67890'
        assert result['musicbrainz_id'] == 'abcde'

def test_cover_extraction_no_cover():
    """Test simple pour vérifier que l'extraction fonctionne quand il n'y a pas de cover"""

    # Créer un mock pour l'objet audio SANS cover
    mock_audio = MagicMock()
    mock_audio.info.length = 180
    mock_audio.info.bitrate = 192000

    # Configurer le mock pour ne PAS retourner de cover
    def mock_getitem(key):
        if key == 'TIT2':
            return 'Test Song'
        elif key == 'TPE1':
            return 'Test Artist'
        elif key == 'TALB':
            return 'Test Album'
        return None  # Pas de cover

    mock_audio.__getitem__ = mock_getitem

    # Configurer le mock pour les appels get()
    def mock_get(key, default=None):
        if key == 'title':
            return 'Test Song'
        elif key == 'artist':
            return 'Test Artist'
        elif key == 'album':
            return 'Test Album'
        elif key == 'genre':
            return 'Rock'
        elif key == 'date':
            return '2023'
        elif key == 'tracknumber':
            return '1'
        return default

    mock_audio.get = mock_get

    # Mock des fonctions importées
    with patch('backend_worker.workers.metadata.enrichment_worker.File') as mock_file, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_tag') as mock_get_tag, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_file_type') as mock_get_file_type, \
         patch('backend_worker.workers.metadata.enrichment_worker.get_musicbrainz_tags') as mock_get_musicbrainz, \
         patch('backend_worker.workers.metadata.enrichment_worker.sanitize_path') as mock_sanitize_path:

        # Configurer les mocks
        mock_file.return_value = mock_audio
        mock_get_tag.side_effect = mock_get
        mock_get_file_type.return_value = 'audio/mpeg'
        mock_get_musicbrainz.return_value = {
            'musicbrainz_artistid': '12345',
            'musicbrainz_albumid': '67890',
            'musicbrainz_id': 'abcde',
            'acoustid_fingerprint': None
        }
        mock_sanitize_path.return_value = '/fake/path/test.mp3'

        # Appeler la fonction avec un chemin fictif
        result = extract_single_file_metadata('/fake/path/test.mp3')

        # Vérifier que les métadonnées de base sont présentes
        assert result is not None
        assert result['title'] == 'Test Song'
        assert result['artist'] == 'Test Artist'
        assert result['album'] == 'Test Album'

        # Vérifier que la cover n'a PAS été extraite (pas de cover intégrée)
        assert 'cover_data' not in result
        assert 'cover_mime_type' not in result

if __name__ == "__main__":
    print("Exécution des tests simples d'extraction des covers...")
    test_cover_extraction_logic()
    print("✓ Test avec cover intégrée - PASSED")
    test_cover_extraction_no_cover()
    print("✓ Test sans cover intégrée - PASSED")
    print("Tous les tests simples d'extraction des covers ont passé avec succès !")