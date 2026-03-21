# Phase 1 — Briefing Développeur : Socle TaskIQ Minimal

## 📋 Résumé

**Phase** : 1 — Socle TaskIQ Minimal  
**Durée estimée** : 2-3 jours  
**Objectif** : Ajouter TaskIQ sans impacter Celery existant  
**Statut** : 🚀 PRÊT À DÉMARRER

---

## 🎯 Contexte

La Phase 0 (Audit) est terminée. Nous avons :
- 26 tâches Celery identifiées avec leurs signatures
- Les dépendances entre tâches documentées
- Une baseline des tests établie (31 unitaires + 6 intégration)
- La configuration Redis documentée

**Prochaine étape** : Créer le socle TaskIQ minimal pour permettre la coexistence avec Celery.

---

## 📦 Tâches à Réaliser

### T1.1 : Ajouter les dépendances TaskIQ
**Fichier** : `backend_worker/requirements.txt`

**Actions** :
1. Ajouter les dépendances TaskIQ :
   ```
   taskiq[redis]>=0.11.0
   taskiq-fastapi>=0.4.0
   ```
2. **NE PAS SUPPRIMER** les dépendances Celery existantes
3. Vérifier la compatibilité avec Python 3.x

**Validation** :
- [ ] `pip install -r backend_worker/requirements.txt` réussit
- [ ] Les imports TaskIQ fonctionnent

---

### T1.2 : Créer `backend_worker/taskiq_app.py`
**Fichier** : `backend_worker/taskiq_app.py`

**Contenu** :
```python
"""Configuration TaskIQ pour SoniqueBay.

Coexiste avec celery_app.py pendant la migration.
"""
from taskiq import TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from backend_worker.utils.logging import logger
import os

# Broker Redis (même instance que Celery, DB différente)
broker = ListQueueBroker(
    url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')  # DB 1 pour coexistence
)

# Backend pour les résultats
result_backend = RedisAsyncResultBackend(
    redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
)

@broker.on_event(TaskiqState.EVENT_PRE_SEND)
async def pre_send_handler(task_name: str, **kwargs):
    logger.info(f"[TASKIQ] Envoi tâche: {task_name}")

@broker.on_event(TaskiqState.EVENT_POST_EXECUTE)
async def post_execute_handler(task_name: str, result, **kwargs):
    logger.info(f"[TASKIQ] Tâche terminée: {task_name}")
```

**Points d'attention** :
- Utiliser Redis DB 1 (pas DB 0 utilisé par Celery)
- Logger avec le préfixe `[TASKIQ]` pour différencier
- Pas de modification de `celery_app.py`

**Validation** :
- [ ] Le module s'importe sans erreur
- [ ] Le broker s'initialise correctement
- [ ] Les handlers de logging fonctionnent

---

### T1.3 : Créer `backend_worker/taskiq_worker.py`
**Fichier** : `backend_worker/taskiq_worker.py`

**Contenu** :
```python
"""Worker TaskIQ pour SoniqueBay.

Démarre en parallèle du worker Celery.
"""
from backend_worker.taskiq_app import broker
import asyncio

# Import des tâches TaskIQ (à migrer progressivement)
# from backend_worker.taskiq_tasks import *

async def main():
    logger.info("[TASKIQ] Démarrage worker TaskIQ...")
    await broker.startup()
    logger.info("[TASKIQ] Worker TaskIQ démarré, en attente de tâches...")
    # Le worker écoute les tâches
    await broker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Points d'attention** :
- Worker async (pas sync comme Celery)
- Pas d'import de tâches pour l'instant (Phase 2)
- Logging clair pour différencier de Celery

**Validation** :
- [ ] Le worker démarre sans erreur
- [ ] Les logs sont visibles
- [ ] Pas d'impact sur Celery

---

### T1.4 : Ajouter le service TaskIQ dans `docker-compose.yml`
**Fichier** : `docker-compose.yml`

**Ajouter** :
```yaml
taskiq-worker:
    build:
        context: .
        dockerfile: backend_worker/Dockerfile
    container_name: soniquebay-taskiq-worker
    restart: unless-stopped
    command: ["python", "-m", "backend_worker.taskiq_worker"]
    volumes:
        - ./backend_worker:/app/backend_worker
        - music-share:/music:ro
        - ./logs:/app/logs
    environment:
        - TASKIQ_BROKER_URL=redis://redis:6379/1
        - TASKIQ_RESULT_BACKEND=redis://redis:6379/1
        - API_URL=http://library:8001
        - MUSIC_PATH=/music
    depends_on:
        redis:
            condition: service_healthy
        api-service:
            condition: service_healthy
    networks:
        default:
            aliases:
                - taskiq-worker
    deploy:
        resources:
            limits:
                cpus: '0.5'
                memory: 512M
```

**Points d'attention** :
- Même Dockerfile que Celery (pas de duplication)
- Variables d'environnement spécifiques TaskIQ
- Même volume musique que Celery
- Limites de ressources identiques

**Validation** :
- [ ] `docker-compose build taskiq-worker` réussit
- [ ] `docker-compose up taskiq-worker` démarre
- [ ] Les logs TaskIQ sont visibles
- [ ] Celery fonctionne toujours

---

### T1.5 : Ajouter les variables d'environnement
**Fichier** : `.env.example`

**Ajouter** :
```bash
# TaskIQ Configuration
TASKIQ_BROKER_URL=redis://redis:6379/1
TASKIQ_RESULT_BACKEND=redis://redis:6379/1
```

**Validation** :
- [ ] Les variables sont documentées
- [ ] Les valeurs par défaut sont cohérentes

---

### T1.6 : Créer les tests unitaires TaskIQ
**Fichier** : `tests/unit/worker/test_taskiq_app.py`

**Contenu** :
```python
"""Tests unitaires pour la configuration TaskIQ.

Vérifie que TaskIQ s'initialise correctement sans impacter Celery.
"""
import pytest
from backend_worker.taskiq_app import broker, result_backend

def test_taskiq_broker_initialization():
    """Test que le broker TaskIQ s'initialise."""
    assert broker is not None
    assert broker.url is not None

def test_taskiq_result_backend_initialization():
    """Test que le backend de résultats s'initialise."""
    assert result_backend is not None

def test_celery_still_works():
    """Test que Celery fonctionne toujours après ajout TaskIQ."""
    from backend_worker.celery_app import celery
    assert celery is not None
    assert celery.conf.broker_url is not None
```

**Validation** :
- [ ] `pytest tests/unit/worker/test_taskiq_app.py -v` passe
- [ ] Les tests Celery existants passent toujours

---

### T1.7 : Exécuter les tests de non-régression
**Actions** :
```bash
# Tests TaskIQ
python -m pytest tests/unit/worker/test_taskiq_app.py -v

# Tests Celery existants (vérifier qu'ils passent toujours)
python -m pytest tests/unit/worker -q --tb=no

# Comparer avec baseline Phase 0
```

**Validation** :
- [ ] Tests TaskIQ passent
- [ ] Tests Celery existants passent (0 régression)
- [ ] Résultats comparables à la baseline

---

## 🔍 Points d'Attention

### 1. Coexistence
- TaskIQ et Celery utilisent la **même instance Redis** mais des **DB différentes** (0 vs 1)
- Les deux workers tournent en **parallèle** dans Docker
- Aucune tâche métier n'est migrée en Phase 1

### 2. Logging
- Utiliser le préfixe `[TASKIQ]` pour tous les logs TaskIQ
- Garder le préfixe `[CELERY]` pour les logs Celery existants
- Permettre le filtrage facile dans les logs

### 3. Tests
- **Ne pas modifier** les tests Celery existants
- **Ajouter** les tests TaskIQ en parallèle
- Vérifier l'absence de régression à chaque étape

### 4. Docker
- **Ne pas modifier** le service `celery-worker` existant
- **Ajouter** le service `taskiq-worker` en parallèle
- Vérifier que les deux services démarrent correctement

---

## 📊 Livrables Attendus

| Livrable | Fichier | Statut |
|----------|---------|--------|
| Dépendances TaskIQ | `backend_worker/requirements.txt` | ⬜ |
| Configuration TaskIQ | `backend_worker/taskiq_app.py` | ⬜ |
| Worker TaskIQ | `backend_worker/taskiq_worker.py` | ⬜ |
| Service Docker | `docker-compose.yml` | ⬜ |
| Variables d'environnement | `.env.example` | ⬜ |
| Tests unitaires | `tests/unit/worker/test_taskiq_app.py` | ⬜ |

---

## ✅ Critères de Validation Phase 1

- [ ] `docker-compose up` démarre les 4 conteneurs (api, celery-worker, taskiq-worker, frontend)
- [ ] Logs TaskIQ visibles sans erreurs
- [ ] Tests unitaires TaskIQ passent
- [ ] Tests unitaires Celery existants passent (0 régression)
- [ ] Performance stable (pas de dégradation)
- [ ] Documentation à jour

---

## 🔄 Prochaines Étapes

### Phase 2 — Migration Pilote (2-4 jours)
- Migrer 1-2 tâches non critiques avec shadow mode
- Créer les feature flags par tâche
- Implémenter le wrapper sync/async

---

## 📞 Contacts

- **Lead Développeur** : Validation globale, revue de code
- **Testeur** : Validation des tests, détection des régressions

---

*Dernière mise à jour : 2026-03-20*
*Phase : 1 (Socle TaskIQ Minimal) — PRÊTE À DÉMARRER*
