"""Script de test autonome pour MusicSummaryService.

Ce script teste le service de résumé musical sans dépendre de la configuration
complète du projet (Redis, DB, etc.).

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import sys
sys.path.insert(0, '.')

from backend_worker.services.music_summary_service import MusicSummaryService


def test_format_key_display():
    """Test de formatage de la clé."""
    service = MusicSummaryService()
    
    # Test avec données complètes
    result = service._format_key_display('C', 'major', '8B')
    assert 'C' in result, f"Key C manquant dans: {result}"
    assert 'Major' in result, f"Scale Major manquant dans: {result}"
    assert '8B' in result, f"Camelot 8B manquant dans: {result}"
    print("✓ test_format_key_display: OK")


def test_get_mood_from_features():
    """Test de détection du mood."""
    service = MusicSummaryService()
    
    # Test mood happy
    features = {'mood_happy': 0.7, 'mood_aggressive': 0.1}
    result = service._get_mood_from_features(features)
    assert result == 'happy', f"Expected 'happy', got {result}"
    
    # Test mood party (plus élevé)
    features = {'mood_happy': 0.3, 'mood_aggressive': 0.2, 'mood_party': 0.6}
    result = service._get_mood_from_features(features)
    assert result == 'party', f"Expected 'party', got {result}"
    
    # Test avec scores trop bas
    features = {'mood_happy': 0.2, 'mood_aggressive': 0.1}
    result = service._get_mood_from_features(features)
    assert result is None, f"Expected None, got {result}"
    
    print("✓ test_get_mood_from_features: OK")


def test_get_energy_level():
    """Test de détection du niveau d'énergie."""
    service = MusicSummaryService()
    
    assert service._get_energy_level(0.8) == 'high'
    assert service._get_energy_level(0.2) == 'low'
    assert service._get_energy_level(0.5) == 'medium'
    assert service._get_energy_level(None) is None
    
    print("✓ test_get_energy_level: OK")


def test_generate_summary_text():
    """Test de génération du résumé textuel."""
    service = MusicSummaryService()
    
    normalized = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
        {'tag': 'workout', 'score': 0.75, 'category': 'usage', 'source': 'calculated'},
    ]
    
    result = service.generate_summary_text(normalized, synthetic_tags)
    
    assert 'rock' in result.lower(), f"Genre rock manquant dans: {result}"
    assert len(result) > 0, "Résumé vide"
    
    print(f"✓ test_generate_summary_text: OK (summary: '{result[:50]}...')")


def test_generate_context():
    """Test de génération du contexte."""
    service = MusicSummaryService()
    
    normalized = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    scores = {
        'energy_score': 0.72,
        'valence': 0.45,
        'dance_score': 0.81,
        'acousticness': 0.15,
        'complexity_score': 0.68,
        'emotional_intensity': 0.7,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
    ]
    
    context = service.generate_context(
        track_id=1,
        normalized=normalized,
        scores=scores,
        synthetic_tags=synthetic_tags,
        source='acoustid+standards+librosa'
    )
    
    assert context['track_id'] == 1
    assert context['genre'] == 'rock'
    assert context['mood'] == 'happy'
    assert context['bpm'] == 128.0
    assert '8B' in context['key']
    assert 'energetic' in context['synthetic_tags']
    assert context['source'] == 'acoustid+standards+librosa'
    
    print("✓ test_generate_context: OK")


def test_generate_search_suggestions():
    """Test de génération des suggestions de recherche."""
    service = MusicSummaryService()
    
    normalized = {
        'bpm': 128.0,
        'genre_main': 'rock',
        'danceability': 0.8,
        'mood_happy': 0.7,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
        {'tag': 'workout', 'score': 0.75, 'category': 'usage', 'source': 'calculated'},
    ]
    
    suggestions = service.generate_search_suggestions(normalized, synthetic_tags)
    
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert len(suggestions) <= 10  # Limite à 10 suggestions
    
    print(f"✓ test_generate_search_suggestions: OK ({len(suggestions)} suggestions)")


def test_create_summary():
    """Test de création du résumé complet."""
    service = MusicSummaryService()
    
    raw_tags = ['ab:hi:genre_tzanetakis:rock', 'ab:mood:happy']
    
    normalized = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    scores = {
        'energy_score': 0.72,
        'valence': 0.45,
        'dance_score': 0.81,
        'acousticness': 0.15,
        'complexity_score': 0.68,
        'emotional_intensity': 0.7,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
        {'tag': 'workout', 'score': 0.75, 'category': 'usage', 'source': 'calculated'},
    ]
    
    summary = service.create_summary(
        track_id=1,
        raw_tags=raw_tags,
        source='acoustid+standards+librosa',
        normalized=normalized,
        scores=scores,
        synthetic_tags=synthetic_tags,
    )
    
    assert summary['track_id'] == 1
    assert summary['tags'] == raw_tags
    assert summary['source'] == 'acoustid+standards+librosa'
    assert summary['version'] == '1.0'
    assert summary['normalized']['bpm'] == 128.0
    assert summary['normalized']['genre_main'] == 'rock'
    assert summary['scores']['energy_score'] == 0.72
    assert len(summary['synthetic_tags']) == 3
    assert len(summary['search_suggestions']) > 0
    assert len(summary['summary']) > 0
    
    # Vérifier la structure attendue
    assert 'context' in summary
    assert summary['context']['bpm'] == 128.0
    
    print(f"✓ test_create_summary: OK (summary: '{summary['summary'][:50]}...')")


def test_extract_summary_for_api():
    """Test d'extraction du résumé pour l'API."""
    service = MusicSummaryService()
    
    raw_tags = ['ab:hi:genre_tzanetakis:rock', 'ab:mood:happy']
    
    normalized = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    scores = {
        'energy_score': 0.72,
        'valence': 0.45,
        'dance_score': 0.81,
        'acousticness': 0.15,
        'complexity_score': 0.68,
        'emotional_intensity': 0.7,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
    ]
    
    full_summary = service.create_summary(
        track_id=1,
        raw_tags=raw_tags,
        source='acoustid+standards+librosa',
        normalized=normalized,
        scores=scores,
        synthetic_tags=synthetic_tags,
    )
    
    api_summary = service.extract_summary_for_api(full_summary)
    
    assert 'track_id' in api_summary
    assert 'summary' in api_summary
    assert 'genre' in api_summary
    assert 'mood' in api_summary
    assert 'bpm' in api_summary
    assert 'energy_score' in api_summary
    assert 'synthetic_tags' in api_summary
    assert 'confidence_score' in api_summary
    
    print("✓ test_extract_summary_for_api: OK")


def test_compare_summaries():
    """Test de comparaison de deux tracks."""
    service = MusicSummaryService()
    
    # Track 1: rock énergétique
    normalized1 = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    scores1 = {
        'energy_score': 0.72,
        'valence': 0.45,
        'dance_score': 0.81,
        'acousticness': 0.15,
        'complexity_score': 0.68,
        'emotional_intensity': 0.7,
    }
    
    synthetic_tags1 = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
    ]
    
    summary1 = service.create_summary(
        track_id=1,
        raw_tags=['test'],
        source='test',
        normalized=normalized1,
        scores=scores1,
        synthetic_tags=synthetic_tags1,
    )
    
    # Track 2: rock similaire (BPM légèrement différent)
    normalized2 = normalized1.copy()
    normalized2['bpm'] = 130.0
    
    scores2 = scores1.copy()
    
    summary2 = service.create_summary(
        track_id=2,
        raw_tags=['test'],
        source='test',
        normalized=normalized2,
        scores=scores2,
        synthetic_tags=synthetic_tags1,
    )
    
    comparison = service.compare_summaries(summary1, summary2)
    
    assert 'similar_genre' in comparison
    assert 'similar_mood' in comparison
    assert 'bpm_difference' in comparison
    assert 'energy_difference' in comparison
    assert 'dance_difference' in comparison
    assert 'common_tags' in comparison
    assert 'compatibility_score' in comparison
    
    assert comparison['similar_genre'] is True
    assert comparison['bpm_difference'] == 2  # 2 BPM de différence
    
    print(f"✓ test_compare_summaries: OK (compatibility: {comparison['compatibility_score']:.2f})")


def test_summary_format():
    """Vérifie que le format correspond à la spécification attendue."""
    service = MusicSummaryService()
    
    normalized = {
        'bpm': 128.0,
        'key': 'C',
        'scale': 'major',
        'camelot_key': '8B',
        'danceability': 0.8,
        'mood_happy': 0.7,
        'mood_aggressive': 0.1,
        'mood_party': 0.6,
        'mood_relaxed': 0.3,
        'instrumental': 0.2,
        'acoustic': 0.1,
        'tonal': 0.9,
        'genre_main': 'rock',
        'genre_secondary': ['alternative', 'indie'],
        'confidence_score': 0.85,
    }
    
    scores = {
        'energy_score': 0.72,
        'valence': 0.45,
        'dance_score': 0.81,
        'acousticness': 0.15,
        'complexity_score': 0.68,
        'emotional_intensity': 0.7,
    }
    
    synthetic_tags = [
        {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
        {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
        {'tag': 'workout', 'score': 0.75, 'category': 'usage', 'source': 'calculated'},
    ]
    
    summary = service.create_summary(
        track_id=1,
        raw_tags=['ab:hi:genre_tzanetakis:rock', 'ab:mood:happy'],
        source='acoustid+standards+librosa',
        normalized=normalized,
        scores=scores,
        synthetic_tags=synthetic_tags,
    )
    
    # Vérifier la structure complète
    assert 'tags' in summary
    assert 'source' in summary
    assert 'version' in summary
    assert 'normalized' in summary
    assert 'scores' in summary
    assert 'synthetic_tags' in summary
    assert 'summary' in summary
    assert 'context' in summary
    assert 'search_suggestions' in summary
    
    # Vérifier les clés normalized
    assert summary['normalized']['bpm'] == 128.0
    assert summary['normalized']['key'] == 'C'
    assert summary['normalized']['camelot_key'] == '8B'
    assert summary['normalized']['danceability'] == 0.8
    assert summary['normalized']['genre_main'] == 'rock'
    assert summary['normalized']['confidence_score'] == 0.85
    
    # Vérifier les clés scores
    assert summary['scores']['energy_score'] == 0.72
    assert summary['scores']['dance_score'] == 0.81
    
    # Vérifier synthetic_tags
    assert len(summary['synthetic_tags']) == 3
    assert all('tag' in t and 'score' in t and 'category' in t for t in summary['synthetic_tags'])
    
    print("✓ test_summary_format: OK")


def main():
    """Exécute tous les tests."""
    print("=" * 60)
    print("Tests du MusicSummaryService")
    print("=" * 60)
    
    tests = [
        test_format_key_display,
        test_get_mood_from_features,
        test_get_energy_level,
        test_generate_summary_text,
        test_generate_context,
        test_generate_search_suggestions,
        test_create_summary,
        test_extract_summary_for_api,
        test_compare_summaries,
        test_summary_format,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: ERROR - {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Résultats: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
