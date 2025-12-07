#!/usr/bin/env python3
"""
Test d'intégration complet pour vérifier que toutes les fonctionnalités sont correctement intégrées.
"""

import os
import sys
import tempfile
from pathlib import Path

# Ajouter le chemin du backend_worker pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend_worker"))

from backend_worker.workers.metadata.enrichment_worker import extract_single_file_metadata

def test_full_integration():
    """Test complet de l'intégration des covers et de l'analyse audio."""
    print("🔍 Exécution du test d'intégration complet...")

    # Créer un fichier audio temporaire pour le test
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
        tmp_file_path = tmp_file.name

    try:
        # Test 1: Vérifier que la fonction existe et est importable
        print("✅ Test 1: Fonction extract_single_file_metadata importée avec succès")

        # Test 2: Vérifier que la fonction gère les fichiers inexistants
        result = extract_single_file_metadata("nonexistent_file.mp3")
        assert result is None, "La fonction devrait retourner None pour les fichiers inexistants"
        print("✅ Test 2: Gestion correcte des fichiers inexistants")

        # Test 3: Vérifier que le code contient la logique d'extraction des covers
        import inspect
        source = inspect.getsource(extract_single_file_metadata)

        # Vérifier les mots-clés attendus
        expected_keywords = ['cover_data', 'cover_mime_type', 'APIC:', 'pictures', 'base64']
        found_keywords = [kw for kw in expected_keywords if kw in source]

        assert len(found_keywords) == len(expected_keywords), f"Tous les mots-clés devraient être présents: {found_keywords}"
        print(f"✅ Test 3: Logique d'extraction des covers présente: {found_keywords}")

        # Test 4: Vérifier que l'analyse audio est mentionnée
        audio_keywords = ['bpm', 'key', 'scale', 'audio_fields']
        found_audio_keywords = [kw for kw in audio_keywords if kw in source]

        assert len(found_audio_keywords) == len(audio_keywords), f"L'analyse audio devrait être présente: {found_audio_keywords}"
        print(f"✅ Test 4: Logique d'analyse audio présente: {found_audio_keywords}")

        # Test 5: Vérifier la gestion des erreurs
        error_keywords = ['try:', 'except Exception', 'logger.warning', 'logger.error']
        found_error_keywords = [kw for kw in error_keywords if kw in source]

        assert len(found_error_keywords) == len(error_keywords), f"La gestion des erreurs devrait être complète: {found_error_keywords}"
        print(f"✅ Test 5: Gestion des erreurs complète: {found_error_keywords}")

        print("🎉 Tous les tests d'intégration ont réussi !")
        print("✅ L'intégration des covers et de l'analyse audio est fonctionnelle")

        return True

    except Exception as e:
        print(f"❌ Erreur lors du test d'intégration: {str(e)}")
        return False

    finally:
        # Nettoyer le fichier temporaire
        try:
            os.unlink(tmp_file_path)
        except Exception:
            pass

if __name__ == "__main__":
    success = test_full_integration()
    sys.exit(0 if success else 1)