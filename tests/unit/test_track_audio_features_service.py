# -*- coding: utf-8 -*-
"""Tests unitaires ciblés pour TrackAudioFeaturesService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.api.services.track_audio_features_service import TrackAudioFeaturesService


class _FakeResult:
    """Résultat SQLAlchemy minimal pour tests unitaires."""

    def __init__(self, first_value=None, all_value=None):
        self._first_value = first_value
        self._all_value = all_value if all_value is not None else []

    def first(self):
        return self._first_value

    def all(self):
        return self._all_value


@pytest.mark.asyncio
async def test_get_analysis_statistics_handles_none_bpm_row() -> None:
    """Vérifie qu'aucune destructuration invalide n'est faite quand first() renvoie None."""
    session = MagicMock()
    service = TrackAudioFeaturesService(session)

    async def fake_count_analyzed_tracks() -> int:
        return 0

    service.count_analyzed_tracks = fake_count_analyzed_tracks  # type: ignore[method-assign]

    bpm_result = _FakeResult(first_value=None)
    by_source_result = _FakeResult(all_value=[("unknown", 0)])

    async def fake_execute(_stmt):
        if not hasattr(fake_execute, "_calls"):
            fake_execute._calls = 0  # type: ignore[attr-defined]
        fake_execute._calls += 1  # type: ignore[attr-defined]
        return bpm_result if fake_execute._calls == 1 else by_source_result  # type: ignore[attr-defined]

    service._execute = fake_execute  # type: ignore[method-assign]

    stats = await service.get_analysis_statistics()

    assert stats["total_analyzed"] == 0
    assert stats["bpm"]["average"] is None
    assert stats["bpm"]["min"] is None
    assert stats["bpm"]["max"] is None
    assert stats["by_source"] == {"unknown": 0}


@pytest.mark.asyncio
async def test_update_with_mir_integration_maps_only_analysis_source() -> None:
    """Vérifie qu'on mappe mir_source vers analysis_source sans toucher à des attributs inconnus."""
    session = MagicMock()
    service = TrackAudioFeaturesService(session)

    features = SimpleNamespace(
        bpm=None,
        key=None,
        scale=None,
        danceability=None,
        mood_happy=None,
        mood_aggressive=None,
        mood_party=None,
        mood_relaxed=None,
        instrumental=None,
        acoustic=None,
        tonal=None,
        genre_main=None,
        camelot_key=None,
        analysis_source=None,
        analyzed_at=None,
        date_modified=None,
    )

    async def fake_get_by_track_id(_track_id: int):
        return features

    async def fake_commit() -> None:
        return None

    async def fake_refresh(_instance) -> None:
        return None

    service.get_by_track_id = fake_get_by_track_id  # type: ignore[method-assign]
    service._commit = fake_commit  # type: ignore[method-assign]
    service._refresh = fake_refresh  # type: ignore[method-assign]

    updated = await service.update_with_mir_integration(
        track_id=1,
        mir_source="essentia",
        mir_version="v1.0.0",
        confidence_score=0.91,
    )

    assert updated is features
    assert features.analysis_source == "essentia"
    assert not hasattr(features, "mir_source")
    assert not hasattr(features, "mir_version")
    assert not hasattr(features, "confidence_score")
