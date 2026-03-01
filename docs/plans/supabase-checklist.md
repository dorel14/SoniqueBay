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

## Phase 2 : Configuration Supabase

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
| 2.14 | Tester démarrage services Supabase | ⬜ | | |
| 2.15 | Tester connexion client Supabase | ⬜ | | |
| 2.16 | Migrer schéma SQLAlchemy → Supabase | ⬜ | | |
| 2.17 | Commit "feat: add supabase infrastructure" | ⬜ | | |


**Validation Phase 2** : 🔄 **EN COURS**  
**Critères** : Services démarrés, connexion OK, schéma migré

---

## Phase 3 : Couche d'Abstraction Database

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 3.1 | Créer `backend/api/utils/feature_flags.py` | ⬜ | | |
| 3.2 | Créer `backend/api/repositories/base.py` (classe abstraite) | ⬜ | | |
| 3.3 | Créer `backend/api/utils/db_adapter.py` | ⬜ | | |
| 3.4 | Implémenter `SQLAlchemyAdapter` | ⬜ | | |
| 3.5 | Implémenter `SupabaseAdapter` | ⬜ | | |
| 3.6 | Créer `backend/api/repositories/sqlalchemy/__init__.py` | ⬜ | | |
| 3.7 | Créer `backend/api/repositories/supabase/__init__.py` | ⬜ | | |
| 3.8 | Créer `tests/unit/test_db_adapter.py` | ⬜ | | |
| 3.9 | Tester basculement feature flag | ⬜ | | |
| 3.10 | Commit "feat: add database abstraction layer" | ⬜ | | |

**Validation Phase 3** : ⬜  
**Critères** : Tests passent, basculement fonctionnel

---

## Phase 4.1 : Services de Lecture Simple

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.1.1 | Créer `SupabaseSettingsRepository` | ⬜ | | |
| 4.1.2 | Adapter `SettingsService` avec feature flag | ⬜ | | |
| 4.1.3 | Tests unitaires Settings | ⬜ | | |
| 4.1.4 | Basculement 10% → 100% Settings | ⬜ | | |
| 4.1.5 | Créer `SupabaseTagsRepository` | ⬜ | | |
| 4.1.6 | Adapter `TagsService` avec feature flag | ⬜ | | |
| 4.1.7 | Tests unitaires Tags | ⬜ | | |
| 4.1.8 | Basculement 10% → 100% Tags | ⬜ | | |
| 4.1.9 | Créer `SupabaseGenresRepository` | ⬜ | | |
| 4.1.10 | Adapter `GenresService` avec feature flag | ⬜ | | |
| 4.1.11 | Tests unitaires Genres | ⬜ | | |
| 4.1.12 | Basculement 10% → 100% Genres | ⬜ | | |
| 4.1.13 | Commit "feat: migrate read-only services to supabase" | ⬜ | | |

**Validation Phase 4.1** : ⬜  
**Critères** : Services lecture simple 100% sur Supabase

---

## Phase 4.2 : Services de Recherche

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.2.1 | Créer `SupabaseSearchRepository` (textuelle) | ⬜ | | |
| 4.2.2 | Adapter `SearchService` avec feature flag | ⬜ | | |
| 4.2.3 | Configurer Supabase FTS | ⬜ | | |
| 4.2.4 | Tests recherche textuelle | ⬜ | | |
| 4.2.5 | Basculement recherche textuelle | ⬜ | | |
| 4.2.6 | Créer `SupabaseVectorSearchRepository` | ⬜ | | |
| 4.2.7 | Adapter `VectorSearchService` avec feature flag | ⬜ | | |
| 4.2.8 | Configurer pgvector Supabase | ⬜ | | |
| 4.2.9 | Tests recherche vectorielle | ⬜ | | |
| 4.2.10 | Basculement recherche vectorielle | ⬜ | | |
| 4.2.11 | Commit "feat: migrate search services to supabase" | ⬜ | | |

**Validation Phase 4.2** : ⬜  
**Critères** : Recherche textuelle et vectorielle fonctionnelle

---

## Phase 4.3 : Services CRUD Complexes

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.3.1 | Créer `SupabaseTrackRepository` | ⬜ | | |
| 4.3.2 | Gérer relations Track (Artist, Album, Genres) | ⬜ | | |
| 4.3.3 | Adapter `TrackService` avec feature flag | ⬜ | | |
| 4.3.4 | Tests unitaires Track | ⬜ | | |
| 4.3.5 | Basculement Track | ⬜ | | |
| 4.3.6 | Créer `SupabaseArtistRepository` | ⬜ | | |
| 4.3.7 | Adapter `ArtistService` avec feature flag | ⬜ | | |
| 4.3.8 | Tests unitaires Artist | ⬜ | | |
| 4.3.9 | Basculement Artist | ⬜ | | |
| 4.3.10 | Créer `SupabaseAlbumRepository` | ⬜ | | |
| 4.3.11 | Adapter `AlbumService` avec feature flag | ⬜ | | |
| 4.3.12 | Tests unitaires Album | ⬜ | | |
| 4.3.13 | Basculement Album | ⬜ | | |
| 4.3.14 | Commit "feat: migrate CRUD services to supabase" | ⬜ | | |

**Validation Phase 4.3** : ⬜  
**Critères** : CRUD Tracks, Artists, Albums 100% Supabase

---

## Phase 4.4 : Services Métier Critiques

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 4.4.1 | Créer table `playqueue` temps réel Supabase | ⬜ | | |
| 4.4.2 | Créer `SupabasePlayQueueRepository` | ⬜ | | |
| 4.4.3 | Configurer Supabase Realtime pour PlayQueue | ⬜ | | |
| 4.4.4 | Adapter `PlayQueueService` avec feature flag | ⬜ | | |
| 4.4.5 | Tests PlayQueue temps réel | ⬜ | | |
| 4.4.6 | Basculement PlayQueue | ⬜ | | |
| 4.4.7 | Créer tables `chat_sessions`, `chat_messages` | ⬜ | | |
| 4.4.8 | Créer `SupabaseChatRepository` | ⬜ | | |
| 4.4.9 | Adapter `ChatService` avec feature flag | ⬜ | | |
| 4.4.10 | Tests Chat IA mémoire persistante | ⬜ | | |
| 4.4.11 | Basculement Chat | ⬜ | | |
| 4.4.12 | Créer `SupabaseScanRepository` | ⬜ | | |
| 4.4.13 | Adapter `ScanService` avec feature flag | ⬜ | | |
| 4.4.14 | Tests Scan intégrité données | ⬜ | | |
| 4.4.15 | Basculement Scan | ⬜ | | |
| 4.4.16 | Commit "feat: migrate business services to supabase" | ⬜ | | |

**Validation Phase 4.4** : ⬜  
**Critères** : PlayQueue temps réel, Chat mémoire, Scan OK

---

## Phase 5 : Migration Frontend

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 5.1 | Ajouter `supabase` à `frontend/requirements.txt` | ⬜ | | |
| 5.2 | Créer `frontend/utils/feature_flags.py` | ⬜ | | |
| 5.3 | Créer `frontend/services/supabase/__init__.py` | ⬜ | | |
| 5.4 | Créer `frontend/services/supabase/auth_service.py` | ⬜ | | |
| 5.5 | Créer `frontend/services/supabase/realtime_service.py` | ⬜ | | |
| 5.6 | Créer `frontend/services/supabase/track_service.py` | ⬜ | | |
| 5.7 | Créer `frontend/services/supabase/artist_service.py` | ⬜ | | |
| 5.8 | Créer `frontend/services/supabase/album_service.py` | ⬜ | | |
| 5.9 | Créer `frontend/services/supabase/search_service.py` | ⬜ | | |
| 5.10 | Adapter composants UI pour Supabase | ⬜ | | |
| 5.11 | Tests E2E frontend Supabase | ⬜ | | |
| 5.12 | Basculement frontend 10% → 100% | ⬜ | | |
| 5.13 | Commit "feat: migrate frontend to supabase direct" | ⬜ | | |

**Validation Phase 5** : ⬜  
**Critères** : Frontend communique directement avec Supabase

---

## Phase 6 : Migration Workers Celery

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 6.1 | Créer table `jobs` dans Supabase | ⬜ | | |
| 6.2 | Créer `backend_worker/utils/supabase_client.py` | ⬜ | | |
| 6.3 | Adapter `backend_worker/tasks/scan_tasks.py` | ⬜ | | |
| 6.4 | Adapter `backend_worker/tasks/extract_tasks.py` | ⬜ | | |
| 6.5 | Adapter `backend_worker/tasks/batch_tasks.py` | ⬜ | | |
| 6.6 | Adapter `backend_worker/tasks/cover_tasks.py` | ⬜ | | |
| 6.7 | Adapter `backend_worker/tasks/vector_tasks.py` | ⬜ | | |
| 6.8 | Tests workers avec Supabase | ⬜ | | |
| 6.9 | Basculement workers | ⬜ | | |
| 6.10 | Commit "feat: migrate celery workers to supabase" | ⬜ | | |

**Validation Phase 6** : ⬜  
**Critères** : Workers Celery utilisent Supabase

---

## Phase 7 : Tests & Validation

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 7.1 | Créer `tests/unit/test_supabase_repositories.py` | ⬜ | | |
| 7.2 | Créer `tests/integration/test_supabase_integration.py` | ⬜ | | |
| 7.3 | Créer `tests/e2e/test_supabase_scenarios.py` | ⬜ | | |
| 7.4 | Créer `tests/performance/test_supabase_perf.py` | ⬜ | | |
| 7.5 | Exécuter tests unitaires | ⬜ | | |
| 7.6 | Exécuter tests intégration | ⬜ | | |
| 7.7 | Exécuter tests E2E (scan → index → recherche → lecture) | ⬜ | | |
| 7.8 | Exécuter benchmarks performance | ⬜ | | |
| 7.9 | Comparer performances avant/après | ⬜ | | |
| 7.10 | Commit "test: add supabase test suite" | ⬜ | | |

**Validation Phase 7** : ⬜  
**Critères** : Tous les tests passent, performance OK

---

## Phase 8 : Basculement & Nettoyage

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 8.1 | Activer Supabase 10% (feature flag) | ⬜ | | |
| 8.2 | Monitorer 24h | ⬜ | | |
| 8.3 | Activer Supabase 50% | ⬜ | | |
| 8.5 | Activer Supabase 100% | ⬜ | | |
| 8.6 | Monitorer 1 semaine | ⬜ | | |
| 8.7 | Supprimer SQLAlchemy (quand stable) | ⬜ | | |
| 8.8 | Supprimer Alembic (quand stable) | ⬜ | | |
| 8.9 | Supprimer endpoints API CRUD obsolètes | ⬜ | | |
| 8.10 | Nettoyer dépendances requirements.txt | ⬜ | | |
| 8.11 | Mettre à jour README.md | ⬜ | | |
| 8.12 | Mettre à jour docs/architecture/ | ⬜ | | |
| 8.13 | Commit "chore: cleanup after supabase migration" | ⬜ | | |

**Validation Phase 8** : ⬜  
**Critères** : Migration 100% complète, documentation à jour

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

---

## Résumé Global

| Phase | Progression | Statut |
|-------|-------------|--------|
| 1. Préparation | 100% | ✅ **COMPLÉTÉE** |
| 2. Configuration | 60% | 🔄 **EN COURS** |
| 3. Abstraction | 0% | ⬜ Non démarré |
| 4.1 Lecture simple | 0% | ⬜ Non démarré |
| 4.2 Recherche | 0% | ⬜ Non démarré |
| 4.3 CRUD | 0% | ⬜ Non démarré |
| 4.4 Métier | 0% | ⬜ Non démarré |
| 5. Frontend | 0% | ⬜ Non démarré |
| 6. Workers | 0% | ⬜ Non démarré |
| 7. Tests | 0% | ⬜ Non démarré |
| 8. Basculement | 0% | ⬜ Non démarré |

**Progression totale** : 15%  
**Prochaine étape** : Finaliser Phase 2 - Tests démarrage services + créer clients Supabase

---

**Dernière mise à jour** : 2025-01-20  
**Prochaine revue** : Après validation Phase 2
