#!/usr/bin/env python3
"""
Script de test pour valider le diagnostic des erreurs 422.

Génère différents types d'erreurs de validation pour tester le système de logging.
"""

import asyncio
import aiohttp
import json
import sys


class ValidationErrorTester:
    """Testeur pour les erreurs de validation 422."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_track_batch_validation_error(self):
        """Test erreur 422 sur /api/tracks/batch avec données invalides."""
        print("\n🧪 Test: Track batch avec données invalides (422)")
        
        # Données invalides - champs obligatoires manquants
        invalid_data = [
            {
                # "title" manquant - champ obligatoire
                "path": "/music/test.mp3",
                "track_artist_id": "not_an_integer",  # Type incorrect
                "duration": 180,
                "invalid_field": "this_should_not_exist"
            },
            {
                "title": "",  # Titre vide
                "track_artist_id": -999,  # ID invalide
                "danceability": 2.0,  # Valeur > 1 (contrainte validée par ge=0, le=1)
                "mood_tags": "not_a_list"  # Devrait être une liste
            }
        ]
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/tracks/batch",
                json=invalid_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 422:
                    error_data = await response.json()
                    print("✅ Erreur 422 capturée comme prévu")
                    print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ Status inattendu: {response.status}")
                    print(f"Réponse: {await response.text()}")
        except Exception as e:
            print(f"Erreur requête: {e}")
    
    async def test_album_batch_validation_error(self):
        """Test erreur 422 sur /api/albums/batch avec données invalides."""
        print("\n🧪 Test: Album batch avec données invalides (422)")
        
        invalid_data = [
            {
                # "title" manquant - champ obligatoire
                "album_artist_id": "invalid_id",
                "release_year": 2024.5,  # Devrait être string
                "invalid_field": "test"
            },
            {
                "title": "",  # Titre vide
                "album_artist_id": 0,  # ID invalide (devrait être > 0)
            }
        ]
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/albums/batch",
                json=invalid_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 422:
                    error_data = await response.json()
                    print("✅ Erreur 422 capturée comme prévu")
                    print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ Status inattendu: {response.status}")
                    print(f"Réponse: {await response.text()}")
        except Exception as e:
            print(f"Erreur requête: {e}")
    
    async def test_single_track_creation_error(self):
        """Test erreur 422 sur création d'une track unique."""
        print("\n🧪 Test: Création track unique avec données invalides (422)")
        
        invalid_track = {
            # "title" manquant - champ obligatoire
            "path": "/music/single_test.mp3",
            "track_artist_id": "not_an_integer",
            "bpm": "not_a_number",
            "danceability": 5.0  # Valeur invalide (doit être entre 0 et 1)
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/tracks",
                json=invalid_track,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 422:
                    error_data = await response.json()
                    print("✅ Erreur 422 capturée comme prévu")
                    print(f"Erreur: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ Status inattendu: {response.status}")
                    print(f"Réponse: {await response.text()}")
        except Exception as e:
            print(f"Erreur requête: {e}")
    
    async def test_graphql_validation_errors(self):
        """Test erreurs de validation GraphQL via mutation."""
        print("\n🧪 Test: GraphQL mutation avec données invalides")
        
        graphql_query = {
            "query": """
            mutation CreateTracksBatch($data: [TrackCreateInput!]!) {
                createTracksBatchMassive(data: $data) {
                    success
                    tracksProcessed
                    message
                }
            }
            """,
            "variables": {
                "data": [
                    {
                        # Champs manquants/invalides
                        "title": "Test Track",
                        "path": "/music/test.mp3",
                        "trackArtistId": "not_an_integer",  # Type incorrect
                        "bpm": "invalid_bpm",
                        "danceability": 3.0  # Valeur > 1
                    }
                ]
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/graphql",
                json=graphql_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                response_data = await response.json()
                print(f"Réponse GraphQL: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
                
                if response_data.get("errors"):
                    print("✅ Erreurs GraphQL capturées")
                else:
                    print("❌ Pas d'erreurs GraphQL détectées")
                    
        except Exception as e:
            print(f"Erreur requête GraphQL: {e}")
    
    async def test_valid_data(self):
        """Test avec données valides pour s'assurer que le système fonctionne."""
        print("\n🧪 Test: Données valides (devrait réussir)")
        
        valid_track = {
            "title": "Test Track Valid",
            "path": "/music/valid_test.mp3",
            "track_artist_id": 1,
            "duration": 180,
            "bpm": 120,
            "danceability": 0.8,
            "year": "2024"
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/tracks",
                json=valid_track,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Status: {response.status}")
                if response.status in [200, 201]:
                    print("✅ Création réussie avec données valides")
                    data = await response.json()
                    print(f"Track créée: ID {data.get('id')}")
                else:
                    print(f"❌ Échec inattendu: {response.status}")
                    print(f"Réponse: {await response.text()}")
        except Exception as e:
            print(f"Erreur requête: {e}")
    
    async def run_all_tests(self):
        """Lance tous les tests de validation."""
        print("🚀 Démarrage des tests de validation 422")
        print("=" * 60)
        
        # Attendre que les services soient prêts
        await asyncio.sleep(2)
        
        # Test des erreurs de validation
        await self.test_track_batch_validation_error()
        await self.test_album_batch_validation_error()
        await self.test_single_track_creation_error()
        await self.test_graphql_validation_errors()
        
        # Test avec données valides
        await self.test_valid_data()
        
        print("\n" + "=" * 60)
        print("✅ Tests terminés. Vérifiez les logs pour les détails des erreurs 422.")
        print("📋 Fichiers de log à surveiller:")
        print("   - backend_worker/logs/soniquebay-*.log")
        print("   - stdout/stderr des conteneurs")
        print("   - Logs applicatifs dans les répertoires de logs")


async def main():
    """Point d'entrée principal."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    async with ValidationErrorTester(base_url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    print("🎵 SoniqueBay - Testeur d'erreurs de validation 422")
    print(f"URL de base: {sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'}")
    print("Usage: python scripts/test_422_errors.py [base_url]")
    print()
    
    asyncio.run(main())