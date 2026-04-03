# Tickets Phase 3 — Nettoyage Dépendances & Environment

## [TICKET-P3-001] Supprimer dépendances Celery de requirements.txt
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Supprimer les dépendances Celery de tous les fichiers `requirements.txt` :
- `backend_worker/requirements.txt` : supprimer `celery>=5.5.3`, `flower>=2.0.0`, `eventlet>=0.33.0`
- `backend/api/requirements.txt` : supprimer `celery==5.5.3`
- Vérifier `requirements-common.txt` et `requirements.txt` racine
- Vérifier que les dépendances TaskIQ sont présentes (`taskiq[redis]`, `taskiq-fastapi`, `httpx`, `aiofiles`)
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P3-002] Nettoyer variables d'environnement Celery
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Supprimer les variables d'environnement Celery :
- `.env` : supprimer `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_ADMIN_API_KEY`, `FLOWER_BASIC_AUTH`, `FLOWER_PASSWORD`
- `.env.example` : supprimer les mêmes variables
- Vérifier que `TASKIQ_BROKER_URL` et `TASKIQ_RESULT_BACKEND` sont présentes
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P3-003] Nettoyer docker-compose.yml
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Supprimer les références Celery dans `docker-compose.yml` :
- Supprimer les variables d'environnement `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` du service API
- Supprimer le volume `celery-beat-data`
- Supprimer le volume `flower-data`
- Vérifier que le service `taskiq-worker` est correctement configuré
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P3-004] Supprimer feature flags Celery fallback
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Supprimer les feature flags de fallback Celery une fois la migration complète :
- Supprimer `ENABLE_CELERY_FALLBACK` de `.env` et `.env.example`
- Supprimer `USE_TASKIQ_FOR_*` si toutes les tâches sont migrées
- Vérifier qu'aucun code ne lit ces variables
**Dépendances**: CLEAN-1, CLEAN-4 (bugs corrigés)
**Durée estimée**: 0.1 jour
**Notes**: À faire en dernier, après validation que toutes les tâches fonctionnent via TaskIQ
