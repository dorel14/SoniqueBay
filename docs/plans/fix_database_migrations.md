# Plan de correction des tests de migrations et schéma de base de données

## Problèmes identifiés
- Échec des tests de migration (stamp, upgrade, downgrade, branches)
- Échec des tests de cohérence de schéma (indexes, not_null_constraints)
- Échec des tests de préservation de données (data_types_compatibility)
- Échec des tests d'historique de migration

## Causes probables
1. **Configuration d'Alembic**
   - Problèmes dans le fichier `alembic.ini`
   - Problèmes dans le script `alembic/env.py`
   - Problèmes de détection des changements de schéma

2. **Cohérence des migrations**
   - Conflits entre les branches de migration
   - Migrations manquantes ou incomplètes
   - Problèmes de fusion des têtes de migration

3. **Compatibilité des types de données**
   - Problèmes de conversion de types lors des migrations
   - Problèmes avec les valeurs par défaut
   - Problèmes avec les contraintes NOT NULL

## Plan d'action
1. Vérifier la configuration d'Alembic dans `alembic.ini` et `alembic/env.py`
2. Examiner l'historique des migrations pour identifier les conflits
3. Corriger les migrations problématiques, en particulier:
   - `fix_indexes_for_search_optimization.py`
   - `fix_not_null_constraints.py`
   - `fix_data_types_compatibility.py`
4. Vérifier les migrations de fusion (`merge_heads.py`, `merge_final_heads.py`)
5. Mettre à jour les tests pour refléter le comportement attendu
6. Créer une nouvelle migration pour corriger les problèmes d'index
7. Vérifier la cohérence entre les modèles SQLAlchemy et les migrations
