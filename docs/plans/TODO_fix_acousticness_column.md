
# TODO : Correction colonne acousticness dans track_mir_scores

## Étapes

- [x] Analyser le mismatch entre modèle et DB
- [x] Confirmer la solution avec l'utilisateur
- [x] Créer la migration Alembic pour renommer la colonne
- [x] Mettre à jour l'index composite dans la migration
- [x] Créer les tests unitaires pour valider la migration
- [ ] Exécuter la migration (si demandé)

## Fichiers créés

| Fichier | Description |
|---------|-------------|
| `alembic/versions/fix_track_mir_scores_acousticness.py` | Migration Alembic pour renommer la colonne |
| `tests/unit/test_track_mir_scores_acousticness_migration.py` | Tests unitaires (9 passed, 1 skipped) |
| `docs/plans/TODO_fix_acousticness_column.md` | Ce fichier de suivi |

## Détails techniques

**Problèmes identifiés :**
1. Colonne `acousticness` : DB a `acousticness_score`, modèle attend `acousticness`
2. Colonne `calculated_at` : manquante dans la DB
3. Erreur PostgreSQL : nom de révision trop long (> 32 caractères)

**Solution implémentée :**
Migration Alembic avec :
1. **Nom de révision raccourci** : `fix_mir_acousticness` (18 caractères) au lieu de `fix_track_mir_scores_acousticness` (32 caractères)
2. **Fusion de deux branches** : `add_mir_norm_cols` et `fix_track_mir_raw_schema`
3. **Ajout de la colonne manquante** : `calculated_at` (DateTime, nullable)
4. **Renommage** : `acousticness_score` → `acousticness`
5. **Recréation de l'index** : `idx_track_mir_scores_multi` avec le nouveau nom de colonne

## Application de la migration

Pour appliquer la migration sur la base de données :

```bash
# Vérifier l'état actuel
alembic current

# Appliquer la migration
alembic upgrade fix_mir_acousticness

# Vérifier que la migration a été appliquée
alembic current
```

## Tests

Résultat des tests : **10 passed, 1 skipped**

```bash
python -m pytest tests/unit/test_track_mir_scores_acousticness_migration.py -v
```

Tests couverts :
- ✅ Existence du fichier de migration
- ✅ Nom de révision raccourci (`fix_mir_acousticness`)
- ✅ Fusion des branches parentes
- ✅ Ajout de la colonne `calculated_at`
- ✅ Renommage `acousticness_score` → `acousticness`
- ✅ Gestion de l'index composite
- ✅ Cohérence avec le modèle SQLAlchemy
