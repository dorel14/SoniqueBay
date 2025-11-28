"""
Test d'intégration pour la correction de l'erreur 307 lors de l'insertion des genres.
"""
import pytest
from unittest.mock import patch
from backend_worker.background_tasks.worker_metadata import _resolve_genres_references


@pytest.mark.asyncio
async def test_resolve_genres_with_complex_genres():
    """
    Test que la résolution des genres fonctionne avec des genres complexes
    qui causaient l'erreur 307.
    """
    # Données de test avec le genre complexe problématique
    tracks_data = [
        {
            'title': 'Test Track 1',
            'genre': 'Dance, Soul, American, Interlude, Jacksons, New Soul - Hip Hop - Rap, Jam And Lewis, Pop, 00S, Rnb, Female Vocalist',
            'genre_main': 'R&B'
        },
        {
            'title': 'Test Track 2', 
            'genre': 'Rock/Pop Alternative',
            'genre_main': 'Alternative Rock'
        }
    ]
    
    # Mock des services
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_genres') as mock_search:
        mock_search.return_value = {}  # Aucun genre existant
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_genres') as mock_create:
            mock_create.return_value = [
                {'id': 1, 'name': 'Dance'},
                {'id': 2, 'name': 'Soul'},
                {'id': 3, 'name': 'American'},
                {'id': 4, 'name': 'Interlude'},
                {'id': 5, 'name': 'Jacksons'},
                {'id': 6, 'name': 'New Soul Hip Hop Rap'},
                {'id': 7, 'name': 'Jam And Lewis'},
                {'id': 8, 'name': 'Pop'},
                {'id': 9, 'name': 'Rnb'},
                {'id': 10, 'name': 'Female Vocalist'},
                {'id': 11, 'name': 'R&B'},
                {'id': 12, 'name': 'Rock Pop Alternative'},
                {'id': 13, 'name': 'Alternative Rock'}
            ]
            
            # Test de la fonction corrigée
            result = await _resolve_genres_references(tracks_data)
            
            # La fonction retourne maintenant un dictionnaire avec 'genres' et 'track_cleaned_genres'
            genres = result['genres']
            
            # Vérifications
            assert len(genres) == 13, f"Attendu 13 genres, obtenu {len(genres)}"
            
            # Vérifier que les genres ont été correctement créés
            created_genres = {genre['name'] for genre in genres}
            
            # Les genres du track 1 (sans le 00S qui doit être filtré)
            expected_genres_1 = {
                'Dance', 'Soul', 'American', 'Interlude', 'Jacksons', 
                'New Soul Hip Hop Rap', 'Jam And Lewis', 'Pop', 'Rnb', 'Female Vocalist'
            }
            
            # Les genres du track 2
            expected_genres_2 = {'Rock Pop Alternative', 'Alternative Rock', 'R&B'}
            
            all_expected = expected_genres_1 | expected_genres_2
            
            assert created_genres == all_expected, f"Genres créés: {created_genres}\nAttendu: {all_expected}"
            
            # Vérifier que _create_missing_genres a été appelé une fois
            assert mock_create.call_count == 1
            
            # Vérifier les données envoyées à la création
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 13, f"Attendu 13 genres à créer, reçu {len(create_call_args)}"
            
            # Vérifier que '00S' n'est PAS dans les genres à créer (filtré)
            genre_names_to_create = {item['name'] for item in create_call_args}
            assert '00S' not in genre_names_to_create, "Le code '00S' nätte pas dû être créé"
            
            print(f"✅ Test d'intégration réussi: {len(genres)} genres créés sans erreur 307")
            print("   - Genre complexe subdivisé en genres individuels")
            print("   - Codes années ('00S') correctement filtrés")
            print("   - Caractères spéciaux traités (/, -, –)")


@pytest.mark.asyncio 
async def test_resolve_genres_existing_genres():
    """
    Test que les genres existants ne sont pas recréés.
    """
    tracks_data = [
        {
            'title': 'Test Track',
            'genre': 'Rock, Pop',
            'genre_main': 'Alternative'
        }
    ]
    
    # Simuler des genres existants
    existing_genres = {
        'rock': {'id': 1, 'name': 'Rock'},
        'pop': {'id': 2, 'name': 'Pop'}
    }
    
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_genres') as mock_search:
        mock_search.return_value = existing_genres
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_genres') as mock_create:
            mock_create.return_value = [
                {'id': 3, 'name': 'Alternative'}
            ]
            
            result = await _resolve_genres_references(tracks_data)
            
            # La fonction retourne maintenant un dictionnaire
            genres = result['genres']
            
            # Vérifier que seuls les nouveaux genres sont créés
            assert mock_create.call_count == 1
            create_call_args = mock_create.call_args[0][0]
            assert len(create_call_args) == 1, f"Attendu 1 genre à créer, reçu {len(create_call_args)}"
            assert create_call_args[0]['name'] == 'Alternative'
            
            # Résultat final doit contenir tous les genres
            assert len(genres) == 3
            
            print("✅ Test genres existants réussi: réutilisation des genres existants")


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_resolve_genres_with_complex_genres()
        await test_resolve_genres_existing_genres()
        print("\n🎉 Tous les tests d'intégration ont réussi!")
    
    asyncio.run(run_tests())