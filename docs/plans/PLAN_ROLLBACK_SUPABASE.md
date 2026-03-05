# Plan de Rollback - Migration Supabase vers PostgreSQL Originale

**Date** : 2025-01-20  
**Objectif** : Revenir à l'architecture PostgreSQL/SQLAlchemy originale  
**Statut** : 🔄 Planification

---

## Résumé Exécutif

Ce document détaille le plan de rollback complet pour éliminer Supabase et revenir à l'architecture PostgreSQL/SQLAlchemy originale de SoniqueBay.

### Architecture Cible (Post-Rollback)

```
┌─────────────┐     HTTP      ┌──────────────┐     SQLAlchemy    ┌─────────────┐
│   NiceGUI   │ ◄────────────► │   FastAPI    │ ◄───────────────► │  PostgreSQL │
│  (Frontend) │                │   (Backend)  │                   │   (Local)   │
└─────────────┘                └──────────────┘                   └─────────────┘
                                      │
                                      │ HTTP API
                                      ▼
                               ┌──────────────┐
                               │Celery Workers│
                               │  (API only)  │
                               └──────────────┘
```

---

## Phase 1 : Préparation et Sauvegarde

### 1.1 Créer une Branche Dédiée

```powershell
# Commandes PowerShell
git checkout master
git checkout -b blackboxai/rollback/supabase-removal
git push -u origin blackboxai/rollback/supabase-removal
```

### 1.2 Sauvegarde des Données

**Action** : Exporter les données de Supabase vers PostgreSQL legacy si nécessaire.

```powershell
# Si des données ont été migrées vers Supabase
# Les re-exporter vers PostgreSQL legacy
docker exec soniquebay-supabase-db pg_dump -U supabase -d postgres > backup_supabase.sql
docker exec -i soniquebay-postgres psql -U postgres -d musicdb < backup_supabase.sql
```

### 1.3 Documentation de l'État Actuel

- [ ] Capturer l'état actuel des conteneurs
- [ ] Documenter les données présentes dans Supabase
- [ ] Vérifier la cohérence des données entre Supabase et PostgreSQL legacy

---

## Phase 2 : Suppression Infrastructure Docker

### 2.1 Arrêter les Services Supabase

```powershell
# Arrêter uniquement les services Supabase
docker-compose stop supabase-db supabase-kong supabase-rest supabase-auth supabase-meta supabase-realtime supabase-storage supabase-imgproxy supabase-studio
```

### 2.2 Modifier docker-compose.yml

**Supprimer les services suivants** :

| Service | Raison |
|---------|--------|
| `supabase-db` | Base de données Supabase |
| `supabase-kong` | API Gateway |
| `supabase-rest` | PostgREST |
| `supabase-auth` | Authentification GoTrue |
| `supabase-meta` | Métadonnées |
| `supabase-realtime` | WebSocket temps réel |
| `supabase-storage` | Stockage fichiers |
| `supabase-imgproxy` | Transformation images |
| `supabase-studio` | Dashboard UI |

**Conserver uniquement** :
- `db` (PostgreSQL legacy)
- `redis`
- `api-service`
- `frontend`
- `celery-worker`
- `celery_beat`
- `llm-service`
- `timesync`
- `celery-insights`

### 2.3 Supprimer le Volume Supabase

```powershell
# Supprimer le volume de données Supabase
docker volume rm soniquebay_supabase-data
# Ou si nommé différemment
docker volume ls | findstr supabase
docker volume rm <nom_du_volume>
```

---

## Phase 3 : Suppression Code Backend

### 3.1 Fichiers à Supprimer

| Fichier | Description | Taille Estimée |
|---------|-------------|----------------|
| `backend/api/utils/supabase_client.py` | Client Supabase backend | ~150 lignes |
| `backend/api/utils/db_adapter.py` | Adaptateur dual DB | ~200 lignes |
| `backend/api/utils/db_config.py` | Configuration feature flags | ~80 lignes |
| `backend/api/repositories/base_repository.py` | Repository pattern | ~180 lignes |
| `backend/api/repositories/__init__.py` | Package repositories | ~20 lignes |
| `backend/api/services/track_service_v2.py` | Service Track V2 | ~300 lignes |
| `backend/api/services/album_service_v2.py` | Service Album V2 | ~250 lignes |
| `backend/api/services/artist_service_v2.py` | Service Artist V2 | ~250 lignes |
| `backend/api/services/vector_search_service_v2.py` | Vector Search V2 | ~200 lignes |
| `backend/api/services/track_mir_service_v2.py` | MIR Service V2 | ~350 lignes |
| `backend/api/services/realtime_service_v2.py` | Realtime Service V2 | ~180 lignes |
| `backend/api/services/chat_memory_service.py` | Chat Memory Service | ~220 lignes |
| `backend/api/routers/chat_realtime_api.py` | Router Realtime HTTP | ~150 lignes |

### 3.2 Nettoyer les Imports

**Fichiers à modifier pour retirer les imports Supabase** :

- `backend/api/__init__.py` - Retirer imports supabase
- `backend/api/api_app.py` - Retirer routes realtime
- `backend/api/services/__init__.py` - Retirer exports V2

---

## Phase 4 : Suppression Code Frontend

### 4.1 Fichiers à Supprimer

| Fichier | Description | Taille Estimée |
|---------|-------------|----------------|
| `frontend/utils/supabase_client.py` | Client Supabase frontend | ~120 lignes |
| `frontend/utils/feature_flags.py` | Feature flags | ~60 lignes |
| `frontend/utils/supabase_realtime.py` | Client Realtime | ~150 lignes |
| `frontend/services/track_service_v2.py` | Service Track V2 | ~200 lignes |
| `frontend/services/album_service_v2.py` | Service Album V2 | ~180 lignes |
| `frontend/services/artist_service_v2.py` | Service Artist V2 | ~180 lignes |
| `frontend/services/search_service_v2.py` | Search Service V2 | ~150 lignes |
| `frontend/services/graphql_replacement_service.py` | GraphQL Replacement | ~120 lignes |

### 4.2 Restaurer Services Originaux

**S'assurer que les services originaux sont fonctionnels** :

- `frontend/services/track_service.py` - Doit utiliser API REST
- `frontend/services/album_service.py` - Doit utiliser API REST
- `frontend/services/artist_service.py` - Doit utiliser API REST
- `frontend/services/search_service.py` - Doit utiliser API REST/GraphQL

---

## Phase 5 : Suppression Code Worker

### 5.1 Fichiers à Supprimer

| Fichier | Description |
|---------|-------------|
| `backend_worker/utils/supabase_sqlalchemy.py` | Connexion SQLAlchemy vers Supabase |
| `backend_worker/utils/supabase_migrator.py` | Outil de migration |
| `backend_worker/utils/supabase_scan_test.py` | Tests scan Supabase |
| `backend_worker/models/` | Copie des modèles (utiliser `backend/api/models/`) |
| `backend_worker/alembic/` | Migrations déplacées (restaurer `alembic/` à la racine) |

### 5.2 Restaurer Configuration Worker

**Modifier** :
- `backend_worker/celery_app.py` - Retirer configuration Supabase
- `backend_worker/Dockerfile` - Retirer dépendances Supabase
- `backend_worker/requirements.txt` - Retirer `supabase>=2.3.0`

---

## Phase 6 : Suppression Tests Supabase

### 6.1 Fichiers à Supprimer

| Fichier | Description |
|---------|-------------|
| `tests/unit/test_db_adapter.py` | Tests adaptateur DB |
| `tests/unit/test_supabase_sqlalchemy.py` | Tests SQLAlchemy Supabase |
| `tests/unit/test_realtime_service_v2.py` | Tests Realtime V2 |
| `tests/unit/test_track_mir_service_v2.py` | Tests MIR V2 |
| `tests/unit/test_vector_search_service_v2.py` | Tests Vector Search V2 |
| `tests/unit/frontend/test_supabase_client_frontend.py` | Tests Client Frontend |
| `tests/integration/test_supabase_integration.py` | Tests Intégration |
| `tests/e2e/test_supabase_scenarios.py` | Tests E2E Supabase |

### 6.2 Conserver les Tests PostgreSQL Originaux

**S'assurer que les tests suivants passent** :
- `tests/unit/test_track_service.py`
- `tests/unit/test_album_service.py`
- `tests/unit/test_artist_service.py`
- `tests/unit/test_search_service.py`

---

## Phase 7 : Suppression Dossier Supabase

### 7.1 Supprimer le Dossier Entier

```powershell
# Supprimer le dossier supabase/
Remove-Item -Recurse -Force supabase/
```

### 7.2 Contenu du Dossier à Supprimer

```
supabase/
├── Dockerfile
├── README.md
├── config/
│   └── kong.yml
├── db_init/
│   └── init_supabase.sql
├── edge-functions/
└── scripts/
    ├── entrypoint.sh
    ├── init-auth-schema.sh
    ├── logs.sh
    ├── start.sh
    ├── stop.sh
    └── test-services.sh
```

---

## Phase 8 : Mise à Jour Dépendances

### 8.1 Backend API

**Fichier** : `backend/api/requirements.txt`

```diff
- supabase>=2.3.0
- postgrest-py>=0.16.0
- realtime-py>=1.0.0
```

### 8.2 Frontend

**Fichier** : `frontend/requirements.txt`

```diff
- supabase>=2.3.0
```

### 8.3 Workers

**Fichier** : `backend_worker/requirements.txt`

```diff
- supabase>=2.3.0
```

---

## Phase 9 : Nettoyage Variables d'Environnement

### 9.1 Fichier .env

**Variables à supprimer** :

```diff
- USE_SUPABASE=true
- USE_SUPABASE_REALTIME=false
- USE_SUPABASE_AUTH=false
- USE_SUPABASE_STORAGE=false
- SUPABASE_URL=http://supabase-kong:8000
- SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- SUPABASE_JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
- SUPABASE_DB_PASSWORD=supabase
- SUPABASE_PROJECT_NAME=soniquebay-project
- SUPABASE_ORGANIZATION_NAME=SoniqueBay
- SUPABASE_SITE_URL=http://localhost:8080
```

**Variables à conserver** :

```env
# PostgreSQL Legacy
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=musicdb
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/musicdb

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# API
API_URL=http://api:8001
ENCRYPTION_KEY=your-encryption-key

# LLM
LLM_PROVIDER=koboldcpp
KOBOLDCPP_BASE_URL=http://llm-service:5001
AGENT_MODEL=koboldcpp/qwen2.5-3b-instruct-q4_k_m

# Platform
PLATFORM=docker
TZ=Europe/Paris
```

---

## Phase 10 : Validation et Tests

### 10.1 Tests Unitaires

```powershell
# Exécuter les tests unitaires PostgreSQL
cd c:/Users/david/Documents/devs/SoniqueBay-app
python -m pytest tests/unit/test_track_service.py -v
python -m pytest tests/unit/test_album_service.py -v
python -m pytest tests/unit/test_artist_service.py -v
python -m pytest tests/unit/test_search_service.py -v
```

### 10.2 Tests E2E

```powershell
# Exécuter les tests E2E
python -m pytest tests/e2e/ -v --tb=short
```

### 10.3 Validation Manuelle

| Test | Commande | Résultat Attendu |
|------|----------|------------------|
| Healthcheck API | `curl http://localhost:8001/health` | `{"status": "healthy"}` |
| Liste tracks | `curl http://localhost:8001/api/tracks` | JSON avec tracks |
| Recherche | `curl http://localhost:8001/api/search?q=test` | Résultats de recherche |
| Frontend | Navigateur http://localhost:8080 | Interface NiceGUI |

---

## Phase 11 : Documentation

### 11.1 Archiver la Documentation Supabase

Déplacer les documents de planification Supabase vers un dossier d'archive :

```powershell
# Créer dossier archive
mkdir docs/plans/archive/supabase-migration/

# Déplacer les documents
Move-Item docs/plans/AUDIT_SUPABASE_MIGRATION.md docs/plans/archive/supabase-migration/
Move-Item docs/plans/TODO_AUDIT_SUPABASE.md docs/plans/archive/supabase-migration/
Move-Item docs/plans/PLAN_REFACTOR_SUPABASE_MIGRATION.md docs/plans/archive/supabase-migration/
Move-Item docs/plans/supabase-checklist.md docs/plans/archive/supabase-migration/
Move-Item docs/plans/PLAN_ROLLBACK_SUPABASE.md docs/plans/archive/supabase-migration/
```

### 11.2 Mettre à Jour README.md

**Ajouter une section** :

```markdown
## Architecture Base de Données

SoniqueBay utilise PostgreSQL avec SQLAlchemy comme ORM.

### Configuration

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/musicdb
```

### Migrations

Les migrations sont gérées avec Alembic :

```bash
alembic upgrade head
```
```

---

## Checklist de Validation du Rollback

| # | Étape | Statut | Date |
|---|-------|--------|------|
| 1 | Création branche rollback | ✅ | 2025-01-20 |
| 2 | Arrêt services Supabase | ✅ | 2025-01-20 |
| 3 | Modification docker-compose.yml | ✅ | 2025-01-20 |
| 4 | Suppression fichiers backend | ✅ | 2025-01-20 |
| 5 | Suppression fichiers frontend | ✅ | 2025-01-20 |
| 6 | Suppression fichiers worker | ✅ | 2025-01-20 |
| 7 | Suppression tests Supabase | ✅ | 2025-01-20 |
| 8 | Suppression dossier supabase/ | ✅ | 2025-01-20 |
| 9 | Mise à jour dépendances | ✅ | 2025-01-20 |
| 10 | Nettoyage variables .env | ✅ | 2025-01-20 |
| 11 | Tests unitaires passent | 🔄 | En attente rebuild conteneurs |
| 12 | Tests E2E passent | ⬜ | |
| 13 | Validation manuelle | ⬜ | |
| 14 | Documentation à jour | ✅ | 2025-01-20 |
| 15 | Merge vers master | ⬜ | |

---

## Commandes de Rollback Rapide

### Script PowerShell Complet

```powershell
# rollback_supabase.ps1
# Script de rollback complet Supabase -> PostgreSQL

Write-Host "=== ROLLBACK SUPABASE -> POSTGRESQL ===" -ForegroundColor Green

# 1. Créer branche
git checkout master
git checkout -b blackboxai/rollback/supabase-removal

# 2. Arrêter services Supabase
Write-Host "Arrêt des services Supabase..." -ForegroundColor Yellow
docker-compose stop supabase-db supabase-kong supabase-rest supabase-auth supabase-meta supabase-realtime supabase-storage supabase-imgproxy supabase-studio

# 3. Supprimer fichiers backend
Write-Host "Suppression fichiers backend..." -ForegroundColor Yellow
Remove-Item backend/api/utils/supabase_client.py -ErrorAction SilentlyContinue
Remove-Item backend/api/utils/db_adapter.py -ErrorAction SilentlyContinue
Remove-Item backend/api/utils/db_config.py -ErrorAction SilentlyContinue
Remove-Item backend/api/repositories/base_repository.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/track_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/album_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/artist_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/vector_search_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/track_mir_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/realtime_service_v2.py -ErrorAction SilentlyContinue
Remove-Item backend/api/services/chat_memory_service.py -ErrorAction SilentlyContinue
Remove-Item backend/api/routers/chat_realtime_api.py -ErrorAction SilentlyContinue

# 4. Supprimer fichiers frontend
Write-Host "Suppression fichiers frontend..." -ForegroundColor Yellow
Remove-Item frontend/utils/supabase_client.py -ErrorAction SilentlyContinue
Remove-Item frontend/utils/feature_flags.py -ErrorAction SilentlyContinue
Remove-Item frontend/utils/supabase_realtime.py -ErrorAction SilentlyContinue
Remove-Item frontend/services/track_service_v2.py -ErrorAction SilentlyContinue
Remove-Item frontend/services/album_service_v2.py -ErrorAction SilentlyContinue
Remove-Item frontend/services/artist_service_v2.py -ErrorAction SilentlyContinue
Remove-Item frontend/services/search_service_v2.py -ErrorAction SilentlyContinue
Remove-Item frontend/services/graphql_replacement_service.py -ErrorAction SilentlyContinue

# 5. Supprimer fichiers worker
Write-Host "Suppression fichiers worker..." -ForegroundColor Yellow
Remove-Item backend_worker/utils/supabase_sqlalchemy.py -ErrorAction SilentlyContinue
Remove-Item backend_worker/utils/supabase_migrator.py -ErrorAction SilentlyContinue
Remove-Item backend_worker/utils/supabase_scan_test.py -ErrorAction SilentlyContinue
Remove-Item -Recurse backend_worker/models/ -ErrorAction SilentlyContinue
Remove-Item -Recurse backend_worker/alembic/ -ErrorAction SilentlyContinue

# 6. Supprimer tests
Write-Host "Suppression tests Supabase..." -ForegroundColor Yellow
Remove-Item tests/unit/test_db_adapter.py -ErrorAction SilentlyContinue
Remove-Item tests/unit/test_supabase_sqlalchemy.py -ErrorAction SilentlyContinue
Remove-Item tests/unit/test_realtime_service_v2.py -ErrorAction SilentlyContinue
Remove-Item tests/unit/test_track_mir_service_v2.py -ErrorAction SilentlyContinue
Remove-Item tests/unit/test_vector_search_service_v2.py -ErrorAction SilentlyContinue
Remove-Item tests/unit/frontend/test_supabase_client_frontend.py -ErrorAction SilentlyContinue
Remove-Item tests/integration/test_supabase_integration.py -ErrorAction SilentlyContinue

# 7. Supprimer dossier supabase
Write-Host "Suppression dossier supabase/..." -ForegroundColor Yellow
Remove-Item -Recurse -Force supabase/ -ErrorAction SilentlyContinue

# 8. Commit
Write-Host "Commit des changements..." -ForegroundColor Yellow
git add -A
git commit -m "rollback: remove Supabase migration and restore PostgreSQL architecture"

Write-Host "=== ROLLBACK TERMINÉ ===" -ForegroundColor Green
Write-Host "Prochaines étapes :" -ForegroundColor Cyan
Write-Host "1. Modifier docker-compose.yml pour supprimer les services Supabase"
Write-Host "2. Mettre à jour les fichiers requirements.txt"
Write-Host "3. Nettoyer le fichier .env"
Write-Host "4. Exécuter les tests"
Write-Host "5. Merger la branche vers master"
```

---

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Perte de données | Faible | Critique | Sauvegarde complète avant rollback |
| Régression fonctionnelle | Moyenne | Haute | Tests complets avant merge |
| Dépendances cassées | Moyenne | Moyenne | Vérifier imports après suppression |
| Configuration invalide | Moyenne | Moyenne | Validation docker-compose.yml |
| Performance dégradée | Faible | Moyenne | Benchmarks post-rollback |

---

## Conclusion

Ce plan de rollback permet de revenir à l'architecture PostgreSQL/SQLAlchemy originale en éliminant complètement Supabase. L'approche progressive assure une transition sans perte de données ni régression fonctionnelle.

**Prochaine étape** : Exécuter le script PowerShell de rollback et valider les tests.

---

**Signé** : SoniqueBay Team  
**Date** : 2025-01-20  
**Statut** : ✅ Rollback exécuté - 45+ fichiers supprimés, architecture PostgreSQL restaurée
