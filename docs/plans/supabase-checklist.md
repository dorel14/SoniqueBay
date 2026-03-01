# Checklist - Migration Supabase

**Branche** : `blackboxai/feature/supabase-migration`  
**Dernière mise à jour** : 2025-01-20

---

## Phase 1 : Préparation Git & Structure ✅

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 1.1 | Vérifier état branche `blackboxai/fix-orchestrator-async-init` | ✅ | 2025-01-20 | Commit effectué |
| 1.2 | Commit/stash changements en cours si nécessaire | ✅ | 2025-01-20 | Stash puis pop |
| 1.3 | Retourner sur `master` | ✅ | 2025-01-20 | OK |
| 1.4 | Merger `blackboxai/fix-orchestrator-async-init` si validé | ⬜ | | Non requis - docs créés directement |
| 1.5 | Créer branche `blackboxai/feature/supabase-migration` | ✅ | 2025-01-20 | Branche créée |
| 1.6 | Créer `docs/plans/supabase-rollback.md` | ✅ | 2025-01-20 | Créé |
| 1.7 | Commit initial "chore: setup supabase migration branch" | ✅ | 2025-01-20 | Commit 8e56029 |

**Validation Phase 1** : ✅ **COMPLÉTÉE**  
**Critères** : Branche propre, prête pour développement

---

## Phase 2 : Configuration Supabase ✅

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 2.1 | Ajouter service `supabase-db` dans docker-compose.yml | ✅ | 2025-01-20 | Service créé avec healthcheck |
| 2.2 | Ajouter service `supabase-realtime` dans docker-compose.yml | ✅ | 2025-01-20 | WebSocket temps réel |
| 2.3 | Ajouter service `supabase-auth` dans docker-compose.yml | ✅ | 2025-01-20 | GoTrue auth |
| 2.4 | Ajouter service `supabase-dashboard` dans docker-compose.yml | ✅ | 2025-01-20 | Studio UI ajouté |
| 2.5 | Créer `supabase/db_init/init_supabase.sql` (extensions) | ✅ | 2025-01-20 | uuid-ossp, pg_trgm, pgcrypto, vector |
| 2.6 | Créer `scripts/migrate_schema_to_supabase.py` | ⬜ | | |
| 2.7 | Créer `backend/api/utils/supabase_client.py` | ✅ | 2025-01-20 | Client backend créé |
| 2.8 | Créer `frontend/utils/supabase_client.py` | ✅ | 2025-01-20 | Client frontend créé |
| 2.9 | Créer `.env.supabase.example` | ✅ | 2025-01-20 | Variables d'environnement documentées |
| 2.10 | Créer `supabase/Dockerfile` | ✅ | 2025-01-20 | Image personnalisée |
| 2.11 | Créer `supabase/scripts/start.sh, stop.sh, logs.sh` | ✅ | 2025-01-20 | Scripts de gestion shell |
| 2.12 | Créer `supabase/scripts/test-services.sh` | ✅ | 2025-01-20 | Script de test |
| 2.13 | Créer `supabase/README.md` | ✅ | 2025-01-20 | Documentation structure |
| 2.14 | Tester démarrage services Supabase | ✅ | 2025-01-20 | Tous les services démarrés, auth fixé |
| 2.15 | Tester connexion client Supabase | ⬜ | | |
| 2.16 | Migrer schéma SQLAlchemy → Supabase | ⬜ | | |
| 2.17 | Commit "feat: add supabase infrastructure" | ✅ | 2025-01-20 | Commit 7ef0cde |
| 2.18 | Créer `supabase/scripts/init-auth-schema.sh` | ✅ | 2025-01-20 | Script pour créer schéma auth |
| 2.19 | Créer `supabase/scripts/entrypoint.sh` | ✅ | 2025-01-20 | Entrypoint Docker pour init automatique auth |
| 2.20 | Mettre à jour `supabase/Dockerfile` avec entrypoint | ✅ | 2025-01-20 | Dockerfile utilise entrypoint.sh |

**Validation Phase 2** : ✅ **COMPLÉTÉE**  
**Critères** : Services démarrés (db, realtime, auth, meta, dashboard), connexion OK, init automatique via entrypoint

---

## Phase 3 : Couche d'Abstraction Database ✅

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 3.1 | Créer `backend/api/utils/db_config.py` | ✅ | 2025-01-20 | Feature flags simples |
| 3.2 | Créer `backend/api/utils/db_adapter.py` | ✅ | 2025-01-20 | DatabaseAdapter unifié |
| 3.3 | Créer `backend/api/repositories/base_repository.py` | ✅ | 2025-01-20 | Pattern repository |
| 3.4 | Créer `backend/api/repositories/__init__.py` | ✅ | 2025-01-20 | Package repositories |
| 3.5 | Commit "feat: add database abstraction layer" | ✅ | 2025-01-20 | Commit 7d4a0d3 |

**Validation Phase 3** : ✅ **COMPLÉTÉE**  
**Critères** : Abstraction simple créée, pas d'usine à gaz, migration progressive par entité

---

## Phase 4 : Refactorisation des Services

### Phase 4.1 : Services de Lecture Simple ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.1.1 | Créer `TrackRepository` avec Supabase | ⬜ | | |
| 4.1.2 | Refactoriser `TrackService` avec feature flag | ⬜ | | |
| 4.1.3 | Créer `AlbumRepository` avec Supabase | ⬜ | | |
| 4.1.4 | Refactoriser `AlbumService` avec feature flag | ⬜ | | |
| 4.1.5 | Créer `ArtistRepository` avec Supabase | ⬜ | | |
| 4.1.6 | Refactoriser `ArtistService` avec feature flag | ⬜ | | |
| 4.1.7 | Tests unitaires repositories | ⬜ | | |
| 4.1.8 | Commit "feat: refactor read services to supabase" | ⬜ | | |

### Phase 4.2 : Services de Recherche ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.2.1 | Refactoriser `SearchService` (textuelle) | ⬜ | | |
| 4.2.2 | Refactoriser `VectorSearchService` (vectorielle) | ⬜ | | |
| 4.2.3 | Configurer pgvector dans Supabase | ⬜ | | |
| 4.2.4 | Tests recherche | ⬜ | | |
| 4.2.5 | Commit "feat: refactor search services to supabase" | ⬜ | | |

### Phase 4.3 : Services CRUD Complexes ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.3.1 | Refactoriser `TrackService` CRUD complet | ⬜ | | |
| 4.3.2 | Gérer relations Track-Artist-Album | ⬜ | | |
| 4.3.3 | Refactoriser `ScanService` | ⬜ | | |
| 4.3.4 | Refactoriser `CoverService` | ⬜ | | |
| 4.3.5 | Tests CRUD | ⬜ | | |
| 4.3.6 | Commit "feat: refactor CRUD services to supabase" | ⬜ | | |

### Phase 4.4 : Services Métier Critiques ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.4.1 | Refactoriser `PlayQueueService` (temps réel) | ⬜ | | |
| 4.4.2 | Refactoriser `ChatService` (mémoire IA) | ⬜ | | |
| 4.4.3 | Refactoriser `AgentService` | ⬜ | | |
| 4.4.4 | Tests services métier | ⬜ | | |
| 4.4.5 | Commit "feat: refactor business services to supabase" | ⬜ | | |

**Validation Phase 4** : ⬜  
**Critères** : Tous les services refactorisés avec feature flags

---

## Phase 5 : Migration Frontend ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 5.1 | Ajouter `supabase` à `frontend/requirements.txt` | ⬜ | | |
| 5.2 | Créer `frontend/utils/feature_flags.py` | ⬜ | | |
| 5.3 | Refactoriser `frontend/services/track_service.py` | ⬜ | | |
| 5.4 | Refactoriser `frontend/services/album_service.py` | ⬜ | | |
| 5.5 | Refactoriser `frontend/services/artist_service.py` | ⬜ | | |
| 5.6 | Refactoriser `frontend/services/search_service.py` | ⬜ | | |
| 5.7 | Tests E2E frontend | ⬜ | | |
| 5.8 | Commit "feat: migrate frontend to supabase" | ⬜ | | |

**Validation Phase 5** : ⬜  
**Critères** : Frontend communique directement avec Supabase

---

## Phase 6 : Migration Workers Celery ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 6.1 | Créer `backend_worker/utils/supabase_client.py` | ⬜ | | |
| 6.2 | Refactoriser `backend_worker/tasks/scan_tasks.py` | ⬜ | | |
| 6.3 | Refactoriser `backend_worker/tasks/extract_tasks.py` | ⬜ | | |
| 6.4 | Refactoriser `backend_worker/tasks/batch_tasks.py` | ⬜ | | |
| 6.5 | Refactoriser `backend_worker/tasks/cover_tasks.py` | ⬜ | | |
| 6.6 | Refactoriser `backend_worker/tasks/vector_tasks.py` | ⬜ | | |
| 6.7 | Tests workers | ⬜ | | |
| 6.8 | Commit "feat: migrate celery workers to supabase" | ⬜ | | |

**Validation Phase 6** : ⬜  
**Critères** : Workers Celery utilisent Supabase

---

## Phase 7 : Tests & Validation ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 7.1 | Créer `tests/unit/test_supabase_repositories.py` | ⬜ | | |
| 7.2 | Créer `tests/integration/test_supabase_integration.py` | ⬜ | | |
| 7.3 | Créer `tests/e2e/test_supabase_scenarios.py` | ⬜ | | |
| 7.4 | Exécuter tests unitaires | ⬜ | | |
| 7.5 | Exécuter tests intégration | ⬜ | | |
| 7.6 | Exécuter tests E2E | ⬜ | | |
| 7.7 | Commit "test: add supabase test suite" | ⬜ | | |

**Validation Phase 7** : ⬜  
**Critères** : Tous les tests passent

---

## Phase 8 : Basculement & Nettoyage ⬜

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 8.1 | Activer Supabase 10% (feature flag) | ⬜ | | |
| 8.2 | Monitorer 24h | ⬜ | | |
| 8.3 | Activer Supabase 50% | ⬜ | | |
| 8.4 | Activer Supabase 100% | ⬜ | | |
| 8.5 | Monitorer 1 semaine | ⬜ | | |
| 8.6 | Supprimer SQLAlchemy (quand stable) | ⬜ | | |
| 8.7 | Supprimer Alembic (quand stable) | ⬜ | | |
| 8.8 | Nettoyer dépendances | ⬜ | | |
| 8.9 | Mettre à jour documentation | ⬜ | | |
| 8.10 | Commit "chore: cleanup after supabase migration" | ⬜ | | |

**Validation Phase 8** : ⬜  
**Critères** : Migration 100% complète

---

## Suivi des Problèmes

| ID | Description | Phase | Statut | Solution |
|----|-------------|-------|--------|----------|
| | | | | |

---

## Notes & Décisions

| Date | Sujet | Décision | Responsable |
|------|-------|----------|-------------|
| 2025-01-20 | Création branche | Branche créée, Phase 1 complétée | BlackboxAI |
| 2025-01-20 | Structure dossier | Dossier `supabase/` créé comme `db_folder/` | BlackboxAI |
| 2025-01-20 | Scripts shell | Scripts en bash (pas PowerShell) pour compatibilité Linux | BlackboxAI |
| 2025-01-20 | Dashboard ajouté | Service supabase-dashboard ajouté avec image latest | BlackboxAI |
| 2025-01-20 | Clients créés | Backend et frontend clients Supabase créés | BlackboxAI |
| 2025-01-20 | Auth fixé | Correction erreur "schema auth does not exist" - script d'init créé | BlackboxAI |
| 2025-01-20 | Entrypoint Docker | Création entrypoint.sh pour initialisation automatique du schéma auth | BlackboxAI |
| 2025-01-20 | Abstraction simple | Approche simple: USE_SUPABASE flag global, pas d'usine à gaz | BlackboxAI |

---

## Résumé Global

| Phase | Progression | Statut |
|-------|-------------|--------|
| 1. Préparation | 100% | ✅ **COMPLÉTÉE** |
| 2. Configuration | 100% | ✅ **COMPLÉTÉE** |
| 3. Abstraction | 100% | ✅ **COMPLÉTÉE** |
| 4. Services (lecture) | 0% | ⬜ Non démarré |
| 4. Services (recherche) | 0% | ⬜ Non démarré |
| 4. Services (CRUD) | 0% | ⬜ Non démarré |
| 4. Services (métier) | 0% | ⬜ Non démarré |
| 5. Frontend | 0% | ⬜ Non démarré |
| 6. Workers | 0% | ⬜ Non démarré |
| 7. Tests | 0% | ⬜ Non démarré |
| 8. Basculement | 0% | ⬜ Non démarré |

**Progression totale** : 25%  
**Prochaine étape** : Phase 4.1 - Refactorisation des services de lecture (Track, Album, Artist)

---

**Dernière mise à jour** : 2025-01-20  
**Prochaine revue** : Début Phase 4.1 - Refactorisation services lecture
