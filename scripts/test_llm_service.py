"""
Script de test pour vérifier le service LLM unifié (Ollama/KoboldCPP).
Auteur: SoniqueBay Team
"""
import asyncio
import os
import sys

# Ajouter le backend au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.api.services.llm_service import LLMService, llm_service


def test_health_check():
    """Teste la vérification de santé du service LLM."""
    print("\n=== Test Health Check ===")
    health = llm_service.health_check()
    print(f"Statut: {health['status']}")
    print(f"Fournisseur: {health['provider']}")
    print(f"URL: {health['base_url']}")
    if 'error' in health:
        print(f"Erreur: {health['error']}")
    return health['status'] == 'healthy'


def test_model_list():
    """Teste la récupération de la liste des modèles."""
    print("\n=== Test Liste des Modèles ===")
    models = llm_service.get_model_list()
    print(f"Nombre de modèles: {len(models.get('models', []))}")
    for model in models.get('models', [])[:3]:  # Afficher les 3 premiers
        print(f"  - {model.get('name', 'N/A')}")
    return len(models.get('models', [])) > 0


async def test_chat_response():
    """Teste la génération d'une réponse de chat."""
    print("\n=== Test Réponse Chat ===")
    try:
        messages = [
            {"role": "system", "content": "Tu es un assistant musical. Sois concis."},
            {"role": "user", "content": "Bonjour, peux-tu me recommander de la musique ?"}
        ]
        
        response = await llm_service.generate_chat_response(
            messages=messages,
            temperature=0.7,
            max_tokens=256,
            stream=False
        )
        
        print(f"Réponse: {response.get('content', 'Pas de réponse')[:100]}...")
        print(f"Modèle utilisé: {response.get('model', 'N/A')}")
        return bool(response.get('content'))
        
    except Exception as e:
        print(f"Erreur: {e}")
        return False


def test_provider_detection():
    """Teste la détection automatique du fournisseur."""
    print("\n=== Test Détection Fournisseur ===")
    service = LLMService(provider_type='auto')
    print(f"Fournisseur détecté: {service.provider_type}")
    print(f"URL: {service.base_url}")
    return service.provider_type in ['koboldcpp', 'ollama']


async def main():
    """Fonction principale de test."""
    print("=" * 60)
    print("Test du Service LLM Unifié (Ollama/KoboldCPP)")
    print("=" * 60)
    
    results = []
    
    # Test 1: Détection du fournisseur
    results.append(("Détection Fournisseur", test_provider_detection()))
    
    # Test 2: Health check
    results.append(("Health Check", test_health_check()))
    
    # Test 3: Liste des modèles
    results.append(("Liste Modèles", test_model_list()))
    
    # Test 4: Réponse chat
    results.append(("Réponse Chat", await test_chat_response()))
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    print(f"\nTotal: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests ont réussi ! Le service LLM est correctement configuré.")
        return 0
    else:
        print("\n⚠️  Certains tests ont échoué. Vérifiez la configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

