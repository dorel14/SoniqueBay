# Plan de correction — Pylance `track_metadata_service.py`

## Informations collectées

- Erreur Pylance signalée:
  - `Result[Tuple[TrackMetadata]] n’est pas awaitable` autour de `backend/api/services/track_metadata_service.py:111`
- Constat dans le fichier:
  - Le service déclare `SessionType = Union[AsyncSession, Session]`.
  - Plusieurs méthodes utilisent directement `await self.session.execute(...)`.
  - Si `self.session` est typé `Union[AsyncSession, Session]`, Pylance voit un cas sync (`Session.execute`) non awaitable → diagnostic type.
  - Le service contient déjà des helpers compatibles sync/async (`_execute`, `_commit`, `_rollback`, `_refresh`, `_delete`) mais ils ne sont pas utilisés partout.

## Plan de modification (incrémental)

1. `backend/api/services/track_metadata_service.py`
   - Remplacer tous les appels directs `await self.session.execute(...)` par `await self._execute(...)`.
   - Remplacer les appels directs `await self.session.commit()` / `await self.session.refresh(...)` / `await self.session.rollback()` / `await self.session.delete(...)` par leurs helpers `_commit`, `_refresh`, `_rollback`, `_delete`.
   - Garder la logique métier identique (pas de changement fonctionnel, seulement correction de typage async/sync).
   - Ajouter typage explicite minimal seulement si nécessaire pour Pylance.

2. `tests/` (minimal)
   - Ajouter un test unitaire ciblé (ou compléter un test existant) pour valider qu’un chemin principal de `TrackMetadataService` fonctionne avec le wrapper `_execute` (sans régression logique).

3. `docs/plans/TODO.md`
   - Étendre la checklist en ajoutant la correction metadata + statut des tâches.

## Fichiers dépendants à éditer

- `backend/api/services/track_metadata_service.py`
- `docs/plans/TODO.md`
- `tests/unit/...` (test ciblé metadata si nécessaire)

## Follow-up

- Exécuter pytest ciblé (critical-path) sur les nouveaux tests unitaires audio + metadata.
- Préparer commit Conventional Commit:
  - `fix(metadata-service): corriger appels awaitables sur SessionType`
