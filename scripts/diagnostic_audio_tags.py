#!/usr/bin/env python3
"""
Script de diagnostic pour analyser les tags audio dans les fichiers FLAC.
Ce script vérifie tous les tags disponibles et identifie ceux qui contiennent
des informations audio (BPM, tonalité, etc.).
"""

import os
import sys

# Ajouter le backend_worker au path pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

from mutagen import File

from backend_worker.services.music_scan import serialize_tags


def analyze_audio_file(file_path: str):
    """
    Analyse tous les tags disponibles dans un fichier audio.
    
    Args:
        file_path: Chemin vers le fichier audio
        
    Returns:
        Dictionnaire avec l'analyse complète
    """
    print(f"\n=== DIAGNOSTIC AUDIO pour {file_path} ===")
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return None
    
    try:
        # Charger le fichier avec mutagen
        audio = File(file_path, easy=False)
        if audio is None:
            print("❌ Impossible de charger le fichier avec mutagen")
            return None
            
        print("✅ Fichier chargé avec succès")
        print(f"📁 Type de fichier: {type(audio).__name__}")
        
        # Analyser tous les tags disponibles
        all_tags = serialize_tags(audio.tags) if audio and hasattr(audio, "tags") and audio.tags else {}
        
        print(f"\n📋 TOUS LES TAGS DISPONIBLES ({len(all_tags)} tags):")
        print("-" * 60)
        
        # Catégoriser les tags
        categories = {
            'Métadonnées de base': ['TITLE', 'ARTIST', 'ALBUM', 'DATE', 'TRACKNUMBER', 'GENRE'],
            'MusicBrainz': ['MUSICBRAINZ', 'UFID:', 'TXXX:'],
            'AcoustID': ['ab:hi:', 'ab:lo:'],
            'BPM/Rythme': ['BPM', 'TBPM', 'TEMPO'],
            'Tonalité/Key': ['KEY', 'TKEY', 'INITIALKEY'],
            'Mood/Émotion': ['MOOD', 'TMOO'],
            'Audio properties': ['BITRATE', 'SAMPLERATE', 'BITS_PER_SAMPLE']
        }
        
        # Rechercher tous les tags pertinents
        found_tags = {}
        
        for category, tag_patterns in categories.items():
            found_tags[category] = []
            for tag_name, tag_value in all_tags.items():
                # Vérifier si le tag correspond aux patterns de la catégorie
                for pattern in tag_patterns:
                    if pattern.upper() in tag_name.upper():
                        found_tags[category].append({
                            'name': tag_name,
                            'value': tag_value,
                            'type': type(tag_value).__name__
                        })
                        break
        
        # Afficher les tags par catégorie
        for category, tags in found_tags.items():
            if tags:
                print(f"\n🎵 {category}:")
                for tag in tags:
                    print(f"  • {tag['name']}: {tag['value']} ({tag['type']})")
            else:
                print(f"\n❌ {category}: Aucun tag trouvé")
        
        # Vérifier spécifiquement les tags AcoustID
        print("\n🔍 RECHERCHE SPÉCIFIQUE ACOUSTID:")
        acoustid_tags = {}
        for tag_name, tag_value in all_tags.items():
            if isinstance(tag_name, str) and ('ab:hi:' in tag_name or 'ab:lo:' in tag_name):
                acoustid_tags[tag_name] = tag_value
                print(f"  • {tag_name}: {tag_value}")
        
        if not acoustid_tags:
            print("  ❌ Aucun tag AcoustID trouvé")
        
        # Vérifier les tags BPM/Key standards
        print("\n🎼 RECHERCHE BPM/KEY STANDARDS:")
        standard_bpm_tags = {}
        standard_key_tags = {}
        
        for tag_name, tag_value in all_tags.items():
            tag_name_upper = tag_name.upper()
            if 'BPM' in tag_name_upper or 'TEMPO' in tag_name_upper:
                standard_bpm_tags[tag_name] = tag_value
                print(f"  • BPM: {tag_name} = {tag_value}")
            elif 'KEY' in tag_name_upper or 'TKEY' in tag_name_upper:
                standard_key_tags[tag_name] = tag_value
                print(f"  • Key: {tag_name} = {tag_value}")
        
        if not standard_bpm_tags:
            print("  ❌ Aucun tag BPM standard trouvé")
        if not standard_key_tags:
            print("  ❌ Aucun tag Key standard trouvé")
        
        # Analyser les capacités du système SoniqueBay
        print("\n🔧 ANALYSE SYSTÈME SONIQUEBAY:")
        
        # Vérifier si les tags AcoustID sont valides pour SoniqueBay
        from backend_worker.services.audio_features_service import (
            _has_valid_acoustid_tags,
        )
        has_valid_acoustid = _has_valid_acoustid_tags(all_tags)
        print(f"  • Tags AcoustID valides pour SoniqueBay: {'✅ OUI' if has_valid_acoustid else '❌ NON'}")
        
        # Vérifier les champs audio que SoniqueBay recherche
        audio_fields = ["bpm", "key", "scale", "danceability", "mood_happy", "mood_aggressive", 
                       "mood_party", "mood_relaxed", "instrumental", "acoustic", "tonal", "camelot_key"]
        
        print("  • Champs audio SoniqueBay recherchés:")
        for field in audio_fields:
            # Chercher des variations du nom de champ
            found = False
            for tag_name in all_tags.keys():
                if field.lower() in tag_name.lower():
                    print(f"    - {field}: ✅ Trouvé ({tag_name} = {all_tags[tag_name]})")
                    found = True
                    break
            if not found:
                print(f"    - {field}: ❌ Non trouvé")
        
        # Résumé
        print("\n📊 RÉSUMÉ:")
        total_tags = len(all_tags)
        acoustid_count = len(acoustid_tags)
        bpm_count = len(standard_bpm_tags)
        key_count = len(standard_key_tags)
        
        print(f"  • Total des tags: {total_tags}")
        print(f"  • Tags AcoustID: {acoustid_count}")
        print(f"  • Tags BPM standard: {bpm_count}")
        print(f"  • Tags Key standard: {key_count}")
        
        if acoustid_count > 0 or bpm_count > 0 or key_count > 0:
            print("  ✅ CONCLUSION: Des champs audio SONT disponibles dans le fichier")
        else:
            print("  ❌ CONCLUSION: Aucun champ audio trouvé dans le fichier")
        
        return {
            'file_path': file_path,
            'total_tags': total_tags,
            'acoustid_tags': acoustid_tags,
            'bpm_tags': standard_bpm_tags,
            'key_tags': standard_key_tags,
            'all_tags': all_tags,
            'has_valid_acoustid': has_valid_acoustid
        }
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python diagnostic_audio_tags.py <chemin_fichier_audio>")
        print("Exemple: python diagnostic_audio_tags.py '/music/Massive Attack/Singles 90_98/02-03 - Massive Attack - Unfinished Sympathy (Nellee Hooper 12″ mix).flac'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Vérifier si c'est un répertoire ou un fichier
    if os.path.isdir(file_path):
        print(f"📁 Analyse de tous les fichiers audio dans: {file_path}")
        audio_extensions = {'.flac', '.mp3', '.m4a', '.ogg', '.wav', '.aac'}
        
        audio_files = []
        for root, dirs, files in os.walk(file_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in audio_extensions):
                    audio_files.append(os.path.join(root, file))
        
        print(f"🎵 {len(audio_files)} fichiers audio trouvés")
        
        for audio_file in audio_files[:10]:  # Limiter à 10 fichiers pour le diagnostic
            analyze_audio_file(audio_file)
            
        if len(audio_files) > 10:
            print(f"\n... et {len(audio_files) - 10} autres fichiers")
            
    else:
        # Analyser un seul fichier
        analyze_audio_file(file_path)


if __name__ == "__main__":
    main()