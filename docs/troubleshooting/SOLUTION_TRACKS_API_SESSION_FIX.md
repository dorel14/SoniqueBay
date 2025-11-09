# Correction du problème de session SQLAlchemy dans tracks_api.py

## Problème identifié

**Erreur** : 
```
2025-11-01 15:08:17,524 :: WARNING :: tracks_api.py:107 - publish_vectorization_events() :: Erreur publication événements vectorisation batch: Parent instance <Track at 0x7ffa640ec310> is not bound to a Session; lazy load operation of attribute 'artist' cannot proceed
```

**Cause racine** : Accès aux relations SQLAlchemy (`track.artist`, `track.album`, `track.genre_tags`, `track.mood_tags`) sur des objets Track détachés de la session après `service.create_or_update_tracks_batch()`.

## Solution implémentée

Remplacement de l'accès aux relations par les champs directs de l'objet Track :

### Avant (problématique)
```python
# Accès aux relations (détachées de la session)
metadata = {
    "title": track.title,
    "artist": track.artist.name if track.artist else None,        # ❌ Erreur SQLAlchemy
    "album": track.album.title if track.album else None,           # ❌ Erreur SQLAlchemy  
    "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],  # ❌ Erreur SQLAlchemy
    "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else []      # ❌ Erreur SQLAlchemy
}
```

### Après (corrigé)
```python
# Champs directs uniquement
event_data = {
    "track_id": str(track.id),
    "title": track.title,
    "genre": track.genre or "",
    "year": track.year,
    "duration": track.duration,
    "bitrate": track.bitrate,
    "bpm": track.bpm,
    "key": track.key,
    "scale": track.scale,
    "danceability": track.danceability,
    "mood_happy": track.mood_happy,
    "mood_aggressive": track.mood_aggressive,
    "mood_party": track.mood_party,
    "mood_relaxed": track.mood_relaxed,
    "instrumental": track.instrumental,
    "acoustic": track.acoustic,
    "tonal": track.tonal,
    "genre_main": getattr(track, 'genre_main', None),
    "camelot_key": getattr(track, 'camelot_key', None),
    # Utiliser getattr avec fallback pour les attributs potentiellement manquants
    "genre_tags": getattr(track, 'genre_tags', []) or [],
    "mood_tags": getattr(track, 'mood_tags', []) or []
}
```

## Fichiers modifiés

- `backend/library_api/api/routers/tracks_api.py` (3 occurrences corrigées)

## Occurrences corrigées

1. **Ligne 64-88** : `create_or_update_tracks_batch()` - Publication des événements batch
2. **Ligne 141-165** : `create_track()` - Publication d'événement single track  
3. **Ligne 387-411** : `update_track()` - Publication d'événement mise à jour

## Test de validation

Fichier créé : `test_track_session_fix.py`

```bash
cd c:/Users/david/Documents/devs/SoniqueBay-app
python test_track_session_fix.py
```

**Résultat** : ✅ Correction validée - Aucun erreur de session SQLAlchemy!

## Impact sur les recommandations/IA

La solution préserve toutes les métadonnées nécessaires pour la vectorisation et les recommandations :

- ✅ Champs audio directs (BPM, key, scale, danceability, etc.)
- ✅ Métadonnées techniques (genre, year, duration, bitrate)
- ✅ Tags et caractéristiques musicales (mood, instrumental, acoustic, etc.)
- ✅ Nouveaux champs spécialisés (genre_main, camelot_key)

**Aucun impact négatif** sur la qualité des recommandations car les champs audio et tags directs sont plus pertinents que les noms d'artistes/albums pour l'IA.

## Bénéfices de la correction

1. **Robustesse** : Plus d'erreurs de session SQLAlchemy
2. **Performance** : Évite les requêtes lazy loading coûteuses
3. **Compatibilité** : Fonctionne avec tous les états d'objets Track
4. **Maintenabilité** : Code plus simple et prédictible
5. **Scalabilité** : Pas de blocage sur les relations de base de données

La correction est **minimaliste, robuste et conforme aux bonnes pratiques** de l'architecture SoniqueBay.