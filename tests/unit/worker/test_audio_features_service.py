"""Tests unitaires pour AudioFeaturesService.

Ces tests vérifient le bon fonctionnement du service d'extraction
de caractéristiques audio.

Auteur: SoniqueBay Team
Version: 2.0.0
"""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import os
import tempfile

from backend_worker.services.audio_features_service import (
    AudioFeaturesService,
    extract_audio_features,
    _extract_features_from_acoustid_tags,
    _extract_features_from_standard_tags,
    _has_valid_acoustid_tags,
    _has_valid_audio_tags,
    analyze_audio_with_librosa,
)


class TestAudioFeaturesService:
    """Tests pour AudioFeaturesService."""
    
    @pytest.fixture
    def service(self):
        """Fixture pour créer une instance du service."""
        return AudioFeaturesService()
    
    def test_has_valid_acoustid_tags_with_valid_tags(self):
        """Test la détection de tags AcoustID valides."""
        tags = {
            'ab:hi:danceability': 0.8,
            'ab:lo:rhythm:bpm': 120,
        }
        assert _has_valid_acoustid_tags(tags) is True
    
    def test_has_valid_acoustid_tags_with_invalid_tags(self):
        """Test la détection de tags AcoustID invalides."""
        tags = {
            'bpm': 120,
            'key': 'C',
        }
        assert _has_valid_acoustid_tags(tags) is False
    
    def test_has_valid_acoustid_tags_empty(self):
        """Test la détection avec tags vides."""
        assert _has_valid_acoustid_tags({}) is False
        assert _has_valid_acoustid_tags(None) is False
    
    def test_has_valid_audio_tags_with_valid_tags(self):
        """Test la détection de tags audio valides."""
        tags = {
            'bpm': 120,
            'key': 'C',
        }
        assert _has_valid_audio_tags(tags) is True
    
    def test_has_valid_audio_tags_with_invalid_tags(self):
        """Test la détection de tags audio invalides."""
        tags = {
            'random_tag': 'value',
        }
        assert _has_valid_audio_tags(tags) is False
    
    def test_extract_features_from_acoustid_tags_complete(self):
        """Test l'extraction complète des features AcoustID."""
        tags = {
            'ab:lo:rhythm:bpm': ['120'],
            'ab:lo:tonal:key_key': ['C'],
            'ab:lo:tonal:key_scale': ['major'],
            'ab:hi:danceability:danceable': ['0.8'],
            'ab:hi:mood_happy:happy': ['0.7'],
            'ab:hi:voice_instrumental:instrumental': ['0.2'],
            'ab:genre': ['rock', 'pop'],
            'ab:mood': ['energetic'],
        }
        
        features = _extract_features_from_acoustid_tags(tags)
        
        assert features['bpm'] == 120.0
        assert features['key'] == 'C'
        assert features['scale'] == 'major'
        assert features['danceability'] == 0.8
        assert features['mood_happy'] == 0.7
        assert features['instrumental'] == 0.2
        assert 'rock' in features['genre_tags']
        assert 'energetic' in features['mood_tags']
    
    def test_extract_features_from_acoustid_tags_partial(self):
        """Test l'extraction partielle des features AcoustID."""
        tags = {
            'ab:lo:rhythm:bpm': ['120'],
        }
        
        features = _extract_features_from_acoustid_tags(tags)
        
        assert features['bpm'] == 120.0
        assert 'key' not in features
    
    def test_extract_features_from_standard_tags_complete(self):
        """Test l'extraction complète des tags standards."""
        tags = {
            'bpm': ['120'],
            'key': ['C'],
            'genre': ['rock'],
        }
        
        features = _extract_features_from_standard_tags(tags)
        
        assert features['bpm'] == 120.0
        assert features['key'] == 'C'
        assert 'rock' in features['genre_tags']
    
    def test_extract_features_from_standard_tags_empty(self):
        """Test l'extraction avec tags vides."""
        features = _extract_features_from_standard_tags({})
        assert features == {}
    
    def test_extract_audio_features_with_acoustid_tags(self):
        """Test l'extraction avec tags AcoustID."""
        tags = {
            'ab:lo:rhythm:bpm': ['120'],
            'ab:lo:tonal:key_key': ['C'],
        }
        
        features = extract_audio_features(tags=tags)
        
        assert features['bpm'] == 120.0
        assert features['key'] == 'C'
    
    def test_extract_audio_features_with_standard_tags(self):
        """Test l'extraction avec tags standards."""
        tags = {
            'bpm': ['120'],
            'key': ['C'],
        }
        
        features = extract_audio_features(tags=tags)
        
        assert features['bpm'] == 120.0
        assert features['key'] == 'C'
    
    def test_extract_audio_features_empty(self):
        """Test l'extraction avec tags vides."""
        features = extract_audio_features(tags={})
        
        assert 'bpm' in features
        assert features.get('bpm') is None or features.get('bpm') == 0
    
    @pytest.mark.asyncio
    async def test_analyze_audio_with_librosa_file_not_found(self):
        """Test l'analyse avec fichier inexistant."""
        result = await analyze_audio_with_librosa(1, '/nonexistent/file.wav')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_analyze_audio_with_librosa_success(self, tmp_path):
        """Test l'analyse audio avec Librosa."""
        # Créer un fichier audio temporaire factice
        test_file = tmp_path / "test.wav"
        test_file.write_bytes(b"RIFF" + b"\x00" * 100)  # Fichier WAV minimaliste
        
        # Mock librosa
        mock_y = np.zeros(1000)
        mock_sr = 22050
        
        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, None)):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 10)):
                    with patch('librosa.feature.rms', return_value=np.array([[0.5]])):
                        with patch('librosa.onset.onset_strength', return_value=np.array([0.8])):
                            with patch('librosa.feature.spectral_contrast', return_value=np.random.rand(6, 10)):
                                with patch('librosa.get_duration', return_value=180.0):
                                    result = await analyze_audio_with_librosa(1, str(test_file))
        
        assert result is not None
        assert 'bpm' in result
        assert 'key' in result
        assert 'duration' in result
    
    def test_service_extract_from_acoustid_tags(self, service):
        """Test la méthode du service pour extraire des tags AcoustID."""
        tags = {
            'ab:hi:danceability': 0.8,
            'ab:hi:energy': 0.7,
        }
        
        features = service._extract_from_acoustid_tags(tags)
        
        assert features is not None
        assert features['danceability'] == 0.8
        assert features['energy'] == 0.7
    
    def test_service_extract_with_librosa_mock(self, service):
        """Test la méthode du service avec Librosa mocké."""
        mock_y = np.zeros(1000)
        mock_sr = 22050
        
        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, None)):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 10)):
                    with patch('librosa.feature.rms', return_value=np.array([[0.5]])):
                        with patch('librosa.onset.onset_strength', return_value=np.array([0.8])):
                            with patch('librosa.feature.spectral_contrast', return_value=np.random.rand(6, 10)):
                                with patch('librosa.get_duration', return_value=180.0):
                                    # Créer un fichier temporaire
                                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                                        f.write(b"dummy")
                                        temp_path = f.name
                                    
                                    try:
                                        features = service._extract_with_librosa(temp_path)
                                        
                                        assert features is not None
                                        assert 'bpm' in features
                                        assert 'key' in features
                                        assert 'duration' in features
                                    finally:
                                        os.unlink(temp_path)
    
    def test_service_estimate_key(self, service):
        """Test l'estimation de la tonalité."""
        # Créer un chromagram mock
        chroma = np.array([
            [1, 0, 0, 0, 1, 0, 0, 1, 0, 0],  # C
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # C#
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # D
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # D#
            [1, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # E
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # F
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # F#
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # G
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # G#
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # A
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # A#
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # B
        ])
        
        key = service._estimate_key(chroma)
        
        # La clé devrait être C (la plus forte)
        assert key == 'C'
    
    def test_service_extract_audio_features_with_tags(self, service):
        """Test l'extraction complète avec tags."""
        tags = {
            'ab:hi:danceability': 0.8,
            'ab:lo:rhythm:bpm': 120,
        }
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b"dummy")
            temp_path = f.name
        
        try:
            features = service.extract_audio_features(temp_path, tags)
            
            assert features is not None
            assert features['danceability'] == 0.8
            assert features['bpm'] == 120.0
        finally:
            os.unlink(temp_path)
    
    def test_service_extract_audio_features_fallback_to_librosa(self, service):
        """Test le fallback vers Librosa quand pas de tags."""
        mock_y = np.zeros(1000)
        mock_sr = 22050
        
        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, None)):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 10)):
                    with patch('librosa.feature.rms', return_value=np.array([[0.5]])):
                        with patch('librosa.onset.onset_strength', return_value=np.array([0.8])):
                            with patch('librosa.feature.spectral_contrast', return_value=np.random.rand(6, 10)):
                                with patch('librosa.get_duration', return_value=180.0):
                                    # Créer un fichier temporaire
                                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                                        f.write(b"dummy")
                                        temp_path = f.name
                                    
                                    try:
                                        features = service.extract_audio_features(temp_path, {})
                                        
                                        assert features is not None
                                        assert 'bpm' in features
                                    finally:
                                        os.unlink(temp_path)


class TestAudioFeaturesEdgeCases:
    """Tests pour les cas limites."""
    
    def test_extract_features_from_acoustid_tags_invalid_values(self):
        """Test l'extraction avec valeurs invalides."""
        tags = {
            'ab:lo:rhythm:bpm': ['invalid'],
            'ab:lo:tonal:key_key': ['C'],
        }
        
        # Ne devrait pas planter, juste ignorer la valeur invalide
        features = _extract_features_from_acoustid_tags(tags)
        
        assert 'bpm' not in features  # Valeur invalide ignorée
        assert features['key'] == 'C'  # Valeur valide conservée
    
    def test_extract_features_from_acoustid_tags_list_values(self):
        """Test l'extraction avec valeurs en liste."""
        tags = {
            'ab:lo:rhythm:bpm': ['120', '121'],  # Liste de valeurs
            'ab:lo:tonal:key_key': ['C', 'D'],   # Liste de clés
        }
        
        features = _extract_features_from_acoustid_tags(tags)
        
        # Devrait prendre la première valeur
        assert features['bpm'] == 120.0
        assert features['key'] == 'C'
    
    def test_has_valid_audio_tags_none_values(self):
        """Test avec valeurs None."""
        tags = {
            'bpm': None,
            'key': '',
        }
        assert _has_valid_audio_tags(tags) is False
    
    def test_service_extract_with_librosa_import_error(self):
        """Test le comportement quand Librosa n'est pas installé."""
        service = AudioFeaturesService()
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'librosa'")):
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(b"dummy")
                temp_path = f.name
            
            try:
                features = service._extract_with_librosa(temp_path)
                assert features is None
            finally:
                os.unlink(temp_path)
