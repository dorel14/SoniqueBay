#!/usr/bin/env python3
"""
Test de validation pour la correction du problème \"AUCUN champ audio trouvé\".
Ce script teste la nouvelle détection des tags audio (AcoustID + standards).
"""

import sys
import os

# Ajouter le backend_worker au path pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

from backend_worker.services.audio_features_service import (
    _has_valid_audio_tags,
    _extract_features_from_standard_tags,
    _extract_features_from_acoustid_tags
)


def test_acoustid_tags_detection():
    """Test la détection des tags AcoustID"""
    print("\n=== TEST DÉTECTION TAGS ACOUSTID ===")
    
    # Tags AcoustID valides
    acoustid_tags = {
        'ab:hi:bpm': ['120'],
        'ab:hi:key': ['C'],
        'ab:hi:danceability': ['danceable'],
        'TPE1': ['Test Artist'],
        'TIT2': ['Test Title']
    }
    
    result = _has_valid_audio_tags(acoustid_tags)
    print(f"Tags AcoustID détectés: {'✅ OUI' if result else '❌ NON'}")
    
    # Extraction des features
    features = _extract_features_from_acoustid_tags(acoustid_tags)
    print(f"Features extraites: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
    
    return result


def test_standard_tags_detection():
    """Test la détection des tags audio standards"""
    print("\n=== TEST DÉTECTION TAGS STANDARDS ===")
    
    # Tags audio standards
    standard_tags = {
        'BPM': ['128'],
        'TBPM': ['128'],
        'KEY': ['Am'],
        'TKEY': ['Am'],
        'MOOD': ['happy'],
        'TMOO': ['energetic'],
        'DANCEABILITY': ['0.8'],
        'ENERGY': ['0.9'],
        'TPE1': ['Test Artist'],
        'TIT2': ['Test Title']
    }
    
    result = _has_valid_audio_tags(standard_tags)
    print(f"Tags standards détectés: {'✅ OUI' if result else '❌ NON'}")
    
    # Extraction des features
    features = _extract_features_from_standard_tags(standard_tags)
    print(f"Features extraites: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
    
    return result


def test_mixed_tags_detection():
    """Test la détection avec un mélange de tags"""
    print("\n=== TEST DÉTECTION TAGS MIXTES ===")
    
    # Tags mixtes (AcoustID + standards)
    mixed_tags = {
        # Tags AcoustID
        'ab:hi:bpm': ['135'],
        # Tags standards
        'BPM': ['135'],
        'KEY': ['D'],
        'MOOD': ['party'],
        # Tags normaux
        'TPE1': ['Massive Attack'],
        'TIT2': ['Unfinished Sympathy'],
        'TALB': ['Singles 90_98']
    }
    
    result = _has_valid_audio_tags(mixed_tags)
    print(f"Tags mixtes détectés: {'✅ OUI' if result else '❌ NON'}")
    
    # Test d'extraction AcoustID d'abord
    acoustid_features = _extract_features_from_acoustid_tags(mixed_tags)
    print(f"Features AcoustID: {[(k, v) for k, v in acoustid_features.items() if v is not None and v != []]}")
    
    # Test d'extraction standards
    standard_features = _extract_features_from_standard_tags(mixed_tags)
    print(f"Features standards: {[(k, v) for k, v in standard_features.items() if v is not None and v != []]}")
    
    return result


def test_no_audio_tags():
    """Test avec aucun tag audio"""
    print("\n=== TEST AUCUN TAG AUDIO ===")
    
    # Tags sans informations audio
    no_audio_tags = {
        'TPE1': ['Test Artist'],
        'TIT2': ['Test Title'],
        'TALB': ['Test Album'],
        'TYER': ['2023']
    }
    
    result = _has_valid_audio_tags(no_audio_tags)
    print(f"Aucun tag audio détecté: {'✅ CORRECT' if not result else '❌ ERREUR'}")
    
    return not result


def main():
    """Fonction principale de test"""
    print("🔧 TEST DE VALIDATION - CORRECTION \"AUCUN CHAMP AUDIO TROUVÉ\"")
    print("=" * 70)
    
    tests = [
        ("Détection tags AcoustID", test_acoustid_tags_detection),
        ("Détection tags standards", test_standard_tags_detection),
        ("Détection tags mixtes", test_mixed_tags_detection),
        ("Aucun tag audio", test_no_audio_tags)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"Résultat: {'✅ PASS' if result else '❌ FAIL'}")
        except Exception as e:
            print(f"❌ ERREUR dans {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 TOUS LES TESTS SONT PASSÉS - La correction fonctionne!")
        print("\n📋 AMÉLIORATIONS APPORTÉES:")
        print("  • Détection étendue des tags audio (AcoustID + standards)")
        print("  • Logs détaillés pour le debugging")
        print("  • Support des tags BPM, KEY, MOOD, DANCEABILITY, etc.")
        print("  • Message d'erreur plus informatif")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ - Vérification nécessaire")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)