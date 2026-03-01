# TODO — Fix: Désynchronisation TrackCreate / TrackAudioFeatures

## Contexte
Erreur `AttributeError: 'TrackCreate' object has no attribute 'bpm'` lors de la mutation
GraphQL `create_tracks`. Les champs audio (`bpm`, `key`, `scale`, etc.) ont été migrés
vers la table `track_audio_features` mais le service et les mutations n'ont pas été mis à jour.

## Étapes

- [x] Analyse des fichiers concernés
- [x] 1. `backend/api/schemas/tracks_schema.py` — Ajout champs audio optionnels à `TrackBase`
- [x] 2. `backend/api/services/track_service.py` — Correction `create_track` et `_create_tracks_batch_optimized`
- [x] 3. `backend/api/graphql/queries/mutations/track_mutations.py` — Correction constructeurs `TrackType`
- [x] 4. `backend/api/graphql/types/tracks_type.py` — Ajout `file_mtime`/`file_size` à `TrackCreateInput`
- [x] 5. Tests unitaires — 5/5 passent (`tests/unit/test_track_audio_features_creation.py`)
- [x] 6. Tests GraphQL — 3/3 passent (`scripts/test_graphql_track_mutation.py`)
- [x] 7. Commit conventionnel

## Notes
- Bug pré-existant détecté (hors scope) : `column track_mir_raw.features_raw does not exist`
  → Désynchronisation modèle MIR / migration DB, à corriger séparément

## Fichiers impactés
- `backend/api/schemas/tracks_schema.py`
- `backend/api/services/track_service.py`
- `backend/api/graphql/queries/mutations/track_mutations.py`
- `backend/api/graphql/types/tracks_type.py`
- `tests/unit/test_track_audio_features_creation.py` (nouveau)
