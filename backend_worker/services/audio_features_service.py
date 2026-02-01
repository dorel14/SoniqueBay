from backend_worker.utils.logging import logger
import librosa
import httpx
import os
import numpy as np
from backend_worker.services.key_service import key_to_camelot
import asyncio


async def analyze_audio_with_librosa(track_id: int, file_path: str) -> dict:
    """
    Analyse un fichier audio avec Librosa de manière optimisée.

    Args:
        track_id: ID de la track à analyser
        file_path: Chemin vers le fichier audio

    Returns:
        Dictionnaire des caractéristiques audio extraites
    """
    try:
        logger.info(f"Analyse Librosa pour track {track_id}: {file_path}")

        # Vérifier que le fichier existe et est accessible
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier audio non trouvé: {file_path}")

        # Utiliser un executor pour les opérations CPU-intensive
        loop = asyncio.get_running_loop()

        # Charger l'audio avec optimisation
        y, sr = await loop.run_in_executor(
            None,
            lambda: librosa.load(file_path, mono=True, duration=60)  # Réduire à 60s pour performance
        )

        # Analyse parallèle des caractéristiques
        tasks = [
            loop.run_in_executor(None, lambda: librosa.beat.beat_track(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.chroma_stft(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.spectral_centroid(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.spectral_rolloff(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.rms(y=y)),
        ]

        # Attendre tous les résultats
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Traiter les résultats avec gestion d'erreurs
        tempo_result, chroma_result, centroid_result, rolloff_result, rms_result = results

        # Extraction du tempo
        tempo = 120.0  # Valeur par défaut
        if not isinstance(tempo_result, Exception):
            tempo, _ = tempo_result
            tempo = float(tempo) if tempo > 0 else 120.0

        # Extraction de la tonalité
        key = "C"
        scale = "major"
        if not isinstance(chroma_result, Exception):
            chroma = chroma_result
            key_index = int(np.mean(chroma, axis=1).argmax())
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key = keys[key_index % 12]
            # Estimation basique de la scale (à améliorer avec un vrai modèle)
            scale = 'major' if key_index % 2 == 0 else 'minor'

        # Calcul des autres caractéristiques avec sécurisation
        features = {
            "bpm": int(tempo),
            "key": key,
            "scale": scale,
            "danceability": 0.5,  # Valeur par défaut
            "acoustic": 0.5,      # Valeur par défaut
            "instrumental": 0.5,  # Valeur par défaut
            "tonal": 0.5,         # Valeur par défaut
            "camelot_key": key_to_camelot(key, scale),
        }

        # Calcul des caractéristiques avancées si les données sont disponibles
        if not isinstance(centroid_result, Exception):
            spectral_centroids = centroid_result[0]
            features["acoustic"] = float(np.clip(np.mean(spectral_centroids < sr/4), 0, 1))

        if not isinstance(rolloff_result, Exception):
            spectral_rolloff = rolloff_result[0]
            features["instrumental"] = float(np.clip(np.mean(spectral_rolloff > sr/3), 0, 1))

        if not isinstance(rms_result, Exception):
            rms = rms_result[0]
            features["danceability"] = float(np.clip(np.mean(rms), 0, 1))

        if not isinstance(chroma_result, Exception):
            features["tonal"] = float(np.clip(np.std(chroma_result), 0, 1))

        logger.info(f"Analyse Librosa terminée pour track {track_id}: BPM={features['bpm']}, Key={features['key']}")

        # Mise à jour asynchrone de la track
        await _update_track_features_async(track_id, features)

        return features

    except Exception as e:
        logger.error(f"Erreur analyse Librosa: {str(e)}")
        return {}


async def _update_track_features_async(track_id: int, features: dict):
    """
    Met à jour les caractéristiques audio d'une track de manière asynchrone.

    Args:
        track_id: ID de la track
        features: Caractéristiques à mettre à jour
    """
    API_URL = os.getenv("API_URL", "http://api:8001")
    
    # === DIAGNOSTIC : APPEL API ===
    logger.info(f"=== Tentative mise à jour track {track_id} ===")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"Features à sauvegarder: {features}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{API_URL}/api/tracks/{track_id}/features",
                json={"features": features}
            )
            
            # === DIAGNOSTIC : RÉPONSE API ===
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response text: {response.text[:200]}...")
            
            response.raise_for_status()
            logger.info(f"Track {track_id} mise à jour avec succès")
            
            return True

    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP {e.response.status_code} lors de la mise à jour de la track {track_id}: {e.response.text}")
        logger.error(f"Endpoint utilisé: {API_URL}/api/tracks/{track_id}/features")
        return False
    except httpx.RequestError as e:
        logger.error(f"Erreur de requête lors de la mise à jour de la track {track_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la track {track_id}: {str(e)}")
        # Note: Retry logic removed as Celery handles task retries
        return False


async def analyze_audio_batch(track_data_list: list) -> dict:
    """
    Analyse un lot de fichiers audio en parallèle ultra-optimisée.

    Args:
        track_data_list: Liste de tuples (track_id, file_path)

    Returns:
        Résultats détaillés de l'analyse pour chaque track
    """
    logger.info(f"Démarrage analyse batch ultra-optimisée de {len(track_data_list)} tracks")

    # Augmenter la parallélisation pour les analyses CPU
    semaphore = asyncio.Semaphore(20)  # Augmenté de 4 à 20 pour plus de parallélisation

    # Utiliser un ThreadPoolExecutor pour les analyses Librosa
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

    async def analyze_with_semaphore(track_data: dict):
        async with semaphore:
            try:
                track_id = track_data.get('id') or track_data.get('track_id')
                file_path = track_data.get('path') or track_data.get('file_path')

                if not track_id or not file_path:
                    logger.error(f"Données track invalides: {track_data}")
                    return None

                # Utiliser l'executor pour l'analyse complète
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    executor,
                    lambda: asyncio.run(analyze_audio_with_librosa(track_id, file_path))
                )

                return {
                    "track_id": track_id,
                    "file_path": file_path,
                    "features": result,
                    "success": bool(result)
                }

            except Exception as e:
                logger.error(f"Exception analyse track {track_data}: {str(e)}")
                return {
                    "track_id": track_data.get('id'),
                    "file_path": track_data.get('path'),
                    "features": {},
                    "success": False,
                    "error": str(e)
                }

    # Lancer toutes les analyses en parallèle
    tasks = [analyze_with_semaphore(track_data) for track_data in track_data_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Traiter et nettoyer les résultats
    successful = 0
    failed = 0
    processed_results = []

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception globale analyse batch: {str(result)}")
            failed += 1
        elif result and result.get("success"):
            successful += 1
            processed_results.append(result)
        else:
            failed += 1
            if result:
                processed_results.append(result)

    # Nettoyer l'executor
    executor.shutdown(wait=True)

    logger.info(f"Analyse batch ultra-optimisée terminée: {successful} succès, {failed} échecs sur {len(track_data_list)} tracks")

    return {
        "total": len(track_data_list),
        "successful": successful,
        "failed": failed,
        "results": processed_results,
        "avg_time_per_track": 0.0  # TODO: Calculer le temps moyen
    }

def _has_valid_audio_tags(tags: dict) -> bool:
    """
    Vérifie si les tags contiennent des données audio valides (AcoustID OU tags standards).
    
    Args:
        tags: Dictionnaire des tags sérialisés
        
    Returns:
        True si des tags audio valides sont présents (AcoustID ou standards)
    """
    if not tags or not isinstance(tags, dict):
        return False
    
    logger.info(f"Vérification des tags audio (AcoustID + standards): {list(tags.keys())}")
    
    # 1. Vérifier les tags AcoustID (commencent par 'ab:')
    acoustid_prefixes = ['ab:hi:', 'ab:lo:']
    for tag_name in tags.keys():
        if isinstance(tag_name, str):
            for prefix in acoustid_prefixes:
                if tag_name.startswith(prefix):
                    values = tags[tag_name]
                    if values and (isinstance(values, list) and any(values)):
                        logger.info(f"Tag AcoustID trouvé: {tag_name} = {values}")
                        return True
    
    # 2. Vérifier les tags audio standards
    standard_audio_patterns = [
        'BPM', 'TBPM', 'TEMPO',  # BPM/Rythme
        'KEY', 'TKEY', 'INITIALKEY',  # Tonalité
        'MOOD', 'TMOO',  # Mood/Émotion
        'DANCEABILITY', 'ENERGY',  # Caractéristiques Spotify
        'ACOUSTICNESS', 'INSTRUMENTALNESS', 'VALENCE'  # Caractéristiques audio
    ]
    
    for tag_name in tags.keys():
        if isinstance(tag_name, str):
            tag_name_upper = tag_name.upper()
            for pattern in standard_audio_patterns:
                if pattern in tag_name_upper:
                    values = tags[tag_name]
                    if values and str(values).strip():
                        logger.info(f"Tag audio standard trouvé: {tag_name} = {values}")
                        return True
    
    logger.info("Aucun tag audio valide trouvé (ni AcoustID ni standard)")
    return False


def _has_valid_acoustid_tags(tags: dict) -> bool:
    """
    Vérifie si les tags contiennent des données AcoustID valides (fonction de compatibilité).
    
    Args:
        tags: Dictionnaire des tags sérialisés
        
    Returns:
        True si des tags AcoustID valides sont présents
    """
    if not tags or not isinstance(tags, dict):
        return False
    
    # Vérifier la présence de tags AcoustID (commencent par 'ab:')
    acoustid_prefixes = ['ab:hi:', 'ab:lo:']
    for tag_name in tags.keys():
        if isinstance(tag_name, str):
            for prefix in acoustid_prefixes:
                if tag_name.startswith(prefix):
                    # Vérifier que la valeur n'est pas vide
                    values = tags[tag_name]
                    if values and (isinstance(values, list) and any(values)):
                        return True
    
    return False


def _extract_features_from_standard_tags(tags: dict) -> dict:
    """
    Extrait les caractéristiques audio depuis les tags audio standards.
    
    Les tags standards incluent:
    - BPM, TBPM, TEMPO -> BPM
    - KEY, TKEY, INITIALKEY -> Tonalité
    - MOOD, TMOO -> Mood
    - DANCEABILITY, ENERGY -> Caractéristiques Spotify
    
    Args:
        tags: Dictionnaire des tags sérialisés
        
    Returns:
        Dictionnaire des caractéristiques extraites
    """
    features = {
        "bpm": None,
        "key": None,
        "scale": None,
        "danceability": None,
        "mood_happy": None,
        "mood_aggressive": None,
        "mood_party": None,
        "mood_relaxed": None,
        "instrumental": None,
        "acoustic": None,
        "tonal": None,
        "genre_tags": [],
        "mood_tags": []
    }
    
    if not tags or not isinstance(tags, dict):
        return features
    
    logger.info(f"Extraction des tags standards: {list(tags.keys())[:20]}...")
    
    # Mapping des tags standards vers les caractéristiques
    standard_mappings = {
        'bpm': ['BPM', 'TBPM', 'TEMPO'],
        'key': ['KEY', 'TKEY', 'INITIALKEY'],
        'mood': ['MOOD', 'TMOO'],
        'danceability': ['DANCEABILITY'],
        'energy': ['ENERGY'],
        'acousticness': ['ACOUSTICNESS'],
        'instrumentalness': ['INSTRUMENTALNESS'],
        'valence': ['VALENCE']
    }
    
    # Extraire les caractéristiques par catégorie
    for feature_key, tag_patterns in standard_mappings.items():
        for tag_name, tag_value in tags.items():
            if isinstance(tag_name, str):
                tag_name_upper = tag_name.upper()
                for pattern in tag_patterns:
                    if pattern in tag_name_upper:
                        # Gérer les valeurs qui sont des listes
                        if isinstance(tag_value, list) and tag_value:
                            tag_value = tag_value[0]
                        
                        if tag_value and str(tag_value).strip():
                            # Conversion selon le type
                            if feature_key == 'bpm':
                                try:
                                    features[feature_key] = int(float(str(tag_value)))
                                    logger.info(f"BPM standard trouvé: {tag_name} = {tag_value}")
                                except (ValueError, TypeError):
                                    pass
                            elif feature_key == 'key':
                                features[feature_key] = str(tag_value).strip()
                                logger.info(f"Key standard trouvée: {tag_name} = {tag_value}")
                            elif feature_key in ['danceability', 'energy', 'acousticness', 'instrumentalness', 'valence']:
                                try:
                                    # Normaliser les valeurs textuelles
                                    if isinstance(tag_value, str):
                                        value_lower = tag_value.lower()
                                        if value_lower in ['true', 'yes', '1', 'high', 'strong']:
                                            features[feature_key] = 1.0
                                        elif value_lower in ['false', 'no', '0', 'low', 'weak']:
                                            features[feature_key] = 0.0
                                    else:
                                        features[feature_key] = float(tag_value)
                                    logger.info(f"Caractéristique {feature_key} standard trouvée: {tag_name} = {tag_value}")
                                except (ValueError, TypeError):
                                    pass
                            elif feature_key == 'mood':
                                mood_value = str(tag_value).lower()
                                features['mood_tags'].append(mood_value)
                                
                                # Mapper les moods vers les caractéristiques
                                mood_mapping = {
                                    'happy': 'mood_happy',
                                    'sad': 'mood_relaxed',
                                    'relaxed': 'mood_relaxed',
                                    'calm': 'mood_relaxed',
                                    'aggressive': 'mood_aggressive',
                                    'energetic': 'mood_party',
                                    'party': 'mood_party',
                                    'electronic': 'mood_party',
                                }
                                
                                for mood_key, feature_key_mapped in mood_mapping.items():
                                    if mood_key in mood_value:
                                        features[feature_key_mapped] = 1.0
                                
                                logger.info(f"Mood standard trouvé: {tag_name} = {tag_value}")
                        break
    
    # Déduire la scale depuis la key si disponible
    if features['key']:
        key = features['key']
        # Déduction basique de la scale (à améliorer)
        minor_keys = ['Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm']
        features['scale'] = 'minor' if key in minor_keys else 'major'
    
    # Mapper les caractéristiques standard vers les champs SoniqueBay
    if features.get('acousticness') is not None:
        features['acoustic'] = features['acousticness']
    if features.get('instrumentalness') is not None:
        features['instrumental'] = features['instrumentalness']
    if features.get('valence') is not None:
        features['tonal'] = features['valence']
    
    logger.info(f"Features standards extraites: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
    return features


def _extract_features_from_acoustid_tags(tags: dict) -> dict:
    """
    Extrait les caractéristiques audio depuis les tags AcoustID.
    
    Les tags AcoustID sont structurés comme suit:
    - ab:hi:bpm:120 -> BPM
    - ab:hi:key:C -> Tonalité
    - ab:hi:mood:happy -> Mood
    - ab:hi:danceability:danceable -> Danceabilité
    - ab:mood -> Liste de moods (ex: ['Not acoustic', 'Aggressive', 'Electronic'])
    - bpm -> BPM standard
    
    Args:
        tags: Dictionnaire des tags AcoustID
        
    Returns:
        Dictionnaire des caractéristiques extraites (None si non disponible)
    """
    features = {
        "bpm": None,
        "key": None,
        "scale": None,
        "danceability": None,
        "mood_happy": None,
        "mood_aggressive": None,
        "mood_party": None,
        "mood_relaxed": None,
        "instrumental": None,
        "acoustic": None,
        "tonal": None,
        "genre_tags": [],
        "mood_tags": []
    }
    
    if not tags or not isinstance(tags, dict):
        return features
    
    logger.info(f"Extraction des tags AcoustID: {list(tags.keys())[:20]}...")
    
    # Mapping des tags AcoustID vers les caractéristiques
    tag_mapping = {
        'ab:hi:bpm': 'bpm',
        'ab:lo:bpm': 'bpm',
        'ab:lo:rhythm:bpm': 'bpm',  # Tag BPM spécifique AcoustID
        'ab:hi:key': 'key',
        'ab:lo:key': 'key',
        'ab:lo:tonal:key_key': 'key',  # Tag key spécifique AcoustID
        'ab:lo:tonal:chords_key': 'key',  # Alternative key tag
        'ab:hi:danceability': 'danceability',
        'ab:lo:danceability': 'danceability',
        'ab:hi:acousticness': 'acoustic',
        'ab:lo:acousticness': 'acoustic',
        'ab:hi:instrumentalness': 'instrumental',
        'ab:lo:instrumentalness': 'instrumental',
        'ab:hi:valence': 'tonal',
        'ab:lo:valence': 'tonal',
    }
    
    # Extraire les tags de mood depuis ab:mood (liste de moods)
    if 'ab:mood' in tags:
        mood_values = tags['ab:mood']
        if isinstance(mood_values, list):
            mood_tags = mood_values
        elif mood_values:
            mood_tags = [mood_values]
        else:
            mood_tags = []
        
        logger.info(f"Moods trouvés dans ab:mood: {mood_tags}")
        
        # Mapper les mood tags vers les caractéristiques
        mood_mapping = {
            'happy': 'mood_happy',
            'sad': 'mood_relaxed',
            'relaxed': 'mood_relaxed',
            'aggressive': 'mood_aggressive',
            'party': 'mood_party',
            'energetic': 'mood_party',
            'calm': 'mood_relaxed',
            'electronic': 'mood_party',
        }
        
        for mood in mood_tags:
            mood_lower = mood.lower() if isinstance(mood, str) else str(mood).lower()
            # Ignorer les moods négatifs (commencent par "not ")
            if mood_lower.startswith('not '):
                continue
            for mood_key, feature_key in mood_mapping.items():
                if mood_key in mood_lower:
                    features[feature_key] = 1.0
                    logger.info(f"Mood mappé: {mood} -> {feature_key}")
        
        features['mood_tags'] = mood_tags
    
    # Extraire les tags de mood depuis ab:hi:mood:* (scores)
    for tag_name, tag_values in tags.items():
        if isinstance(tag_name, str) and 'ab:hi:mood' in tag_name and tag_name != 'ab:mood':
            if isinstance(tag_values, list) and tag_values:
                mood_score = float(tag_values[0])
                # Extraire le nom du mood depuis le tag
                mood_name = tag_name.split(':')[-1]
                logger.info(f"Mood score trouvé: {mood_name} = {mood_score}")
                
                # Mapper les moods vers les caractéristiques
                mood_mapping = {
                    'happy': 'mood_happy',
                    'sad': 'mood_relaxed',
                    'relaxed': 'mood_relaxed',
                    'aggressive': 'mood_aggressive',
                    'party': 'mood_party',
                    'energetic': 'mood_party',
                    'calm': 'mood_relaxed',
                }
                
                for mood_key, feature_key in mood_mapping.items():
                    if mood_key in mood_name.lower():
                        features[feature_key] = mood_score
                        logger.info(f"Mood score mappé: {mood_name} ({mood_score}) -> {feature_key}")
    
    # Extraire les tags de genre depuis ab:hi:genre:* et ab:genre
    genre_tags = []
    
    # Extraire depuis ab:genre (liste de genres)
    if 'ab:genre' in tags:
        genre_values = tags['ab:genre']
        if isinstance(genre_values, list):
            genre_tags.extend(genre_values)
        elif genre_values:
            genre_tags.append(genre_values)
        logger.info(f"Genres trouvés dans ab:genre: {genre_tags}")
    
    # Extraire depuis ab:hi:genre:* (scores)
    for tag_name, tag_values in tags.items():
        if isinstance(tag_name, str) and 'ab:hi:genre' in tag_name and tag_name != 'ab:genre':
            if isinstance(tag_values, list) and tag_values:
                genre_score = float(tag_values[0])
                # Extraire le nom du genre depuis le tag
                genre_name = tag_name.split(':')[-1]
                logger.info(f"Genre score trouvé: {genre_name} = {genre_score}")
                genre_tags.append(genre_name)
    
    features['genre_tags'] = genre_tags
    
    # Extraire les caractéristiques numériques
    for tag_name, feature_key in tag_mapping.items():
        if tag_name in tags:
            value = tags[tag_name]
            if isinstance(value, list) and value:
                value = value[0]
            
            # Conversion selon le type de caractéristique
            if feature_key == 'bpm':
                try:
                    features[feature_key] = int(float(value))
                    logger.info(f"BPM extrait: {features[feature_key]}")
                except (ValueError, TypeError):
                    pass
            elif feature_key == 'key':
                features[feature_key] = str(value) if value else None
                logger.info(f"Key extraite: {features[feature_key]}")
            elif feature_key in ['danceability', 'acoustic', 'instrumental', 'tonal']:
                try:
                    # Normaliser les valeurs textuelles
                    if isinstance(value, str):
                        value_lower = value.lower()
                        if value_lower in ['true', 'yes', '1', 'danceable', 'acoustic', 'instrumental']:
                            features[feature_key] = 1.0
                        elif value_lower in ['false', 'no', '0', 'not danceable', 'not acoustic', 'not instrumental']:
                            features[feature_key] = 0.0
                    else:
                        features[feature_key] = float(value)
                    logger.info(f"{feature_key} extrait: {features[feature_key]}")
                except (ValueError, TypeError):
                    pass
    
    # Déduire la scale depuis la key si disponible
    if features['key']:
        key = features['key']
        # Déduction basique de la scale (à améliorer)
        minor_keys = ['Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm']
        features['scale'] = 'minor' if key in minor_keys else 'major'
    
    logger.info(f"Features AcoustID extraites: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
    return features


async def extract_audio_features(audio, tags, file_path: str = None, track_id: int = None):
    """
    Extrait les caractéristiques audio en fusionnant les tags AcoustID et standards,
    puis Librosa en fallback.
    
    Les tags AcoustID et standards sont fusionnés pour maximiser les données extraites.
    Les tags standards (bpm, key, etc.) sont prioritaires sur les tags AcoustID
    car ils sont souvent plus précis.
    
    Args:
        audio: Objet audio (non utilisé, conservé pour compatibilité)
        tags: Tags sérialisés du fichier audio
        file_path: Chemin vers le fichier audio (requis pour fallback Librosa)
        track_id: ID de la track
        
    Returns:
        Dictionnaire des caractéristiques audio extraites
    """
    # === DIAGNOSTIC: LOG DÉTAILLÉ D'ENTRÉE ===
    logger.info(f"=== extract_audio_features appelé pour track {track_id} ===")
    logger.info(f"File path: {file_path}")
    logger.info(f"Audio object type: {type(audio)}")
    logger.info(f"Audio object is None: {audio is None}")
    logger.info(f"Tags parameter type: {type(tags)}")
    logger.info(f"Tags is None: {tags is None}")
    logger.info(f"Tags is empty dict: {tags == {}}")
    
    if tags:
        logger.info(f"Nombre de tags: {len(tags)}")
        logger.info(f"Toutes les clés de tags: {list(tags.keys())}")
        
        # Recherche de tags audio spécifiques
        audio_related_keys = [k for k in tags.keys() if any(term in str(k).upper() for term in ['BPM', 'KEY', 'TEMPO', 'MOOD', 'DANCE', 'ENERGY', 'ACOUSTIC', 'AB:'])]
        logger.info(f"Clés liées à l'audio trouvées: {audio_related_keys}")
        
        # Afficher les valeurs des tags audio trouvés
        for key in audio_related_keys[:5]:  # Limiter à 5 pour éviter les logs trop longs
            logger.info(f"  Tag '{key}': {tags[key]}")
    else:
        logger.warning(f"⚠️  AUCUN TAGS fourni pour track {track_id}!")
    
    # Initialiser les features avec des valeurs par défaut
    features = {
        "bpm": None,
        "key": None,
        "scale": None,
        "danceability": None,
        "mood_happy": None,
        "mood_aggressive": None,
        "mood_party": None,
        "mood_relaxed": None,
        "instrumental": None,
        "acoustic": None,
        "tonal": None,
        "genre_tags": [],
        "mood_tags": []
    }
    
    # ÉTAPE 1: Extraire depuis les tags AcoustID (genres, moods, etc.)
    if tags and _has_valid_acoustid_tags(tags):
        logger.info(f"📋 Extraction depuis les tags AcoustID pour track {track_id}")
        acoustid_features = _extract_features_from_acoustid_tags(tags)
        
        logger.info(f"🔍 DEBUG - Features AcoustID extraites: {acoustid_features}")
        
        # Fusionner les features AcoustID (genres et moods sont importants)
        for key, value in acoustid_features.items():
            if value is not None and value != []:
                # Les genres et moods sont fusionnés (concaténation des listes)
                if key in ['genre_tags', 'mood_tags']:
                    if isinstance(value, list):
                        features[key].extend(value)
                    else:
                        features[key].append(value)
                # Les autres features sont prises si non définies
                elif features.get(key) is None:
                    features[key] = value
        
        logger.info(f"✅ Features AcoustID fusionnées pour track {track_id}")
    else:
        logger.info(f"ℹ️  Pas de tags AcoustID valides pour track {track_id}")
    
    # ÉTAPE 2: Extraire depuis les tags standards (bpm, key, etc.)
    # Les tags standards sont PRIORITAIRES sur les tags AcoustID
    if tags and _has_valid_audio_tags(tags):
        logger.info(f"🎼 Extraction depuis les tags standards pour track {track_id}")
        standard_features = _extract_features_from_standard_tags(tags)
        
        logger.info(f"🔍 DEBUG - Features standards extraites: {standard_features}")
        
        # Fusionner les features standards (priorité sur AcoustID)
        for key, value in standard_features.items():
            if value is not None and value != []:
                # Les genres et moods sont fusionnés (concaténation des listes)
                if key in ['genre_tags', 'mood_tags']:
                    if isinstance(value, list):
                        features[key].extend(value)
                    else:
                        features[key].append(value)
                # Les autres features écrasent les valeurs AcoustID
                else:
                    features[key] = value
        
        logger.info(f"✅ Features standards fusionnées pour track {track_id}")
    else:
        logger.info(f"ℹ️  Pas de tags audio standards valides pour track {track_id}")
    
    # Nettoyer les doublons dans les listes
    features['genre_tags'] = list(set(features['genre_tags'])) if features['genre_tags'] else []
    features['mood_tags'] = list(set(features['mood_tags'])) if features['mood_tags'] else []
    
    # Vérifier si nous avons des données utiles
    has_useful_data = any([
        features.get('bpm') is not None,
        features.get('key') is not None,
        features.get('danceability') is not None,
        features.get('acoustic') is not None,
        features.get('instrumental') is not None,
        features.get('genre_tags'),
        features.get('mood_tags'),
    ])
    
    if has_useful_data:
        logger.info(f"✅ Features extraites pour track {track_id}: BPM={features.get('bpm')}, Key={features.get('key')}")
        logger.info(f"🎵 Champs audio extraits: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
        
        # Mettre à jour la track avec les features extraites
        if track_id:
            await _update_track_features_async(track_id, features)
        
        return features
    
    # ÉTAPE 3: Fallback avec Librosa si les tags ne sont pas disponibles ou incomplets
    if file_path and track_id:
        logger.info(f"🎵 Fallback Librosa pour track {track_id}")
        try:
            features = await analyze_audio_with_librosa(track_id, file_path)
            
            if features:
                logger.info(f"✅ Features extraites avec Librosa pour track {track_id}: BPM={features.get('bpm')}, Key={features.get('key')}")
                logger.info(f"🎵 Champs audio extraits: {[(k, v) for k, v in features.items() if v is not None and v != []]}")
                return features
            else:
                logger.warning(f"⚠️  Aucune feature extraite avec Librosa pour track {track_id}")
        except Exception as e:
            logger.error(f"❌ Erreur extraction Librosa pour track {track_id}: {str(e)}")
    else:
        logger.error(f"❌ Paramètres manquants pour fallback Librosa: file_path={file_path}, track_id={track_id}")
    
    # ÉTAPE 4: Retourner des valeurs par défaut si tout échoue
    logger.warning(f"⚠️  Retour valeurs par défaut pour track {track_id}")
    return {
        "bpm": None,
        "key": None,
        "scale": None,
        "danceability": None,
        "mood_happy": None,
        "mood_aggressive": None,
        "mood_party": None,
        "mood_relaxed": None,
        "instrumental": None,
        "acoustic": None,
        "tonal": None,
        "genre_tags": [],
        "mood_tags": []
    }

# Note: retry_failed_updates function removed as Celery handles task retries
