# TODO — Fix: Désynchronisation TrackMIRRaw modèle / migration DB

## Contexte
Erreur `column track_mir_raw.features_raw does not exist` — la migration Alembic
`b2c3d4e5f6g7_add_mir_tables.py` a créé la table `track_mir_raw` avec des noms de
colonnes différents de ceux définis dans le modèle SQLAlchemy `TrackMIRRaw`.

## Désynchronisation détectée

| Colonne DB (migration) | Colonne Modèle | Action |
|---|---|---|
| `extractor` (NOT NULL) | `mir_source` (nullable) | Renommage + DROP NOT NULL |
| `version` | `mir_version` | Renommage |
| `tags_json` | `features_raw` | Renommage |
| `created_at` | `analyzed_at` | Renommage |
| `raw_data_json` | *(absent)* | Suppression |
| `extraction_time` | *(absent)* | Suppression |
| `confidence` | *(absent)* | Suppression |
| UniqueConstraint(`track_id`, `extractor`) | UniqueConstraint(`track_id`) | Correction |
| Index `idx_track_mir_raw_extractor` | Index `idx_track_mir_raw_source` | Correction |
| Index `idx_track_mir_raw_confidence` | Index `idx_track_mir_raw_analyzed_at` | Correction |

## Bugs secondaires dans le code applicatif

| Fichier | Problème |
|---|---|
| `tracks_type.py` résolveur `mir_raw` | Accède à `raw.bpm`, `raw.key`, `raw.analysis_source`… inexistants dans le modèle |
| `track_mir_queries.py` `_mir_raw_to_type` | Utilise `mir_raw.created_at` au lieu de `mir_raw.analyzed_at` |
| `track_mir_mutations.py` `create_track_mir_raw` | Utilise `mir_raw.created_at` au lieu de `mir_raw.analyzed_at` |

## Étapes

- [x] Analyse des fichiers concernés
- [x] 1. `alembic/versions/fix_track_mir_raw_schema.py` — Nouvelle migration (merge 2 heads)
- [x] 2. `backend/api/graphql/types/tracks_type.py` — Corriger résolveur `mir_raw`
- [x] 3. `backend/api/graphql/queries/track_mir_queries.py` — Corriger `_mir_raw_to_type`
- [x] 4. `backend/api/graphql/mutations/track_mir_mutations.py` — Corriger `create_track_mir_raw`
- [x] 5. `tests/unit/test_track_mir_raw_model.py` — Nouveau test unitaire (21/21 ✅)
- [x] 6. Commit conventionnel (`f5d5f1a`)

## Fichiers impactés
- `alembic/versions/fix_track_mir_raw_schema.py` (nouveau)
- `backend/api/graphql/types/tracks_type.py`
- `backend/api/graphql/queries/track_mir_queries.py`
- `backend/api/graphql/mutations/track_mir_mutations.py`
- `tests/unit/test_track_mir_raw_model.py` (nouveau)
