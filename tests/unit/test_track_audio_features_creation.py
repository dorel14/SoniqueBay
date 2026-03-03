# -*- coding: utf-8 -*-
"""
Tests unitaires pour la création de tracks avec caractéristiques audio.

Valide que les champs audio (bpm, key, etc.) sont correctement transmis
à TrackAudioFeatures lors de la création de tracks via GraphQL.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.api.schemas.tracks_schema import TrackCreate


class TestTrackAudioFeaturesCreation:
    """Tests pour la création de tracks avec audio features."""

    @pytest.fixture
    def mock_session(self):
        """Mock session SQLAlchemy asynchrone."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.is_active = True
        return session

    @pytest.fixture
    def mock_audio_features_service(self):
        """Mock TrackAudioFeaturesService."""
        service = AsyncMock()
        service.create_or_update = AsyncMock()
        return service

    @pytest.fixture
    def track_service(self, mock_session, mock_audio_features_service):
        """TrackService avec mocks injectés."""
        from backend.api.services.track_service import TrackService
        service = TrackService(mock_session)
        service.audio_features_service = mock_audio_features_service
        return service

    @pytest.mark.asyncio
    async def test_track_create_with_audio_features(
        self, track_service, mock_session, mock_audio_features_service
    ):
        """Test création track avec champs audio — doit créer TrackAudioFeatures."""
        # Simuler le refresh qui assigne un id au TrackModel
        async def fake_refresh(obj):
            obj.id = 123

        mock_session.refresh.side_effect = fake_refresh

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
            genre_main="Electronic",
        )

        result = await track_service.create_track(track_data)

        # Vérifications de base
        assert result.id == 123
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Vérifier que TrackAudioFeatures a été créé avec les bonnes valeurs
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
            analysis_source="tags",
        )

    @pytest.mark.asyncio
    async def test_track_create_without_audio_features(
        self, track_service, mock_session, mock_audio_features_service
    ):
        """Test création track sans champs audio — ne doit PAS créer TrackAudioFeatures."""
        async def fake_refresh(obj):
            obj.id = 456

        mock_session.refresh.side_effect = fake_refresh

        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            album_id=1,
            genre="Rock",
        )

        result = await track_service.create_track(track_data)

        assert result.id == 456
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # TrackAudioFeatures ne doit PAS être créé si aucun champ audio n'est fourni
        mock_audio_features_service.create_or_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_create_partial_audio_features(
        self, track_service, mock_session, mock_audio_features_service
    ):
        """Test création track avec quelques champs audio seulement."""
        async def fake_refresh(obj):
            obj.id = 789

        mock_session.refresh.side_effect = fake_refresh

        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            album_id=1,
            bpm=140.0,
            key="A",
            # Autres champs audio laissés à None
        )

        result = await track_service.create_track(track_data)

        assert result.id == 789

        # Vérifier que TrackAudioFeatures a été créé avec les valeurs partielles
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
            analysis_source="tags",
        )

    def test_track_create_schema_accepts_audio_fields(self):
        """Test que TrackCreate accepte les champs audio sans AttributeError."""
        track_data = TrackCreate(
            title="Test Track",
            path="/music/test.mp3",
            track_artist_id=1,
            bpm=120.0,
            key="C",
            scale="major",
            danceability=0.75,
            mood_happy=0.6,
            mood_aggressive=0.1,
            mood_party=0.5,
            mood_relaxed=0.8,
            instrumental=0.05,
            acoustic=0.4,
            tonal=0.9,
            camelot_key="8B",
            genre_main="Electronic",
        )

        # Tous les champs audio doivent être accessibles sans AttributeError
        assert track_data.bpm == 120.0
        assert track_data.key == "C"
        assert track_data.scale == "major"
        assert track_data.danceability == 0.75
        assert track_data.mood_happy == 0.6
        assert track_data.mood_aggressive == 0.1
        assert track_data.mood_party == 0.5
        assert track_data.mood_relaxed == 0.8
        assert track_data.instrumental == 0.05
        assert track_data.acoustic == 0.4
        assert track_data.tonal == 0.9
        assert track_data.camelot_key == "8B"
        assert track_data.genre_main == "Electronic"
        assert track_data.title == "Test Track"
        assert track_data.path == "/music/test.mp3"
        assert track_data.track_artist_id == 1

    def test_track_create_schema_defaults_audio_fields_to_none(self):
        """Test que les champs audio sont None par défaut dans TrackCreate."""
        track_data = TrackCreate(
            title="Minimal Track",
            path="/music/minimal.mp3",
            track_artist_id=1,
        )

        assert track_data.bpm is None
        assert track_data.key is None
        assert track_data.scale is None
        assert track_data.danceability is None
        assert track_data.mood_happy is None
        assert track_data.mood_aggressive is None
        assert track_data.mood_party is None
        assert track_data.mood_relaxed is None
        assert track_data.instrumental is None
        assert track_data.acoustic is None
        assert track_data.tonal is None
        assert track_data.camelot_key is None
        assert track_data.genre_main is None
