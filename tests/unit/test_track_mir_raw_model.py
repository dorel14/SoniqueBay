# -*- coding: utf-8 -*-
"""
Tests unitaires — TrackMIRRaw : cohérence modèle / schéma DB.

Rôle:
    Vérifie que le modèle SQLAlchemy TrackMIRRaw expose bien les colonnes
    attendues après la migration fix_track_mir_raw_schema, et que les
    convertisseurs GraphQL (_mir_raw_to_type, résolveur mir_raw) fonctionnent
    correctement avec le modèle corrigé.

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mir_raw(
    id: int = 1,
    track_id: int = 42,
    features_raw: Dict[str, Any] | None = None,
    mir_source: str | None = "acoustid",
    mir_version: str | None = "1.0",
    analyzed_at: datetime | None = None,
    date_added: datetime | None = None,
    date_modified: datetime | None = None,
) -> MagicMock:
    """
    Crée un mock de TrackMIRRaw avec les attributs du modèle corrigé.

    Simule un objet SQLAlchemy retourné par la session sans accès DB réel.
    """
    obj = MagicMock()
    obj.id = id
    obj.track_id = track_id
    obj.features_raw = features_raw or {}
    obj.mir_source = mir_source
    obj.mir_version = mir_version
    obj.analyzed_at = analyzed_at or datetime(2026, 1, 1, 12, 0, 0)
    obj.date_added = date_added or datetime(2026, 1, 1, 12, 0, 0)
    obj.date_modified = date_modified or datetime(2026, 1, 1, 12, 0, 0)
    # S'assurer que les anciens attributs DB ne sont PAS présents
    del obj.extractor
    del obj.version
    del obj.tags_json
    del obj.created_at
    del obj.raw_data_json
    del obj.extraction_time
    del obj.confidence
    return obj


# ---------------------------------------------------------------------------
# Tests — Attributs du modèle
# ---------------------------------------------------------------------------


class TestTrackMIRRawModelAttributes:
    """Vérifie que le modèle expose les bons attributs (post-migration)."""

    def test_model_has_features_raw(self) -> None:
        """features_raw doit exister dans le modèle."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        assert hasattr(TrackMIRRaw, "features_raw"), (
            "TrackMIRRaw doit avoir la colonne 'features_raw' (pas 'tags_json')"
        )

    def test_model_has_mir_source(self) -> None:
        """mir_source doit exister dans le modèle."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        assert hasattr(TrackMIRRaw, "mir_source"), (
            "TrackMIRRaw doit avoir la colonne 'mir_source' (pas 'extractor')"
        )

    def test_model_has_mir_version(self) -> None:
        """mir_version doit exister dans le modèle."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        assert hasattr(TrackMIRRaw, "mir_version"), (
            "TrackMIRRaw doit avoir la colonne 'mir_version' (pas 'version')"
        )

    def test_model_has_analyzed_at(self) -> None:
        """analyzed_at doit exister dans le modèle."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        assert hasattr(TrackMIRRaw, "analyzed_at"), (
            "TrackMIRRaw doit avoir la colonne 'analyzed_at' (pas 'created_at')"
        )

    def test_model_does_not_have_extractor(self) -> None:
        """extractor ne doit PAS exister dans le modèle (renommé en mir_source)."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        # La colonne 'extractor' ne doit pas être mappée
        columns = [c.key for c in TrackMIRRaw.__table__.columns]
        assert "extractor" not in columns, (
            "La colonne 'extractor' ne doit plus exister dans TrackMIRRaw "
            "(elle a été renommée en 'mir_source' par fix_track_mir_raw_schema)"
        )

    def test_model_does_not_have_tags_json(self) -> None:
        """tags_json ne doit PAS exister dans le modèle (renommé en features_raw)."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        columns = [c.key for c in TrackMIRRaw.__table__.columns]
        assert "tags_json" not in columns, (
            "La colonne 'tags_json' ne doit plus exister dans TrackMIRRaw "
            "(elle a été renommée en 'features_raw' par fix_track_mir_raw_schema)"
        )

    def test_model_does_not_have_raw_data_json(self) -> None:
        """raw_data_json ne doit PAS exister dans le modèle (supprimée)."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        columns = [c.key for c in TrackMIRRaw.__table__.columns]
        assert "raw_data_json" not in columns, (
            "La colonne 'raw_data_json' a été supprimée par fix_track_mir_raw_schema"
        )

    def test_model_tablename(self) -> None:
        """Le nom de table doit être 'track_mir_raw'."""
        from backend.api.models.track_mir_raw_model import TrackMIRRaw

        assert TrackMIRRaw.__tablename__ == "track_mir_raw"


# ---------------------------------------------------------------------------
# Tests — Convertisseur GraphQL _mir_raw_to_type
# ---------------------------------------------------------------------------


class TestMirRawToType:
    """Vérifie que _mir_raw_to_type extrait correctement les champs depuis features_raw."""

    def test_returns_none_for_none_input(self) -> None:
        """_mir_raw_to_type(None) doit retourner None."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        assert _mir_raw_to_type(None) is None

    def test_extracts_bpm_from_features_raw(self) -> None:
        """bpm doit être extrait depuis features_raw['bpm']."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(features_raw={"bpm": 128, "key": "C"})
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.bpm == 128

    def test_extracts_key_from_features_raw(self) -> None:
        """key doit être extrait depuis features_raw['key']."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(features_raw={"key": "Am", "scale": "minor"})
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.key == "Am"
        assert result.scale == "minor"

    def test_extracts_genre_tags_from_features_raw(self) -> None:
        """genre_tags doit être extrait depuis features_raw['genre_tags']."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(
            features_raw={"genre_tags": ["rock", "indie"], "mood_tags": ["energetic"]}
        )
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.genre_tags == ["rock", "indie"]
        assert result.mood_tags == ["energetic"]

    def test_uses_mir_source_as_analysis_source(self) -> None:
        """analysis_source doit provenir de mir_source (pas d'un champ inexistant)."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(mir_source="librosa")
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.analysis_source == "librosa"

    def test_uses_analyzed_at_as_created_at(self) -> None:
        """created_at dans le type GraphQL doit provenir de analyzed_at du modèle."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        ts = datetime(2026, 3, 15, 10, 30, 0)
        mock_raw = _make_mir_raw(analyzed_at=ts)
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.created_at == ts

    def test_empty_features_raw_returns_defaults(self) -> None:
        """Un features_raw vide doit retourner des valeurs None/[] sans erreur."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(features_raw={})
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.bpm is None
        assert result.key is None
        assert result.genre_tags == []
        assert result.mood_tags == []

    def test_none_features_raw_returns_defaults(self) -> None:
        """Un features_raw None doit être traité comme {} sans lever d'exception."""
        from backend.api.graphql.queries.track_mir_queries import _mir_raw_to_type

        mock_raw = _make_mir_raw(features_raw=None)
        # Le convertisseur fait `raw.features_raw or {}` donc None → {}
        mock_raw.features_raw = None
        result = _mir_raw_to_type(mock_raw)

        assert result is not None
        assert result.bpm is None
        assert result.genre_tags == []


# ---------------------------------------------------------------------------
# Tests — Résolveur mir_raw dans TrackType
# ---------------------------------------------------------------------------


class TestTrackTypeMirRawResolver:
    """Vérifie que le résolveur mir_raw de TrackType extrait correctement les champs."""

    def _make_track_type_with_mir_raw(self, features_raw: dict, mir_source: str = "test"):
        """Crée un TrackType minimal avec _mir_raw mocké."""
        from backend.api.graphql.types.tracks_type import TrackType

        track = TrackType.__new__(TrackType)
        mock_raw = _make_mir_raw(features_raw=features_raw, mir_source=mir_source)
        track._mir_raw = mock_raw
        return track

    def test_resolver_extracts_bpm_from_features_raw(self) -> None:
        """Le résolveur doit extraire bpm depuis features_raw."""
        track = self._make_track_type_with_mir_raw({"bpm": 140})
        result = track.mir_raw()

        assert result is not None
        assert result.bpm == 140

    def test_resolver_uses_mir_source(self) -> None:
        """Le résolveur doit utiliser mir_source comme analysis_source."""
        track = self._make_track_type_with_mir_raw({}, mir_source="essentia")
        result = track.mir_raw()

        assert result is not None
        assert result.analysis_source == "essentia"

    def test_resolver_returns_none_when_no_mir_raw(self) -> None:
        """Le résolveur doit retourner None si _mir_raw est absent."""
        from backend.api.graphql.types.tracks_type import TrackType

        track = TrackType.__new__(TrackType)
        # Pas de _mir_raw défini
        result = track.mir_raw()

        assert result is None

    def test_resolver_returns_none_when_mir_raw_is_none(self) -> None:
        """Le résolveur doit retourner None si _mir_raw est None."""
        from backend.api.graphql.types.tracks_type import TrackType

        track = TrackType.__new__(TrackType)
        track._mir_raw = None
        result = track.mir_raw()

        assert result is None

    def test_resolver_handles_full_features_raw(self) -> None:
        """Le résolveur doit gérer un features_raw complet sans erreur."""
        full_features = {
            "bpm": 120,
            "key": "G",
            "scale": "major",
            "danceability": 0.75,
            "mood_happy": 0.8,
            "mood_aggressive": 0.1,
            "mood_party": 0.6,
            "mood_relaxed": 0.3,
            "instrumental": 0.9,
            "acoustic": 0.2,
            "tonal": 0.85,
            "genre_tags": ["pop", "dance"],
            "mood_tags": ["happy", "energetic"],
        }
        track = self._make_track_type_with_mir_raw(full_features, mir_source="acoustid")
        result = track.mir_raw()

        assert result is not None
        assert result.bpm == 120
        assert result.key == "G"
        assert result.scale == "major"
        assert result.danceability == 0.75
        assert result.mood_happy == 0.8
        assert result.instrumental == 0.9
        assert result.genre_tags == ["pop", "dance"]
        assert result.mood_tags == ["happy", "energetic"]
        assert result.analysis_source == "acoustid"
