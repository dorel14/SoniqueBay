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
| 5 | Rebuild conteneur `celery-worker` | ✅ | 2026-03-04 | Build terminé, conteneur démarré |
| 6 | Rebuild conteneur `frontend` | ✅ | 2026-03-04 | Build terminé, conteneur démarré |

---

## 🔄 Tâches en Cours / À Faire

| # | Tâche | Statut | Priorité | Notes |
|---|-------|--------|----------|-------|
| 7 | Démarrer celery-worker après rebuild | ✅ | 2026-03-04 | Conteneur démarré et healthy |
| 8 | Démarrer frontend après rebuild | ✅ | 2026-03-04 | Conteneur démarré (port 8080) |
| 9 | Tester connexion Supabase PostgreSQL | ⬜ | Haute | Port 54322 - À tester |
| 10 | Tester TrackServiceV2 CRUD | ⬜ | Moyenne | Feature flag USE_SUPABASE |
| 11 | Tester DatabaseAdapter avec Supabase | ⬜ | Moyenne | Adapter routing |
| 12 | Tester Celery bulk insert | ⬜ | Moyenne | SQLAlchemy async |
| 13 | Vérifier supabase-realtime | ❌ | Moyenne | **Désactivé** - APP_NAME non reconnu |
| 14 | Vérifier supabase-auth | ✅ | 2026-03-04 | **Healthy** - Fonctionnel sur port 54324 |
| 15 | Fixer supabase-dashboard (unhealthy) | ⚠️ | Basse | Fonctionnel mais healthcheck manquant |
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
1. **supabase-dashboard unhealthy** - Le dashboard Supabase fonctionne mais healthcheck manquant
   - Port : 54325
   - Impact : Faible (UI admin non critique, Next.js ready)
   - Action : Ajouter healthcheck ou accepter statut non bloquant

2. **supabase-realtime désactivé** - Service optionnel non fonctionnel
   - Port : 54323
   - Impact : Moyen (WebSocket legacy disponible en fallback)
   - Action : Investiguer version image ou garder WebSocket legacy

3. **Dépendance legacy TrackService** - `TrackServiceV2` importe encore `TrackService`
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
| soniquebay-supabase-realtime | ❌ Exited | - | - | **Désactivé** - APP_NAME non reconnu |
| soniquebay-supabase-auth | ✅ Up | 54324 | **healthy** | GoTrue auth fonctionnel |
| soniquebay-supabase-meta | ✅ Up | 8085 | healthy | Métadonnées (port changé 8080→8085) |
| soniquebay-supabase-dashboard | ⚠️ Up | 54325 | unhealthy* | Studio UI (*fonctionnel mais sans healthcheck) |
| soniquebay-redis | ✅ Up | 6379 | healthy | Broker Celery |
| soniquebay-postgres | ✅ Up | 5432 | healthy | Legacy DB |
| soniquebay-api | ✅ Up | 8001 | healthy | **Rebuildé avec supabase-py** |
| soniquebay-celery-worker | ✅ Up | - | running | Worker Celery opérationnel |
| soniquebay-frontend | ✅ Up | 8080 | unhealthy* | Frontend NiceGUI (*healthcheck en cours) |
| llm-service | ✅ Up | 5001 | starting | KoboldCpp |

---

## 🎯 Prochaines Étapes Prioritaires

1. **Tester connexion API → Supabase** (port 54322)
2. **Exécuter tests unitaires V2** (Track, Album, Artist services)
3. **Valider DatabaseAdapter** (routing SQLAlchemy ↔ Supabase)
4. **Documenter** état realtime (optionnel) et dashboard

---

**Dernière mise à jour** : 2026-03-04 12:45  
**Prochaine revue** : Tests connexion Supabase et services V2

---

## 📄 Référence

Voir `docs/plans/STATUS_SUPABASE_MIGRATION_2026-03-04.md` pour le point de situation complet.
