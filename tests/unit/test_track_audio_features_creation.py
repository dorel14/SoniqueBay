# -*- coding: utf-8 -*-
"""
Tests unitaires pour la création de tracks avec caractéristiques audio.

Valide que les champs audio (bpm, key, etc.) sont correctement transmis
à TrackAudioFeatures lors de la création de tracks via GraphQL.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.api.schemas.tracks_schema import TrackCreate
from backend.api.services.track_service import TrackService
from backend.api.services.track_audio_features_service import TrackAudioFeaturesService


class TestTrackAudioFeaturesCreation:
    """Tests pour la création de tracks avec audio features."""

    @pytest.fixture
    def mock_session(self):
        """Mock session SQLAlchemy."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_audio_features_service(self, mock_session):
        """Mock TrackAudioFeaturesService."""
        service = TrackAudioFeaturesService(mock_session)
        service.create_or_update = AsyncMock()
        return service

    @pytest.fixture
    def track_service(self, mock_session, mock_audio_features_service):
        """TrackService avec mocks."""
        service = TrackService(mock_session)
        service.audio_features_service = mock_audio_features_service
        return service

    def test_track_create_with_audio_features(self, track_service, mock_session, mock_audio_features_service):
        """Test création track avec champs audio — doit créer TrackAudioFeatures."""
        # Données de test avec audio features
        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            album_id=1,
            bpm=120.0,
            key="C",
            scale="major",
            danceability=0.8,
            mood_happy=0.7,
            mood_aggressive=0.2,
            mood_party=0.6,
            mood_relaxed=0.5,
            instrumental=0.1,
            acoustic=0.3,
            tonal=0.9,
            camelot_key="8B",
            genre_main="Electronic"
        )

        # Mock TrackModel
        mock_track = MagicMock()
        mock_track.id = 123
        mock_session.add.return_value = None
        mock_session.refresh.side_effect = lambda t: setattr(t, 'id', 123)

        # Exécution
        result = track_service.create_track(track_data)

        # Vérifications
        assert result.id == 123
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Vérifier que TrackAudioFeatures a été créé
        mock_audio_features_service.create_or_update.assert_called_once_with(
            track_id=123,
            bpm=120.0,
            key="C",
            scale="major",
            danceability=0.8,
            mood_happy=0.7,
            mood_aggressive=0.2,
            mood_party=0.6,
            mood_relaxed=0.5,
            instrumental=0.1,
            acoustic=0.3,
            tonal=0.9,
            camelot_key="8B",
            genre_main="Electronic",
            analysis_source='tags'
        )

    def test_track_create_without_audio_features(self, track_service, mock_session, mock_audio_features_service):
        """Test création track sans champs audio — ne doit pas créer TrackAudioFeatures."""
        # Données de test sans audio features
        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            album_id=1,
            genre="Rock"
        )

        # Mock TrackModel
        mock_track = MagicMock()
        mock_track.id = 456
        mock_session.refresh.side_effect = lambda t: setattr(t, 'id', 456)

        # Exécution
        result = track_service.create_track(track_data)

        # Vérifications
        assert result.id == 456
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Vérifier que TrackAudioFeatures n'a PAS été créé
        mock_audio_features_service.create_or_update.assert_not_called()

    def test_track_create_partial_audio_features(self, track_service, mock_session, mock_audio_features_service):
        """Test création track avec quelques champs audio seulement."""
        # Données de test avec audio features partielles
        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            album_id=1,
            bpm=140.0,
            key="A",
            # Autres champs audio None
        )

        # Mock TrackModel
        mock_track = MagicMock()
        mock_track.id = 789
        mock_session.refresh.side_effect = lambda t: setattr(t, 'id', 789)

        # Exécution
        result = track_service.create_track(track_data)

        # Vérifications
        assert result.id == 789

        # Vérifier que TrackAudioFeatures a été créé avec les valeurs fournies
        mock_audio_features_service.create_or_update.assert_called_once_with(
            track_id=789,
            bpm=140.0,
            key="A",
            scale=None,
            danceability=None,
            mood_happy=None,
            mood_aggressive=None,
            mood_party=None,
            mood_relaxed=None,
            instrumental=None,
            acoustic=None,
            tonal=None,
            camelot_key=None,
            genre_main=None,
            analysis_source='tags'
        )

    def test_track_create_schema_accepts_audio_fields(self):
        """Test que TrackCreate accepte les champs audio."""
        # Cette assertion devrait réussir maintenant que nous avons ajouté les champs
        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            bpm=120.0,
            key="C",
            scale="major"
        )

        assert track_data.bpm == 120.0
        assert track_data.key == "C"
        assert track_data.scale == "major"
        assert track_data.title == "Test Track"
        assert track_data.path == "/music/test.mp3"
        assert track_data.track_artist_id == 1
