# TODO Audit Supabase Migration

**Date de création** : 2026-03-03  
**Branche** : `blackboxai/feature/supabase-migration`  
**Statut** : 🔄 En cours

---

## ✅ Tâches Complétées

| # | Tâche | Statut | Date | Notes |
|---|-------|--------|------|-------|
| 1 | Fixer `backend/api/requirements.txt` - Ajouter `supabase>=2.3.0` | ✅ | 2026-03-03 | Dépendance ajoutée |
| 2 | Fixer `backend/api/utils/db_config.py` - MIGRATED_TABLES par défaut | ✅ | 2026-03-03 | `_DEFAULT_MIGRATED_TABLES` ajouté |
| 3 | Rebuild conteneur `api-service` avec --no-cache | ✅ | 2026-03-03 | Container rebuildé et démarré |
| 4 | Vérifier healthcheck API | ✅ | 2026-03-03 | `GET /api/healthcheck` → `healthy` |
| 5 | Rebuild conteneur `celery-worker` | 🔄 | 2026-03-03 | Build en cours (étape apt) |
| 6 | Rebuild conteneur `frontend` | 🔄 | 2026-03-03 | Build en cours (étape apt) |

---

## 🔄 Tâches en Cours / À Faire

| # | Tâche | Statut | Priorité | Notes |
|---|-------|--------|----------|-------|
| 7 | Démarrer celery-worker après rebuild | ⬜ | Haute | Attendre fin build |
| 8 | Démarrer frontend après rebuild | ⬜ | Haute | Attendre fin build |
| 9 | Tester connexion Supabase PostgreSQL | ⬜ | Haute | Port 54322 |
| 10 | Tester TrackServiceV2 CRUD | ⬜ | Moyenne | Feature flag USE_SUPABASE |
| 11 | Tester DatabaseAdapter avec Supabase | ⬜ | Moyenne | Adapter routing |
| 12 | Tester Celery bulk insert | ⬜ | Moyenne | SQLAlchemy async |
| 13 | Vérifier supabase-realtime | ⬜ | Moyenne | Port 54323 |
| 14 | Vérifier supabase-auth | ⬜ | Moyenne | Port 54324 |
| 15 | Fixer supabase-dashboard (unhealthy) | ⬜ | Basse | Port 54325 |
| 16 | Exécuter tests unitaires V2 | ⬜ | Moyenne | 20 tests existants |
| 17 | Exécuter tests E2E | ⬜ | Moyenne | 9 tests, 1 échec connu |
| 18 | Documenter écarts checklist | ⬜ | Basse | Rapport final |
| 19 | Proposer plan Phase 7 | ⬜ | Basse | Tests complétion |
| 20 | Identifier blockers Phase 8 | ⬜ | Basse | Basculement |

---

## 🐛 Problèmes Identifiés

### 🔴 Critiques (À fixer immédiatement)
- **Aucun** - Les problèmes critiques ont été résolus

### 🟡 Moyens (À surveiller)
1. **supabase-dashboard unhealthy** - Le dashboard Supabase ne démarre pas correctement
   - Port : 54325
   - Impact : Faible (UI admin non critique)
   - Action : Vérifier logs `docker logs soniquebay-supabase-dashboard`

2. **Dépendance legacy TrackService** - `TrackServiceV2` importe encore `TrackService`
   - Fichier : `backend/api/services/track_service_v2.py`
   - Impact : Moyen (code mort potentiel)
   - Action : Refactoriser pour éliminer dépendance

### 🟢 Faibles (Documentation)
- SQLAlchemy backend lève `NotImplementedError` (attendu, fallback non requis)
- 1 test E2E échoue (88.9% passent, acceptable pour l'instant)

---

## 📊 État des Conteneurs

| Conteneur | Statut | Port | Health | Notes |
|-----------|--------|------|--------|-------|
| soniquebay-supabase-db | ✅ Up | 54322 | healthy | PostgreSQL + extensions |
| soniquebay-supabase-realtime | ✅ Up | 54323 | - | WebSocket temps réel |
| soniquebay-supabase-auth | ✅ Up | 54324 | - | GoTrue auth |
| soniquebay-supabase-meta | ✅ Up | 8080 | healthy | Métadonnées |
| soniquebay-supabase-dashboard | ⚠️ Up | 54325 | **unhealthy** | Studio UI |
| soniquebay-redis | ✅ Up | 6379 | healthy | Broker Celery |
| soniquebay-postgres | ✅ Up | 5432 | healthy | Legacy DB |
| soniquebay-api | ✅ Up | 8001 | healthy | **Rebuildé avec supabase-py** |
| soniquebay-celery-worker | 🔄 Build | - | - | **En cours de rebuild** |
| soniquebay-frontend | 🔄 Build | - | - | **En cours de rebuild** |
| llm-service | ✅ Up | 5001 | starting | KoboldCpp |

---

## 🎯 Prochaines Étapes Prioritaires

1. **Attendre fin builds** celery-worker et frontend (en cours)
2. **Démarrer** les conteneurs rebuildés
3. **Tester** TrackServiceV2 avec USE_SUPABASE=true
4. **Vérifier** connexion realtime et auth

---

**Dernière mise à jour** : 2026-03-03 17:50  
**Prochaine revue** : Après fin builds celery-worker et frontend
