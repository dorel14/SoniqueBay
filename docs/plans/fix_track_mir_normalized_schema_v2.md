# Fix: Correction du schéma track_mir_normalized

## Problème identifié

Le modèle SQLAlchemy `TrackMIRNormalized` attendait des colonnes différentes de celles créées par la migration `b2c3d4e5f6g7_add_mir_tables.py`, causant l'erreur :

```
column track_mir_normalized.bpm does not exist
```

### Colonnes attendues par le modèle (nouveau schéma)

- `bpm`, `key`, `scale`, `danceability`
- `mood_happy`, `mood_aggressive`, `mood_party`, `mood_relaxed`
- `instrumental`, `acoustic`, `tonal`
- `genre_main`, `genre_secondary`, `camelot_key`
- `confidence_score`, `normalized_at`

### Colonnes créées par la migration (ancien schéma)

- `loudness`, `tempo`, `energy`, `valence`, `acousticness`, `instrumentalness`
- `speechiness`, `liveness`, `dynamic_range`, `spectral_complexity`
- `harmonic_complexity`, `perceptual_roughness`, `auditory_roughness`
- `normalization_source`, `normalization_version`, `normalization_date`

## Solution implémentée

### 1. Migration Alembic

Création de `alembic/versions/add_mir_norm_cols.py` qui ajoute :

- Toutes les colonnes du nouveau schéma (sauf `danceability` qui existe déjà)
- Les indexes correspondants (uniquement pour le nouveau schéma)
- Conservation des colonnes de l'ancien schéma pour compatibilité

**Note importante :** Le nom de révision a été raccourci de `add_track_mir_normalized_missing_columns` à `add_mir_norm_cols` pour respecter la limite de 32 caractères de la colonne `alembic_version.version_num`.

### 2. Modèle SQLAlchemy mis à jour

Mise à jour de `backend/api/models/track_mir_normalized_model.py` pour inclure :

- Toutes les colonnes du nouveau schéma
- Toutes les colonnes de l'ancien schéma (conservées)
- Tous les indexes nécessaires (avec commentaires pour les indexes existants)

### 3. Tests unitaires

Création de `tests/unit/test_track_mir_normalized_migration.py` pour valider :

- Présence de toutes les colonnes du nouveau schéma
- Présence de toutes les colonnes de l'ancien schéma
- Fonctionnement de `to_dict()` avec toutes les colonnes
- Structure correcte de la migration

## Fichiers modifiés/créés

```
alembic/versions/add_mir_norm_cols.py                    (nouveau)
backend/api/models/track_mir_normalized_model.py         (modifié)
tests/unit/test_track_mir_normalized_migration.py      (nouveau)
docs/plans/fix_track_mir_normalized_schema_v2.md       (nouveau)
```

## Application de la migration

Pour appliquer la migration sur la base de données :

```bash
# Vérifier l'état des migrations
alembic current

# Appliquer la migration
alembic upgrade add_mir_norm_cols

# Vérifier que la migration a été appliquée
alembic current
```

## Résultat

Après application de la migration :

- La table `track_mir_normalized` contient toutes les colonnes du nouveau schéma
- Les colonnes de l'ancien schéma sont conservées pour compatibilité
- Tous les indexes sont créés pour optimiser les requêtes
- Les services MIR peuvent maintenant fonctionner correctement

## Tests

Les tests unitaires valident :

- ✅ Présence des colonnes du nouveau schéma
- ✅ Présence des colonnes de l'ancien schéma
- ✅ Méthode `to_dict()` fonctionnelle
- ✅ Méthode `__repr__()` fonctionnelle
- ✅ Fichier de migration existant
- ✅ Révision parente correcte
- ✅ Toutes les colonnes requises dans la migration
- ✅ Tous les indexes requis dans la migration

```bash
# Exécuter les tests
python -m pytest tests/unit/test_track_mir_normalized_migration.py -v
```

Résultat : **8 passed**

## Notes de correction

### Corrections apportées après les tests initiaux

1. **Colonne `danceability`** : Retirée de la migration car elle existe déjà dans l'ancien schéma
2. **Indexes de l'ancien schéma** : Retirés de la migration car ils existent déjà (`tempo`, `energy`, `valence`, `danceability`)
3. **Nom de révision** : Raccourci de `add_track_mir_normalized_missing_columns` (38 caractères) à `add_mir_norm_cols` (16 caractères) pour respecter la limite de 32 caractères de PostgreSQL
