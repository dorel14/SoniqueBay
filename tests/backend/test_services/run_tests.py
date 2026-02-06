# -*- coding: utf-8 -*-
"""
Script de test standalone pour MIRNormalizationService.
Ce script peut être exécuté directement avec Python sans dépendre de pytest.
"""
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))

from backend.api.services.mir_normalization_service import MIRNormalizationService

def run_tests():
    """Exécute tous les tests du service MIRNormalizationService."""
    service = MIRNormalizationService()
    passed = 0
    failed = 0

    def test(name, condition):
        nonlocal passed, failed
        if condition:
            print(f"✓ {name}: OK")
            passed += 1
        else:
            print(f"✗ {name}: FAIL")
            failed += 1

    # === Tests normalize_binary_to_continuous ===
    test("True retourne 1.0", service.normalize_binary_to_continuous(True) == 1.0)
    test("False retourne 0.0", service.normalize_binary_to_continuous(False) == 0.0)
    test("'yes' retourne 1.0", service.normalize_binary_to_continuous("yes") == 1.0)
    test("'no' retourne 0.0", service.normalize_binary_to_continuous("no") == 0.0)
    test("'true' retourne 1.0", service.normalize_binary_to_continuous("true") == 1.0)
    test("'false' retourne 0.0", service.normalize_binary_to_continuous("false") == 0.0)
    test("'1' retourne 1.0", service.normalize_binary_to_continuous("1") == 1.0)
    test("'0' retourne 0.0", service.normalize_binary_to_continuous("0") == 0.0)
    test("'danceable' retourne 1.0", service.normalize_binary_to_continuous("danceable") == 1.0)
    test("'acoustic' retourne 1.0", service.normalize_binary_to_continuous("acoustic") == 1.0)

    # Test ValueError pour valeur invalide
    try:
        service.normalize_binary_to_continuous("invalid")
        test("Valeur invalide lève ValueError", False)
    except ValueError:
        test("Valeur invalide lève ValueError", True)

    # Test confiance
    test("Confiance appliquée", service.normalize_binary_to_continuous(True, confidence=0.8) == 0.8)

    # === Tests handle_opposing_tags ===
    net, conf = service.handle_opposing_tags(0.8, 0.3)
    test("Opposing tags: net=0.5, conf=0.5", net == 0.5 and conf == 0.5)

    net, conf = service.handle_opposing_tags(0.2, 0.7)
    test("Opposing tags négatif: net=0.0", net == 0.0)

    net, conf = service.handle_opposing_tags(0.5, 0.5)
    test("Opposing tags égaux: net=0.0", net == 0.0)

    net, conf = service.handle_opposing_tags(1.0, 0.0)
    test("Opposing tags max: net=1.0, conf=1.0", net == 1.0 and conf == 1.0)

    # === Tests normalize_bpm ===
    test("BPM 60 retourne 0.0", service.normalize_bpm(60) == 0.0)
    test("BPM 200 retourne 1.0", service.normalize_bpm(200) == 1.0)
    test("BPM 130 retourne 0.5", service.normalize_bpm(130) == 0.5)
    test("BPM < 60 retourne 0.0", service.normalize_bpm(50) == 0.0)
    test("BPM > 200 retourne 1.0", service.normalize_bpm(220) == 1.0)
    test("BPM None retourne 0.5", service.normalize_bpm(None) == 0.5)

    # Test ValueError pour BPM invalide
    try:
        service.normalize_bpm(0)
        test("BPM 0 lève ValueError", False)
    except ValueError:
        test("BPM 0 lève ValueError", True)

    try:
        service.normalize_bpm(-10)
        test("BPM négatif lève ValueError", False)
    except ValueError:
        test("BPM négatif lève ValueError", True)

    # === Tests normalize_key_scale ===
    key, scale, camelot = service.normalize_key_scale("C", "major")
    test("C major: key=C, scale=major, camelot=8B",
         key == "C" and scale == "major" and camelot == "8B")

    key, scale, camelot = service.normalize_key_scale("A", "minor")
    test("A minor: key=A, scale=minor, camelot=8A",
         key == "A" and scale == "minor" and camelot == "8A")

    key, scale, camelot = service.normalize_key_scale("G", "major")
    test("G major: key=G, scale=major, camelot=9B",
         key == "G" and scale == "major" and camelot == "9B")

    key, scale, camelot = service.normalize_key_scale("E", "minor")
    test("E minor: key=E, scale=minor, camelot=9A",
         key == "E" and scale == "minor" and camelot == "9A")

    key, scale, camelot = service.normalize_key_scale("Db", "major")
    test("Db major: key=C#, scale=major, camelot=3B",
         key == "C#" and scale == "major" and camelot == "3B")

    key, scale, camelot = service.normalize_key_scale("Bb", "major")
    test("Bb major: key=A#, scale=major, camelot=6B",
         key == "A#" and scale == "major" and camelot == "6B")

    key, scale, camelot = service.normalize_key_scale("Xyz")
    test("Unknown key: key=Xyz, camelot=Unknown",
         key == "Xyz" and camelot == "Unknown")

    try:
        service.normalize_key_scale("")
        test("Clé vide lève ValueError", False)
    except ValueError:
        test("Clé vide lève ValueError", True)

    # === Tests calculate_confidence_score ===
    # Features vides retourne 0.5 (confiance par défaut quand pas de facteurs)
    result = service.calculate_confidence_score({})
    test("Confiance features vides", result == 0.5)

    # Test avec source_consensus (clé valide)
    result = service.calculate_confidence_score({'source_consensus': 0.8})
    test("Haute confiance: > 0.5", result > 0.5)

    # Test avec facteur bas
    result = service.calculate_confidence_score({'source_consensus': 0.2})
    test("Confiance avec facteur bas", result < 0.5)

    # === Tests normalize_acoustid_tags ===
    result = service.normalize_acoustid_tags({'danceable': True})
    test("AcoustID danceable=True", result.get('danceability', 0.0) == 1.0)

    result = service.normalize_acoustid_tags({'acoustic': True})
    test("AcoustID acoustic=True", result.get('acoustic', 0.0) == 1.0)

    result = service.normalize_acoustid_tags({'mood_happy': True, 'not_happy': False})
    test("AcoustID happy vs not_happy", result.get('mood_happy', 0) > 0.5)

    result = service.normalize_acoustid_tags({'aggressive': True, 'not_aggressive': True})
    test("AcoustID aggressive vs not_aggressive (égaux)", result.get('aggressive', 0.0) == 0.0)

    result = service.normalize_acoustid_tags({'instrumental': 0.7, 'voice': 0.3})
    test("AcoustID instrumental et voice présents",
         'instrumental' in result and 'voice' in result)

    # Test confiance appliquée - confidence n'est pas dans le mapping donc pas utilisé directement
    result = service.normalize_acoustid_tags({'danceable': True, 'confidence': 0.5})
    test("AcoustID confiance appliquée (danceable=1.0)", result.get('danceability', 0.0) == 1.0)

    # === Tests normalize_moods_mirex ===
    result = service.normalize_moods_mirex(['Danceable'])
    test("MIREX Danceable", result.get('danceable', 0.0) > 0.5)

    result = service.normalize_moods_mirex(['Happy'])
    test("MIREX Happy", result.get('happy', 0.0) > 0.5)

    result = service.normalize_moods_mirex(['Danceable', 'Happy', 'Energetic'])
    test("MIREX multiple moods",
         'danceable' in result and 'happy' in result and 'energetic' in result)

    result = service.normalize_moods_mirex([])
    test("MIREX liste vide", result == {})

    result = service.normalize_moods_mirex(['UnknownMood'])
    test("MIREX mood inconnu", 'unknownmood' in result and result['unknownmood'] == 0.3)

    # === Tests normalize_genre_taxonomies ===
    result = service.normalize_genre_taxonomies({'lastfm': ['Rock']})
    test("Genre unique: Rock", result.get('genre_main', '') == 'Rock')

    result = service.normalize_genre_taxonomies({
        'lastfm': ['Rock', 'Alternative'],
        'discogs': ['Electronic']
    })
    test("Genres multiples: main et secondary",
         'genre_main' in result and 'genre_secondary' in result)

    result = service.normalize_genre_taxonomies({})
    test("Genres vides", result == {})

    # === Tests normalize_all_features ===
    raw = {
        'acoustid': {
            'danceable': True,
            'mood_happy': False,
            'acoustic': True
        },
        'moods_mirex': ['Danceable'],
        'bpm': 128,
        'key': 'C',
        'scale': 'major',
        'genres': {
            'lastfm': ['Rock']
        }
    }

    result = service.normalize_all_features(raw)

    test("All features: danceability", 'danceability' in result)
    test("All features: bpm_raw", result.get('bpm_raw') == 128)
    test("All features: bpm_score", 'bpm_score' in result)
    test("All features: key", result.get('key') == 'C')
    test("All features: scale", result.get('scale') == 'major')
    test("All features: camelot_key", result.get('camelot_key') == '8B')
    test("All features: genre_main", result.get('genre_main') == 'Rock')
    test("All features: confidence_score", 'confidence_score' in result)

    # === Résumé ===
    print()
    print(f"Tests passés: {passed}")
    print(f"Tests échoués: {failed}")
    print(f"Total: {passed + failed}")

    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
