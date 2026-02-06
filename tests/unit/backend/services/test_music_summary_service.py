"""Tests unitaires pour MusicSummaryService.

Ces tests vérifient le bon fonctionnement du service de résumé musical
et de ses différentes méthodes de génération de résumés, contextes et suggestions.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import pytest
from backend_worker.services.music_summary_service import MusicSummaryService


class TestMusicSummaryService:
    """Tests pour MusicSummaryService."""
    
    @pytest.fixture
    def service(self) -> MusicSummaryService:
        """Fixture pour créer une instance du service."""
        return MusicSummaryService()
    
    @pytest.fixture
    def sample_normalized(self) -> dict:
        """Données normalisées typiques pour un track rock énergétique."""
        return {
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
    
    @pytest.fixture
    def sample_scores(self) -> dict:
        """Scores calculés typiques."""
        return {
            'energy_score': 0.72,
            'valence': 0.45,
            'dance_score': 0.81,
            'acousticness': 0.15,
            'complexity_score': 0.68,
            'emotional_intensity': 0.7,
        }
    
    @pytest.fixture
    def sample_synthetic_tags(self) -> list[dict]:
        """Tags synthétiques générés."""
        return [
            {'tag': 'energetic', 'score': 0.8, 'category': 'mood', 'source': 'calculated'},
            {'tag': 'dancefloor', 'score': 0.85, 'category': 'atmosphere', 'source': 'calculated'},
            {'tag': 'workout', 'score': 0.75, 'category': 'usage', 'source': 'calculated'},
        ]
    
    @pytest.fixture
    def sample_raw_tags(self) -> list[str]:
        """Tags bruts sources."""
        return ['ab:hi:genre_tzanetakis:rock', 'ab:mood:happy']
    
    def test_format_key_display_major(self, service: MusicSummaryService) -> None:
        """Test de formatage de la clé majeure."""
        result = service._format_key_display('C', 'major', '8B')
        assert 'C' in result
        assert 'Major' in result
        assert '8B' in result
    
    def test_format_key_display_minor(self, service: MusicSummaryService) -> None:
        """Test de formatage de la clé mineure."""
        result = service._format_key_display('Am', 'minor', '5Am')
        assert 'AM' in result or 'Am' in result
        assert 'Minor' in result
    
    def test_format_key_display_partial(self, service: MusicSummaryService) -> None:
        """Test de formatage avec données partielles."""
        result = service._format_key_display('C', None, None)
        assert 'C' in result
        assert 'Inconnue' not in result
    
    def test_format_key_display_empty(self, service: MusicSummaryService) -> None:
        """Test de formatage avec données vides."""
        result = service._format_key_display(None, None, None)
        assert 'Inconnue' in result
    
    def test_get_mood_from_features_happy(self, service: MusicSummaryService) -> None:
        """Test de détection du mood happy."""
        features = {'mood_happy': 0.7, 'mood_aggressive': 0.1}
        result = service._get_mood_from_features(features)
        assert result == 'happy'
    
    def test_get_mood_from_features_party(self, service: MusicSummaryService) -> None:
        """Test de détection du mood party (le plus élevé)."""
        features = {'mood_happy': 0.3, 'mood_aggressive': 0.2, 'mood_party': 0.6}
        result = service._get_mood_from_features(features)
        assert result == 'party'
    
    def test_get_mood_from_features_low_score(self, service: MusicSummaryService) -> None:
        """Test de détection du mood avec scores trop bas."""
        features = {'mood_happy': 0.2, 'mood_aggressive': 0.1}
        result = service._get_mood_from_features(features)
        assert result is None
    
    def test_get_energy_level_high(self, service: MusicSummaryService) -> None:
        """Test de détection du niveau d'énergie élevé."""
        result = service._get_energy_level(0.8)
        assert result == 'high'
    
    def test_get_energy_level_low(self, service: MusicSummaryService) -> None:
        """Test de détection du niveau d'énergie bas."""
        result = service._get_energy_level(0.2)
        assert result == 'low'
    
    def test_get_energy_level_medium(self, service: MusicSummaryService) -> None:
        """Test de détection du niveau d'énergie moyen."""
        result = service._get_energy_level(0.5)
        assert result == 'medium'
    
    def test_get_energy_level_none(self, service: MusicSummaryService) -> None:
        """Test de détection du niveau d'énergie avec valeur None."""
        result = service._get_energy_level(None)
        assert result is None
    
    def test_generate_summary_text_rock(
        self, 
        service: MusicSummaryService,
        sample_normalized: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de génération du résumé textuel pour un track rock."""
        result = service.generate_summary_text(sample_normalized, sample_synthetic_tags)
        
        assert 'rock' in result.lower()
        assert len(result) > 0
    
    def test_generate_summary_text_empty(
        self,
        service: MusicSummaryService
    ) -> None:
        """Test de génération du résumé avec des données vides."""
        result = service.generate_summary_text({}, [])
        assert result == "un titre musical"
    
    def test_generate_context(
        self,
        service: MusicSummaryService,
        sample_normalized: dict,
        sample_scores: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de génération du contexte musical."""
        context = service.generate_context(
            track_id=1,
            normalized=sample_normalized,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
            source='acoustid+standards+librosa'
        )
        
        assert context['track_id'] == 1
        assert context['genre'] == 'rock'
        assert context['mood'] == 'happy'
        assert context['bpm'] == 128.0
        assert '8B' in context['key']
        assert 'energetic' in context['synthetic_tags']
        assert context['source'] == 'acoustid+standards+librosa'
    
    def test_generate_search_suggestions(
        self,
        service: MusicSummaryService,
        sample_normalized: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de génération des suggestions de recherche."""
        suggestions = service.generate_search_suggestions(
            sample_normalized, 
            sample_synthetic_tags
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert len(suggestions) <= 10  # Limite à 10 suggestions
    
    def test_generate_search_suggestions_empty(
        self,
        service: MusicSummaryService
    ) -> None:
        """Test de génération des suggestions avec données vides."""
        suggestions = service.generate_search_suggestions({}, [])
        assert isinstance(suggestions, list)
        assert len(suggestions) == 0
    
    def test_create_summary(
        self,
        service: MusicSummaryService,
        sample_raw_tags: list[str],
        sample_normalized: dict,
        sample_scores: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de création du résumé complet."""
        summary = service.create_summary(
            track_id=1,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=sample_normalized,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
        )
        
        assert summary['track_id'] == 1
        assert summary['tags'] == sample_raw_tags
        assert summary['source'] == 'acoustid+standards+librosa'
        assert summary['version'] == '1.0'
        assert summary['normalized']['bpm'] == 128.0
        assert summary['normalized']['genre_main'] == 'rock'
        assert summary['scores']['energy_score'] == 0.72
        assert len(summary['synthetic_tags']) == 3
        assert len(summary['search_suggestions']) > 0
        assert len(summary['summary']) > 0
    
    def test_extract_summary_for_api(
        self,
        service: MusicSummaryService,
        sample_raw_tags: list[str],
        sample_normalized: dict,
        sample_scores: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test d'extraction du résumé pour l'API."""
        full_summary = service.create_summary(
            track_id=1,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=sample_normalized,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
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
    
    def test_compare_summaries_similar(
        self,
        service: MusicSummaryService,
        sample_raw_tags: list[str],
        sample_normalized: dict,
        sample_scores: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de comparaison de deux tracks similaires."""
        summary1 = service.create_summary(
            track_id=1,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=sample_normalized,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
        )
        
        # Créer un deuxième résumé similaire
        normalized2 = sample_normalized.copy()
        normalized2['bpm'] = 130.0  # BPM légèrement différent
        
        scores2 = sample_scores.copy()
        
        summary2 = service.create_summary(
            track_id=2,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=normalized2,
            scores=scores2,
            synthetic_tags=sample_synthetic_tags,
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
        assert comparison['bpm_difference'] < 10  # 2 BPM de différence
        assert comparison['compatibility_score'] > 0.5
    
    def test_compare_summaries_different(
        self,
        service: MusicSummaryService,
        sample_raw_tags: list[str],
        sample_normalized: dict,
        sample_scores: dict,
        sample_synthetic_tags: list[dict]
    ) -> None:
        """Test de comparaison de deux tracks différents."""
        summary1 = service.create_summary(
            track_id=1,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=sample_normalized,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
        )
        
        # Créer un deuxième résumé différent
        normalized2 = sample_normalized.copy()
        normalized2['genre_main'] = 'jazz'
        normalized2['mood_happy'] = 0.1
        
        summary2 = service.create_summary(
            track_id=2,
            raw_tags=sample_raw_tags,
            source='acoustid+standards+librosa',
            normalized=normalized2,
            scores=sample_scores,
            synthetic_tags=sample_synthetic_tags,
        )
        
        comparison = service.compare_summaries(summary1, summary2)
        
        assert comparison['similar_genre'] is False
        assert comparison['compatibility_score'] < 0.5


class TestMusicSummaryServiceEdgeCases:
    """Tests pour les cas limites du MusicSummaryService."""
    
    @pytest.fixture
    def service(self) -> MusicSummaryService:
        """Fixture pour créer une instance du service."""
        return MusicSummaryService()
    
    def test_summary_with_minimal_data(self, service: MusicSummaryService) -> None:
        """Test de résumé avec des données minimales."""
        normalized = {'bpm': 120.0}
        scores = {}
        synthetic_tags = []
        
        summary = service.create_summary(
            track_id=1,
            raw_tags=['test'],
            source='test',
            normalized=normalized,
            scores=scores,
            synthetic_tags=synthetic_tags,
        )
        
        assert summary['track_id'] == 1
        assert summary['normalized']['bpm'] == 120.0
        assert summary['summary'] is not None
    
    def test_summary_with_none_values(self, service: MusicSummaryService) -> None:
        """Test de résumé avec des valeurs None."""
        normalized = {
            'bpm': None,
            'key': None,
            'scale': None,
            'camelot_key': None,
            'danceability': None,
            'mood_happy': None,
            'mood_aggressive': None,
            'mood_party': None,
            'mood_relaxed': None,
            'instrumental': None,
            'acoustic': None,
            'tonal': None,
            'genre_main': None,
            'genre_secondary': [],
            'confidence_score': 0.0,
        }
        scores = {
            'energy_score': None,
            'valence': None,
            'dance_score': None,
            'acousticness': None,
            'complexity_score': None,
            'emotional_intensity': None,
        }
        synthetic_tags = []
        
        summary = service.create_summary(
            track_id=1,
            raw_tags=[],
            source='test',
            normalized=normalized,
            scores=scores,
            synthetic_tags=synthetic_tags,
        )
        
        assert summary['track_id'] == 1
        assert summary['summary'] is not None
        assert len(summary['search_suggestions']) == 0
    
    def test_compare_summaries_empty(self, service: MusicSummaryService) -> None:
        """Test de comparaison avec des résumés vides."""
        summary1 = {
            'track_id': 1,
            'normalized': {'bpm': None, 'genre_main': None},
            'context': {'mood': None},
            'scores': {},
            'synthetic_tags': [],
        }
        summary2 = {
            'track_id': 2,
            'normalized': {'bpm': None, 'genre_main': None},
            'context': {'mood': None},
            'scores': {},
            'synthetic_tags': [],
        }
        
        comparison = service.compare_summaries(summary1, summary2)
        
        assert 'compatibility_score' in comparison
        assert comparison['compatibility_score'] >= 0.0
