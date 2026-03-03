# -*- coding: utf-8 -*-
"""Script de test pour les services MIR."""

import sys
sys.path.insert(0, '.')

from backend.api.services.genre_taxonomy_service import GenreTaxonomyService
from backend.api.services.synthetic_tags_service import SyntheticTagsService

def test_genre_taxonomy_service():
    """Test GenreTaxonomyService."""
    print('=== Test GenreTaxonomyService ===')
    service = GenreTaxonomyService()
    
    # Test avec tags mixtes
    result = service.extract_genres_from_tags({
        'tags': ['ab:hi:genre_tzanetakis:rock', 'genre:pop']
    })
    print(f'Extract: {result}')
    
    assert 'pop' in result['standards'], f"Expected 'pop' in standards, got: {result['standards']}"
    assert 'rock' in result['gtzan'], f"Expected 'rock' in gtzan, got: {result['gtzan']}"
    print('✓ Tags extraits correctement!')
    
    # Test vote principal
    main_genre, conf = service.vote_genre_main(result)
    print(f'Main genre: {main_genre}, confidence: {conf}')
    assert main_genre == 'rock', f"Expected 'rock', got '{main_genre}'"
    print('✓ Vote principal fonctionne!')
    
    # Test complet avec plusieurs taxonomies
    result2 = service.extract_genres_from_tags({
        'tags': [
            'ab:hi:genre_tzanetakis:rock',
            'ab:hi:genre_tzanetakis:jazz', 
            'ab:hi:genre_rosamerica:pop',
            'genre:rock'
        ]
    })
    print(f'Result complet: {result2}')
    
    main, conf2 = service.vote_genre_main(result2)
    print(f'Main: {main}, conf: {conf2}')
    print('✓ Test complet réussi!')
    
    return True

def test_synthetic_tags_service():
    """Test SyntheticTagsService."""
    print('\n=== Test SyntheticTagsService ===')
    service = SyntheticTagsService()
    
    # Test mood tags
    mood_tags = service.generate_mood_tags(
        {'mood_aggressive': 0.3},
        {'mood_valence': 0.8}
    )
    print(f'Mood tags: {mood_tags}')
    assert any(t['tag'] == 'bright' for t in mood_tags)
    print('✓ Mood tags fonctionnent!')
    
    # Test energy tags
    energy_tags = service.generate_energy_tags(
        {},
        {'energy_score': 0.85}
    )
    print(f'Energy tags: {energy_tags}')
    assert any(t['tag'] == 'high_energy' for t in energy_tags)
    print('✓ Energy tags fonctionnent!')
    
    # Test complet
    all_tags = service.generate_all_tags(
        {
            'acoustic': 0.3,
            'mood_aggressive': 0.7,
            'mood_party': 0.7,
        },
        {
            'energy_score': 0.8,
            'mood_valence': 0.6,
            'dance_score': 0.85,
            'acousticness': 0.4,
        }
    )
    print(f'All tags: {all_tags}')
    assert len(all_tags) > 0
    print('✓ Tous les tags fonctionnent!')
    
    return True

if __name__ == '__main__':
    try:
        test_genre_taxonomy_service()
        test_synthetic_tags_service()
        print('\n=== Tous les tests passent! ===')
    except Exception as e:
        print(f'\n❌ Erreur: {e}')
        sys.exit(1)
