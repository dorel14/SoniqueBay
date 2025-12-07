# -*- coding: utf-8 -*-
"""
Test d'intégration pour l'extraction des covers dans enrichment_worker.py
"""

import tempfile
import os
from unittest.mock import patch, MagicMock
from backend_worker.workers.metadata.enrichment_worker import extract_single_file_metadata

def test_cover_extraction_mp3_with_embedded_cover():
    """Test l'extraction des covers intégrées pour un fichier MP3 avec cover"""

    # Créer un fichier MP3 temporaire avec des métadonnées et une cover intégrée
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
        tmp_path = tmp_file.name

        try:
            # Créer un objet audio mock avec une cover intégrée
            mock_audio = MagicMock()
            mock_audio.info.length = 180
            mock_audio.info.bitrate = 192000

            # Créer une cover mock
            mock_apic = MagicMock()
            mock_apic.mime = 'image/jpeg'
            mock_apic.data = b'fake_image_data'

            mock_audio.__getitem__ = MagicMock(side_effect=lambda key: {
                'APIC:': mock_apic,
                'TIT2': 'Test Song',
                'TPE1': 'Test Artist',
                'TALB': 'Test Album',
                'TCON': 'Rock',
                'TDRC': '2023',
                'TRCK': '1'
            }.get(key))

            mock_audio.get = MagicMock(side_effect=lambda key, default=None: {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'genre': 'Rock',
                'date': '2023',
                'tracknumber': '1'
            }.get(key, default))

            # Mock des fonctions de music_scan
            with patch('backend_worker.workers.metadata.enrichment_worker.File') as mock_file, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_tag') as mock_get_tag, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_file_type') as mock_get_file_type, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_musicbrainz_tags') as mock_get_musicbrainz:

                # Configurer les mocks
                mock_file.return_value = mock_audio
                mock_get_tag.side_effect = mock_audio.get
                mock_get_file_type.return_value = 'audio/mpeg'
                mock_get_musicbrainz.return_value = {
                    'musicbrainz_artistid': '12345',
                    'musicbrainz_albumid': '67890',
                    'musicbrainz_id': 'abcde',
                    'acoustid_fingerprint': None
                }

                # Appeler la fonction
                result = extract_single_file_metadata(tmp_path)

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

        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

def test_cover_extraction_mp3_without_embedded_cover():
    """Test l'extraction des covers pour un fichier MP3 sans cover intégrée"""

    # Créer un fichier MP3 temporaire sans cover
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
        tmp_path = tmp_file.name

        try:
            # Créer un objet audio mock sans cover intégrée
            mock_audio = MagicMock()
            mock_audio.info.length = 180
            mock_audio.info.bitrate = 192000

            # Pas de cover dans __getitem__
            mock_audio.__getitem__ = MagicMock(side_effect=lambda key: {
                'TIT2': 'Test Song',
                'TPE1': 'Test Artist',
                'TALB': 'Test Album',
                'TCON': 'Rock',
                'TDRC': '2023',
                'TRCK': '1'
            }.get(key))

            mock_audio.get = MagicMock(side_effect=lambda key, default=None: {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'genre': 'Rock',
                'date': '2023',
                'tracknumber': '1'
            }.get(key, default))

            # Mock des fonctions de music_scan
            with patch('backend_worker.workers.metadata.enrichment_worker.File') as mock_file, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_tag') as mock_get_tag, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_file_type') as mock_get_file_type, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_musicbrainz_tags') as mock_get_musicbrainz:

                # Configurer les mocks
                mock_file.return_value = mock_audio
                mock_get_tag.side_effect = mock_audio.get
                mock_get_file_type.return_value = 'audio/mpeg'
                mock_get_musicbrainz.return_value = {
                    'musicbrainz_artistid': '12345',
                    'musicbrainz_albumid': '67890',
                    'musicbrainz_id': 'abcde',
                    'acoustid_fingerprint': None
                }

                # Appeler la fonction
                result = extract_single_file_metadata(tmp_path)

                # Vérifier que les métadonnées de base sont présentes
                assert result is not None
                assert result['title'] == 'Test Song'
                assert result['artist'] == 'Test Artist'
                assert result['album'] == 'Test Album'

                # Vérifier que la cover n'a pas été extraite (pas de cover intégrée)
                assert 'cover_data' not in result
                assert 'cover_mime_type' not in result

        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

def test_cover_extraction_flac_with_embedded_cover():
    """Test l'extraction des covers intégrées pour un fichier FLAC avec cover"""

    # Créer un fichier FLAC temporaire avec des métadonnées et une cover intégrée
    with tempfile.NamedTemporaryFile(suffix='.flac', delete=False) as tmp_file:
        tmp_path = tmp_file.name

        try:
            # Créer un objet audio mock avec une cover intégrée (format FLAC)
            mock_audio = MagicMock()
            mock_audio.info.length = 240
            mock_audio.info.bitrate = 1000  # FLAC bitrate calculé

            # Créer une picture mock pour FLAC
            mock_picture = MagicMock()
            mock_picture.mime = 'image/png'
            mock_picture.data = b'fake_flac_image_data'

            mock_audio.pictures = [mock_picture]

            mock_audio.__getitem__ = MagicMock(side_effect=lambda key: {
                'TIT2': 'FLAC Song',
                'TPE1': 'FLAC Artist',
                'TALB': 'FLAC Album',
                'TCON': 'Jazz',
                'TDRC': '2022',
                'TRCK': '2'
            }.get(key))

            mock_audio.get = MagicMock(side_effect=lambda key, default=None: {
                'title': 'FLAC Song',
                'artist': 'FLAC Artist',
                'album': 'FLAC Album',
                'genre': 'Jazz',
                'date': '2022',
                'tracknumber': '2'
            }.get(key, default))

            # Mock des fonctions de music_scan
            with patch('backend_worker.workers.metadata.enrichment_worker.File') as mock_file, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_tag') as mock_get_tag, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_file_type') as mock_get_file_type, \
                 patch('backend_worker.workers.metadata.enrichment_worker.get_musicbrainz_tags') as mock_get_musicbrainz:

                # Configurer les mocks
                mock_file.return_value = mock_audio
                mock_get_tag.side_effect = mock_audio.get
                mock_get_file_type.return_value = 'audio/flac'
                mock_get_musicbrainz.return_value = {
                    'musicbrainz_artistid': 'flac123',
                    'musicbrainz_albumid': 'flac456',
                    'musicbrainz_id': 'flac789',
                    'acoustid_fingerprint': None
                }

                # Appeler la fonction
                result = extract_single_file_metadata(tmp_path)

                # Vérifier que les métadonnées de base sont présentes
                assert result is not None
                assert result['title'] == 'FLAC Song'
                assert result['artist'] == 'FLAC Artist'
                assert result['album'] == 'FLAC Album'
                assert result['genre'] == 'Jazz'

                # Vérifier que la cover FLAC a été extraite
                assert 'cover_data' in result
                assert 'cover_mime_type' in result
                assert result['cover_mime_type'] == 'image/png'
                assert 'data:image/png;base64,' in result['cover_data']
                assert 'fake_flac_image_data' in result['cover_data']

        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

if __name__ == "__main__":
    print("Exécution des tests d'intégration des covers...")
    test_cover_extraction_mp3_with_embedded_cover()
    print("✓ Test MP3 avec cover intégré - PASSED")
    test_cover_extraction_mp3_without_embedded_cover()
    print("✓ Test MP3 sans cover intégré - PASSED")
    test_cover_extraction_flac_with_embedded_cover()
    print("✓ Test FLAC avec cover intégré - PASSED")
    print("Tous les tests d'intégration des covers ont passé avec succès !")