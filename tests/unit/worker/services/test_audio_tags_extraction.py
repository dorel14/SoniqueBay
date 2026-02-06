#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider l'extraction des tags audio depuis les fichiers.

Ce script teste l'extraction des tags AcoustID et standards depuis un fichier audio
et vérifie que les caractéristiques audio (BPM, tonalité, moods, genres) sont
correctement extraites.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mutagen import File
from backend_worker.services.audio_features_service import (
    extract_audio_features,
    _extract_features_from_acoustid_tags,
    _extract_features_from_standard_tags,
    _has_valid_acoustid_tags,
    _has_valid_audio_tags,
)
from backend_worker.services.music_scan import serialize_tags
from backend_worker.utils.logging import logger


def test_extract_features_from_acoustid_tags():
    """Test l'extraction des features depuis les tags AcoustID."""
    logger.info("=" * 80)
    logger.info("TEST: Extraction des features depuis les tags AcoustID")
    logger.info("=" * 80)

    # Tags AcoustID de l'exemple fourni par l'utilisateur
    tags = {
        'ab:hi:mood_aggressive:not aggressive': ['0.461390972137'],
        'ab:hi:mood_electronic:electronic': ['0.940065085888'],
        'ab:hi:genre_electronic:techno': ['0.00530991051346'],
        'ab:hi:moods_mirex:literate, poignant, wistful, bittersweet, autumnal, brooding': ['0.200133308768'],
        'ab:hi:genre_tzanetakis:disco': ['0.0518908686936'],
        'ab:lo:tonal:chords_scale': ['minor'],
        'ab:hi:genre_electronic:ambient': ['0.0402529537678'],
        'ab:hi:voice_instrumental:instrumental': ['0.976257145405'],
        'ab:genre': ['Electronic', 'Trance', 'Dance', 'Jazz'],
        'ab:hi:genre_tzanetakis:pop': ['0.0622744634748'],
        'ab:lo:tonal:chords_key': ['B'],
        'ab:lo:tonal:key_scale': ['major'],
        'ab:lo:rhythm:bpm': ['133.919158936'],
        'ab:hi:genre_rosamerica:dance': ['0.99874830246'],
        'ab:hi:danceability:not danceable': ['4.1884053644e-05'],
        'ab:hi:ismir04_rhythm:rumba-misc': ['0.0478919744492'],
        'ab:hi:mood_electronic:not electronic': ['0.0599348880351'],
        'ab:hi:genre_electronic:drum and bass': ['0.00100953748915'],
        'ab:hi:timbre:dark': ['0.889169216156'],
        'ab:hi:genre_tzanetakis:reggae': ['0.0622723288834'],
        'ab:hi:genre_rosamerica:rock': ['0.000309895374812'],
        'ab:hi:genre_tzanetakis:metal': ['0.0519040971994'],
        'ab:hi:voice_instrumental:voice': ['0.0237428341061'],
        'ab:hi:mood_party:party': ['0.94538640976'],
        'ab:hi:genre_tzanetakis:hiphop': ['0.155698984861'],
        'ab:lo:tonal:key_key': ['E'],
        'ab:hi:ismir04_rhythm:chachacha': ['0.205542996526'],
        'ab:hi:genre_tzanetakis:classical': ['0.0345780998468'],
        'ab:hi:ismir04_rhythm:rumba-american': ['0.0660188049078'],
        'ab:hi:genre_dortmund:electronic': ['0.999999582767'],
        'ab:hi:ismir04_rhythm:jive': ['0.129581585526'],
        'ab:hi:tonal_atonal:tonal': ['0.225971668959'],
        'ab:hi:moods_mirex:aggressive, fiery, tense/anxious, intense, volatile, visceral': ['0.637312233448'],
        'ab:hi:danceability:danceable': ['0.999958097935'],
        'ab:hi:mood_party:not party': ['0.0546135939658'],
        'ab:hi:genre_tzanetakis:country': ['0.103735685349'],
        'ab:mood': ['Not acoustic', 'Aggressive', 'Electronic', 'Happy', 'Party', 'Not relaxed', 'Not sad'],
        'ab:hi:ismir04_rhythm:waltz': ['0.0244606081396'],
        'ab:hi:genre_dortmund:rock': ['1.05633070291e-07'],
        'ab:hi:moods_mirex:humorous, silly, campy, quirky, whimsical, witty, wry': ['0.0376816093922'],
        'ab:hi:mood_relaxed:relaxed': ['0.196425050497'],
        'ab:hi:genre_electronic:house': ['0.00770339276642'],
        'bpm': ['134'],
        'ab:hi:ismir04_rhythm:samba': ['0.109423451126'],
        'ab:hi:genre_electronic:trance': ['0.945724189281'],
        'ab:hi:tonal_atonal:atonal': ['0.774028301239'],
        'ab:lo:tonal:chords_changes_rate': ['0.030385190621'],
        'ab:hi:genre_rosamerica:jazz': ['4.03387421102e-05'],
        'ab:hi:timbre:bright': ['0.110830776393'],
        'ab:hi:mood_acoustic:not acoustic': ['0.999992251396'],
        'ab:hi:gender:female': ['0.944188416004'],
        'ab:hi:ismir04_rhythm:tango': ['0.159760206938'],
        'ab:hi:mood_sad:sad': ['0.316827952862'],
        'ab:hi:genre_rosamerica:speech': ['6.73034883221e-05'],
        'ab:hi:genre_dortmund:pop': ['1.55241295374e-08'],
        'ab:hi:mood_happy:happy': ['0.527822375298'],
        'ab:hi:genre_rosamerica:rhythm and blues': ['0.000254677608609'],
        'key': ['E'],
        'ab:hi:mood_relaxed:not relaxed': ['0.803574979305'],
        'ab:hi:genre_tzanetakis:rock': ['0.103792458773'],
        'ab:hi:genre_tzanetakis:blues': ['0.0622663982213'],
        'ab:hi:mood_sad:not sad': ['0.683172047138'],
        'ab:hi:ismir04_rhythm:quickstep': ['0.0353913493454'],
        'ab:hi:genre_rosamerica:pop': ['0.00018216468743'],
        'ab:hi:genre_dortmund:alternative': ['4.72600127435e-12'],
        'ab:hi:mood_acoustic:acoustic': ['7.72694238549e-06'],
        'ab:hi:mood_aggressive:aggressive': ['0.538609027863'],
        'ab:hi:ismir04_rhythm:viennesewaltz': ['0.171692177653'],
        'ab:hi:moods_mirex:rollicking, cheerful, fun, sweet, amiable/good natured': ['0.0520649626851'],
        'ab:hi:genre_rosamerica:classical': ['2.76430426993e-07'],
    }

    logger.info(f"Tags AcoustID fournis: {len(tags)} tags")
    logger.info(f"Tags AcoustID: {list(tags.keys())[:20]}...")

    # Vérifier si les tags sont valides
    has_valid_tags = _has_valid_acoustid_tags(tags)
    logger.info(f"Tags AcoustID valides: {has_valid_tags}")

    if has_valid_tags:
        # Extraire les features
        features = _extract_features_from_acoustid_tags(tags)

        logger.info("\n" + "=" * 80)
        logger.info("RÉSULTATS DE L'EXTRACTION")
        logger.info("=" * 80)

        # Afficher les features extraites
        for key, value in features.items():
            if value is not None and value != []:
                logger.info(f"  {key}: {value}")

        # Vérifications spécifiques
        logger.info("\n" + "=" * 80)
        logger.info("VÉRIFICATIONS")
        logger.info("=" * 80)

        # Vérifier le BPM
        if features.get('bpm'):
            logger.info(f"✅ BPM extrait: {features['bpm']}")
        else:
            logger.warning("❌ BPM non extrait")

        # Vérifier la key
        if features.get('key'):
            logger.info(f"✅ Key extraite: {features['key']}")
        else:
            logger.warning("❌ Key non extraite")

        # Vérifier les moods
        if features.get('mood_tags'):
            logger.info(f"✅ Moods extraits: {features['mood_tags']}")
        else:
            logger.warning("❌ Moods non extraits")

        # Vérifier les genres
        if features.get('genre_tags'):
            logger.info(f"✅ Genres extraits: {features['genre_tags']}")
        else:
            logger.warning("❌ Genres non extraits")

        # Vérifier les scores de mood
        mood_scores = {
            'mood_happy': features.get('mood_happy'),
            'mood_aggressive': features.get('mood_aggressive'),
            'mood_party': features.get('mood_party'),
            'mood_relaxed': features.get('mood_relaxed'),
        }
        logger.info(f"✅ Scores de mood: {mood_scores}")

        return features
    else:
        logger.error("❌ Tags AcoustID non valides")
        return None


def test_extract_features_from_standard_tags():
    """Test l'extraction des features depuis les tags standards."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Extraction des features depuis les tags standards")
    logger.info("=" * 80)

    # Tags standards de l'exemple fourni par l'utilisateur
    tags = {
        'bpm': ['134'],
        'key': ['E'],
        'genre': ['Trance'],
    }

    logger.info(f"Tags standards fournis: {len(tags)} tags")
    logger.info(f"Tags standards: {list(tags.keys())}")

    # Vérifier si les tags sont valides
    has_valid_tags = _has_valid_audio_tags(tags)
    logger.info(f"Tags standards valides: {has_valid_tags}")

    if has_valid_tags:
        # Extraire les features
        features = _extract_features_from_standard_tags(tags)

        logger.info("\n" + "=" * 80)
        logger.info("RÉSULTATS DE L'EXTRACTION")
        logger.info("=" * 80)

        # Afficher les features extraites
        for key, value in features.items():
            if value is not None and value != []:
                logger.info(f"  {key}: {value}")

        # Vérifications spécifiques
        logger.info("\n" + "=" * 80)
        logger.info("VÉRIFICATIONS")
        logger.info("=" * 80)

        # Vérifier le BPM
        if features.get('bpm'):
            logger.info(f"✅ BPM extrait: {features['bpm']}")
        else:
            logger.warning("❌ BPM non extrait")

        # Vérifier la key
        if features.get('key'):
            logger.info(f"✅ Key extraite: {features['key']}")
        else:
            logger.warning("❌ Key non extraite")

        return features
    else:
        logger.error("❌ Tags standards non valides")
        return None


def test_extract_audio_features_from_file(file_path: str):
    """Test l'extraction des features depuis un fichier audio."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Extraction des features depuis un fichier audio")
    logger.info("=" * 80)

    if not os.path.exists(file_path):
        logger.error(f"Fichier non trouvé: {file_path}")
        return None

    logger.info(f"Fichier: {file_path}")

    # Charger le fichier audio avec mutagen
    audio = File(file_path, easy=True)

    if audio is None:
        logger.error("Impossible de charger le fichier audio")
        return None

    # Sérialiser les tags
    tags = serialize_tags(audio.tags) if audio and hasattr(audio, "tags") else {}

    logger.info(f"Tags sérialisés: {len(tags)} tags")
    logger.info(f"Tags: {list(tags.keys())[:20]}...")

    # Extraire les features
    features = extract_audio_features(
        audio=audio,
        tags=tags,
        file_path=file_path,
        track_id=None
    )

    logger.info("\n" + "=" * 80)
    logger.info("RÉSULTATS DE L'EXTRACTION")
    logger.info("=" * 80)

    # Afficher les features extraites
    for key, value in features.items():
        if value is not None and value != []:
            logger.info(f"  {key}: {value}")

    return features


def main():
    """Fonction principale."""
    logger.info("=" * 80)
    logger.info("SCRIPT DE TEST D'EXTRACTION DES TAGS AUDIO")
    logger.info("=" * 80)

    # Test 1: Extraction depuis les tags AcoustID
    test_extract_features_from_acoustid_tags()

    # Test 2: Extraction depuis les tags standards
    test_extract_features_from_standard_tags()

    # Test 3: Extraction depuis un fichier audio (optionnel)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        test_extract_audio_features_from_file(file_path)
    else:
        logger.info("\n" + "=" * 80)
        logger.info("Pour tester avec un fichier audio, utilisez:")
        logger.info("  python scripts/test_audio_tags_extraction.py <chemin_du_fichier>")
        logger.info("=" * 80)

    logger.info("\n" + "=" * 80)
    logger.info("TEST TERMINÉ")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
