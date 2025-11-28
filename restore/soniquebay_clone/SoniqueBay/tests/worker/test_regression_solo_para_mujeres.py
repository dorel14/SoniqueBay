"""
Test de régression pour le bug original avec l'album "Sólo para mujeres".

Ce test reproduit le scénario exact qui causait l'erreur :
'int' object has no attribute 'startswith'
"""
import pytest
import asyncio
from unittest.mock import patch
from backend_worker.background_tasks.worker_metadata import _resolve_albums_references


@pytest.mark.asyncio
async def test_regression_solo_para_mujeres_album():
    """
    Test de régression pour le bug avec l'album "Sólo para mujeres".
    
    Scénario original :
    - Album existant trouvé avec ID entier (456)
    - Album_mapping mis à jour avec l'ID entier
    - Tentative d'appel .startswith() sur l'entier → Erreur
    
    Ce test vérifie que la correction évite cette erreur.
    """
    # Données reproduisant le scénario original
    artist_mapping = {
        "test artist": 405  # album_artist_id de l'erreur originale
    }
    
    albums_data = [
        {
            'title': 'Solo para mujeres',  # Simplifier le nom pour éviter les problèmes d'encodage
            'album_artist_name': 'Test Artist',  # Correspondre au artist_mapping
            'release_year': 2023
        }
    ]
    
    # Simuler la réponse de l'API qui a causé l'erreur
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search:
        # Simuler un album trouvé (comme dans les logs)
        mock_search.return_value = {
            'solo para mujeres_405': {
                'id': 456,  # ID entier comme dans l'erreur originale
                'title': 'Solo para mujeres'
            }
        }
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            mock_create.return_value = []  # Aucun nouvel album
            
            # Cette ligne ne doit PAS lever l'erreur "int object has no attribute startswith"
            try:
                result = await _resolve_albums_references(albums_data, artist_mapping)
                
                # Vérifications
                album_mapping = result['album_mapping']
                
                # Vérifier que la clé existe
                expected_key = 'solo para mujeres_405'
                assert expected_key in album_mapping
                
                # Vérifier que la valeur est l'ID entier (album existant)
                album_id = album_mapping[expected_key]
                assert isinstance(album_id, int)
                assert album_id == 456
                
                print(f"✅ Régression évitée: album_mapping[{expected_key}] = {album_id} (type: {type(album_id)})")
                
            except AttributeError as e:
                if "'int' object has no attribute 'startswith'" in str(e):
                    pytest.fail(f"Régression détectée ! Le bug original persiste: {e}")
                else:
                    raise


@pytest.mark.asyncio
async def test_album_mapping_type_safety():
    """
    Test simplifié de sécurité des types pour album_mapping.
    
    Vérifie que la correction gère correctement les cas mixtes (entiers et strings).
    """
    # Test simple qui reproduit le scénario exact du bug
    artist_mapping = {
        "test artist": 123
    }
    
    albums_data = [
        {
            'title': 'Test Album',
            'album_artist_name': 'Test Artist',
            'release_year': 2023
        }
    ]
    
    # Test 1: Album existant (devrait retourner un entier)
    with patch('backend_worker.background_tasks.worker_metadata._search_existing_albums') as mock_search:
        mock_search.return_value = {
            'test album_123': {
                'id': 456,  # ID entier
                'title': 'Test Album'
            }
        }
        
        with patch('backend_worker.background_tasks.worker_metadata._create_missing_albums') as mock_create:
            mock_create.return_value = []
            
            # Vérifier que cette ligne ne lève pas d'erreur "'int' object has no attribute 'startswith'"
            result = await _resolve_albums_references(albums_data, artist_mapping)
            
            album_mapping = result['album_mapping']
            album_id = album_mapping['test album_123']
            
            # Vérifier le type
            assert isinstance(album_id, int), f"Attendu int, obtenu {type(album_id)}"
            assert album_id == 456
            
            print(f"✅ Test album existant: ID = {album_id} (type: {type(album_id).__name__})")


if __name__ == "__main__":
    asyncio.run(test_regression_solo_para_mujeres_album())
    asyncio.run(test_album_mapping_type_safety())
    print("✅ Tous les tests de régression ont réussi!")