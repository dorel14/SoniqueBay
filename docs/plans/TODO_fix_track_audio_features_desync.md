# TODO — Fix: Désynchronisation TrackCreate / TrackAudioFeatures

## Contexte
Erreur `AttributeError: 'TrackCreate' object has no attribute 'bpm'` lors de la mutation
GraphQL `create_tracks`. Les champs audio (`bpm`, `key`, `scale`, etc.) ont été migrés
vers la table `track_audio_features` mais le service et les mutations n'ont pas été mis à jour.

## Étapes

- [x] Analyse des fichiers concernés
- [ ] 1. `backend/api/schemas/tracks_schema.py` — Ajouter les champs audio optionnels à `TrackBase`
- [ ] 2. `backend/api/services/track_service.py` — Corriger `create_track` et `_create_tracks_batch_optimized`
- [ ] 3. `backend/api/graphql/queries/mutations/track_mutations.py` — Corriger les constructeurs `TrackType`
- [ ] 4. `backend/api/graphql/types/tracks_type.py` — Ajouter `file_mtime`/`file_size` à `TrackCreateInput`
- [ ] 5. Tests unitaires — Valider la création de tracks avec audio features
- [ ] 6. Commit conventionnel

## Fichiers impactés
- `backend/api/schemas/tracks_schema.py`
- `backend/api/services/track_service.py`
- `backend/api/graphql/queries/mutations/track_mutations.py`
- `backend/api/graphql/types/tracks_type.py`
- `tests/unit/test_track_audio_features_creation.py` (nouveau)
