#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider l'intégration des tags audio avec la base de données.

Ce script teste que les tags mood et genre sont correctement stockés en base de données
après l'extraction depuis les fichiers audio.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_worker.services.audio_features_service import (
    extract_audio_features,
    _extract_features_from_acoustid_tags,
    _extract_features_from_standard_tags,
    _has_valid_acoustid_tags,
    _has_valid_audio_tags
)
from backend_worker.utils.logging import logger


def test_acoustid_tags_extraction():
    """Test l'extraction des tags AcoustID depuis un fichier audio."""
    logger.info("=" * 80)
    logger.info("TEST 1: Extraction des tags AcoustID")
    logger.info("=" * 80)

    # Exemple de tags AcoustID (issu du fichier FLAC fourni)
    example_tags = {
        'ab:hi:mood_aggressive:not aggressive': ['0.461390972137'],
        'ab:hi:mood_electronic:electronic': ['0.940065085888'],
        'ab:hi:genre_electronic:techno': ['0.00530991051346'],
        'ab:hi:moods_mirex:literate, poignant, wistful, bittersweet, autumnal, brooding': ['0.200133308768'],
        'ab:hi:voice_instrumental:instrumental': ['0.976257145405'],
        'ab:genre': ['Electronic', 'Trance', 'Dance', 'Jazz'],
        'ab:hi:genre_tzanetakis:rock': ['0.103792458773'],
        'ab:mood': ['Not acoustic', 'Aggressive', 'Electronic', 'Happy', 'Party', 'Not relaxed', 'Not sad'],
        'ab:lo:rhythm:bpm': ['133.919158936'],
        'ab:hi:danceability:danceable': ['0.999958097935'],
        'ab:hi:mood_party:party': ['0.94538640976'],
        'ab:hi:mood_happy:happy': ['0.527822375298'],
        'ab:hi:mood_relaxed:relaxed': ['0.196425050497'],
        'ab:hi:mood_aggressive:aggressive': ['0.538609027863'],
        'ab:hi:genre_electronic:trance': ['0.945724189281'],
    }

    logger.info(f"Tags AcoustID fournis: {len(example_tags)} tags")

    # Vérifier que les tags sont valides
    has_valid_tags = _has_valid_acoustid_tags(example_tags)
    logger.info(f"Tags AcoustID valides: {has_valid_tags}")

    if not has_valid_tags:
        logger.error("❌ Les tags AcoustID ne sont pas reconnus comme valides!")
        return False

    # Extraire les caractéristiques
    features = _extract_features_from_acoustid_tags(example_tags)

    logger.info("\n📊 Caractéristiques extraites:")
    for key, value in features.items():
        if value is not None and value != []:
            logger.info(f"  {key}: {value}")

    # Vérifier les champs critiques
    critical_fields = {
        'bpm': features.get('bpm'),
        'key': features.get('key'),
        'danceability': features.get('danceability'),
        'mood_happy': features.get('mood_happy'),
        'mood_aggressive': features.get('mood_aggressive'),
        'mood_party': features.get('mood_party'),
        'mood_relaxed': features.get('mood_relaxed'),
        'genre_tags': features.get('genre_tags'),
        'mood_tags': features.get('mood_tags'),
    }

    logger.info("\n🔍 Vérification des champs critiques:")
    all_valid = True
    for field, value in critical_fields.items():
        if value is None or value == []:
            logger.warning(f"  ⚠️  {field}: {value} (manquant)")
            all_valid = False
        else:
            logger.info(f"  ✅ {field}: {value}")

    if all_valid:
        logger.info("\n✅ TEST 1 RÉUSSI: Tous les champs critiques sont extraits!")
        return True
    else:
        logger.error("\n❌ TEST 1 ÉCHOUÉ: Certains champs critiques sont manquants!")
        return False


def test_standard_tags_extraction():
    """Test l'extraction des tags standards depuis un fichier audio."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Extraction des tags standards")
    logger.info("=" * 80)

    # Exemple de tags standards
    example_tags = {
        'BPM': ['134'],
        'KEY': ['E'],
        'MOOD': ['Happy', 'Party'],
        'DANCEABILITY': ['0.9'],
        'ENERGY': ['0.8'],
        'ACOUSTICNESS': ['0.1'],
        'INSTRUMENTALNESS': ['0.9'],
        'VALENCE': ['0.7'],
    }

    logger.info(f"Tags standards fournis: {len(example_tags)} tags")

    # Vérifier que les tags sont valides
    has_valid_tags = _has_valid_audio_tags(example_tags)
    logger.info(f"Tags standards valides: {has_valid_tags}")

    if not has_valid_tags:
        logger.error("❌ Les tags standards ne sont pas reconnus comme valides!")
        return False

    # Extraire les caractéristiques
    features = _extract_features_from_standard_tags(example_tags)

    logger.info("\n📊 Caractéristiques extraites:")
    for key, value in features.items():
        if value is not None and value != []:
            logger.info(f"  {key}: {value}")

    # Vérifier les champs critiques
    critical_fields = {
        'bpm': features.get('bpm'),
        'key': features.get('key'),
        'danceability': features.get('danceability'),
        'mood_tags': features.get('mood_tags'),
    }

    logger.info("\n🔍 Vérification des champs critiques:")
    all_valid = True
    for field, value in critical_fields.items():
        if value is None or value == []:
            logger.warning(f"  ⚠️  {field}: {value} (manquant)")
            all_valid = False
        else:
            logger.info(f"  ✅ {field}: {value}")

    if all_valid:
        logger.info("\n✅ TEST 2 RÉUSSI: Tous les champs critiques sont extraits!")
        return True
    else:
        logger.error("\n❌ TEST 2 ÉCHOUÉ: Certains champs critiques sont manquants!")
        return False


def test_extract_audio_features_integration():
    """Test l'intégration complète de l'extraction des caractéristiques audio."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Intégration complète de l'extraction")
    logger.info("=" * 80)

    # Exemple de tags AcoustID complets
    example_tags = {
        'ab:hi:mood_aggressive:not aggressive': ['0.461390972137'],
        'ab:hi:mood_electronic:electronic': ['0.940065085888'],
        'ab:hi:genre_electronic:techno': ['0.00530991051346'],
        'ab:hi:moods_mirex:literate, poignant, wistful, bittersweet, autumnal, brooding': ['0.200133308768'],
        'ab:hi:voice_instrumental:instrumental': ['0.976257145405'],
        'ab:genre': ['Electronic', 'Trance', 'Dance', 'Jazz'],
        'ab:hi:genre_tzanetakis:rock': ['0.103792458773'],
        'ab:mood': ['Not acoustic', 'Aggressive', 'Electronic', 'Happy', 'Party', 'Not relaxed', 'Not sad'],
        'ab:lo:rhythm:bpm': ['133.919158936'],
        'ab:hi:danceability:danceable': ['0.999958097935'],
        'ab:hi:mood_party:party': ['0.94538640976'],
        'ab:hi:mood_happy:happy': ['0.527822375298'],
        'ab:hi:mood_relaxed:relaxed': ['0.196425050497'],
        'ab:hi:mood_aggressive:aggressive': ['0.538609027863'],
        'ab:hi:genre_electronic:trance': ['0.945724189281'],
    }

    logger.info(f"Tags fournis: {len(example_tags)} tags")

    # Extraire les caractéristiques avec la fonction principale (async)
    import asyncio
    features = asyncio.run(extract_audio_features(
        audio=None,
        tags=example_tags,
        file_path=None,
        track_id=1
    ))

    logger.info("\n📊 Caractéristiques extraites:")
    for key, value in features.items():
        if value is not None and value != []:
            logger.info(f"  {key}: {value}")

    # Vérifier les champs critiques
    critical_fields = {
        'bpm': features.get('bpm'),
        'key': features.get('key'),
        'danceability': features.get('danceability'),
        'mood_happy': features.get('mood_happy'),
        'mood_aggressive': features.get('mood_aggressive'),
        'mood_party': features.get('mood_party'),
        'mood_relaxed': features.get('mood_relaxed'),
        'genre_tags': features.get('genre_tags'),
        'mood_tags': features.get('mood_tags'),
    }

    logger.info("\n🔍 Vérification des champs critiques:")
    all_valid = True
    for field, value in critical_fields.items():
        if value is None or value == []:
            logger.warning(f"  ⚠️  {field}: {value} (manquant)")
            all_valid = False
        else:
            logger.info(f"  ✅ {field}: {value}")

    if all_valid:
        logger.info("\n✅ TEST 3 RÉUSSI: L'intégration complète fonctionne!")
        return True
    else:
        logger.error("\n❌ TEST 3 ÉCHOUÉ: Certains champs critiques sont manquants!")
        return False


def test_db_integration():
    """Test l'intégration avec la base de données."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Intégration avec la base de données")
    logger.info("=" * 80)

    try:
        from backend.api.utils.database import get_db
        from backend.api.services.track_service import TrackService
        from backend.api.schemas.tracks_schema import TrackCreate

        # Créer une session de base de données
        db_gen = get_db()
        db = next(db_gen)

        # Créer un service de tracks
        track_service = TrackService(db)

        # Créer des données de test
        track_data = TrackCreate(
            title="Test Track",
            path="/test/path.flac",
            track_artist_id=1,
            album_id=1,
            genre="Electronic",
            bpm=134,
            key="E",
            scale="major",
            duration=300,
            track_number="1",
            disc_number="1",
            year="2010",
            file_type="audio/flac",
            bitrate=1000,
            danceability=0.9,
            mood_happy=0.5,
            mood_aggressive=0.5,
            mood_party=0.9,
            mood_relaxed=0.2,
            instrumental=0.9,
            acoustic=0.1,
            tonal=0.7,
            camelot_key="12B",
            genre_tags=["Electronic", "Trance", "Dance", "Jazz"],
            mood_tags=["Happy", "Party", "Aggressive"]
        )

        logger.info("Données de test créées")

        # Créer la track
        track = track_service.create_track(track_data)

        logger.info(f"Track créée avec ID: {track.id}")

        # Vérifier que les tags sont correctement stockés
        db.refresh(track)

        logger.info("\n📊 Tags stockés en base de données:")
        logger.info(f"  Genre tags: {[tag.name for tag in track.genre_tags]}")
        logger.info(f"  Mood tags: {[tag.name for tag in track.mood_tags]}")

        # Vérifier les champs critiques
        critical_fields = {
            'bpm': track.bpm,
            'key': track.key,
            'danceability': track.danceability,
            'mood_happy': track.mood_happy,
            'mood_aggressive': track.mood_aggressive,
            'mood_party': track.mood_party,
            'mood_relaxed': track.mood_relaxed,
        }

        logger.info("\n🔍 Vérification des champs critiques:")
        all_valid = True
        for field, value in critical_fields.items():
            if value is None:
                logger.warning(f"  ⚠️  {field}: {value} (manquant)")
                all_valid = False
            else:
                logger.info(f"  ✅ {field}: {value}")

        # Nettoyer
        db.delete(track)
        db.commit()

        if all_valid:
            logger.info("\n✅ TEST 4 RÉUSSI: L'intégration avec la base de données fonctionne!")
            return True
        else:
            logger.error("\n❌ TEST 4 ÉCHOUÉ: Certains champs critiques sont manquants en base de données!")
            return False

    except Exception as e:
        logger.error(f"❌ Erreur lors du test d'intégration avec la base de données: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale pour exécuter tous les tests."""
    logger.info("\n" + "=" * 80)
    logger.info("DÉBUT DES TESTS D'INTÉGRATION DES TAGS AUDIO")
    logger.info("=" * 80)

    results = []

    # Test 1: Extraction des tags AcoustID
    results.append(("Extraction des tags AcoustID", test_acoustid_tags_extraction()))

    # Test 2: Extraction des tags standards
    results.append(("Extraction des tags standards", test_standard_tags_extraction()))

    # Test 3: Intégration complète de l'extraction
    results.append(("Intégration complète de l'extraction", test_extract_audio_features_integration()))

    # Test 4: Intégration avec la base de données
    results.append(("Intégration avec la base de données", test_db_integration()))

    # Résumé des résultats
    logger.info("\n" + "=" * 80)
    logger.info("RÉSUMÉ DES TESTS")
    logger.info("=" * 80)

    for test_name, result in results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        logger.info("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        return 0
    else:
        logger.error("\n❌ CERTAINS TESTS ONT ÉCHOUÉ!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
