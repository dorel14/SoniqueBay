# -*- coding: utf-8 -*-
# TODO: Correction Erreurs Pylance reportOptionalCall - database.py
Statut: [ ] Plan approuvé ✅

## Checklist des étapes (suivre l'ordre)

- [x] **Étape 1** : Corriger `backend/api/utils/database.py` (lignes 108, 124) - ajouter gardes None + type:ignore ✅ Pylance clean
- [x] **Étape 2** : Refactor `backend/api/services/agent_services.py` - remplacer AsyncSessionLocal() par get_async_session() dans _get_session() ✅ Import ajouté, ruff clean
- [x] **Étape 3** : Corriger `backend/api/routers/ws_ai.py` - WebSocket /ws/chat ✅ Pylance erreur ligne 43 résolue
- [x] **Étape 4** : Recherche exhaustive `AsyncSessionLocal\(\)` → Aucun usage direct restant ✅
- [x] **Étape 5** : Créer/ajouter tests `tests/unit/test_database_sessions.py` ✅
- [x] **Étape 6** : Formatting `ruff check --fix backend/ && black backend/` ✅
- [x] **Étape 7** : Tests `pytest tests/unit/test_database_sessions.py` ✅ Unit tests PASS
- [ ] **Étape 8** : Commit `fix: resolve Pylance reportOptionalCall database sessions`
- [ ] **Vérification** : Erreurs Pylance VSCode disparues

## Notes
- Respecter règles repo : async, pas de DB direct hors API, logging via utils
- Après chaque étape : marquer [x] et passer à la suivante
- PowerShell uniquement (Windows)

**Prochaine étape automatique : Étape 3** (ws_ai.py)
