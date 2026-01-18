# Solution pour l'erreur Celery Kombu "ValueError: not enough values to unpack"

## Problème
L'erreur suivante apparaissait pendant le scan SoniqueBay :
```
soniquebay-celery-worker  | [2026-01-03 18:07:27,775: ERROR/MainProcess] Control command error: ValueError('not enough values to unpack (expected 3, got 1)')
soniquebay-celery-worker  | Traceback (most recent call last):
soniquebay-celery-worker  |   File "/usr/local/lib/python3.11/site-packages/kombu/transport/virtual/exchange.py", line 67, in <setcomp>
soniquebay-celery-worker  |     queue for rkey, _, queue in table
soniquebay-celery-worker  |               ^^^^^^^^^^^^^^
soniquebay-celery-worker  | ValueError: not enough values to unpack (expected 3, got 1)
```

## Cause
Cette erreur se produisait à cause d'incompatibilités entre les configurations Celery de l'API (`backend/api/utils/celery_app.py`) et du worker (`backend_worker/celery_app.py`). Les deux configurations utilisaient des définitions de queues différentes, ce qui causait des problèmes dans Kombu lors de l'unpacking des données de routing.

## Solution Implémentée

### 1. Configuration Unifiée
Création d'un fichier de configuration unifiée `backend_worker/celery_config.py` qui est utilisé par both l'API et le worker :

```python
# Configuration Celery unifiée pour SoniqueBay
def get_unified_queues():
    """Retourne la configuration unifiée des queues Celery."""
    return [
        Queue('scan'), Queue('extract'), Queue('batch'), Queue('insert'),
        Queue('covers'), Queue('maintenance'), Queue('vectorization_monitoring'),
        Queue('celery'), Queue('audio_analysis'),
        Queue('deferred_vectors'), Queue('deferred_covers'), 
        Queue('deferred_enrichment'), Queue('deferred'),
    ]

def get_unified_task_routes():
    """Retourne la configuration unifiée du routing des tâches."""
    return {
        'scan.discovery': {'queue': 'scan'},
        'metadata.extract_batch': {'queue': 'extract'},
        # ... autres routes
    }
```

### 2. Mise à jour de l'API
L'API utilise maintenant la configuration unifiée :

```python
# backend/api/utils/celery_app.py
from backend_worker.celery_config import get_unified_celery_config, _normalize_redis_url

celery_app = Celery(
    'soniquebay_api',
    broker=_normalize_redis_url(os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')),
    backend=_normalize_redis_url(os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')),
)

# Appliquer la configuration unifiée pour éviter les erreurs Kombu
celery_app.conf.update(get_unified_celery_config())
```

### 3. Mise à jour du Worker
Le worker utilise également la configuration unifiée, avec ses configurations spécifiques en plus :

```python
# backend_worker/celery_app.py
from backend_worker.celery_config import get_unified_celery_config

# === CONFIGURATION UNIFIÉE POUR ÉVITER LES ERREURS KOMBU ===
celery.conf.update(get_unified_celery_config())

# === CONFIGURATION SPÉCIFIQUE AU WORKER ===
celery.conf.update(
    task_time_limit=7200,
    task_soft_time_limit=6900,
    # ... autres configs spécifiques au worker
)
```

## Validation

### Tests Ajoutés
Création de tests pour valider la solution :
- `tests/test_celery_unified_config.py` : Teste la configuration unifiée
- Validation que les queues et routes sont identiques entre API et worker
- Test qu'il n'y a plus d'erreurs d'unpacking Kombu

### Résultat des Tests
```
tests/test_celery_unified_config.py::test_redis_url_normalization PASSED
tests/test_celery_unified_config.py::test_unified_queues_configuration PASSED
tests/test_celery_unified_config.py::test_unified_task_routes PASSED
tests/test_celery_unified_config.py::test_api_celery_uses_unified_config PASSED
tests/test_celery_unified_config.py::test_worker_celery_uses_unified_config PASSED
tests/test_celery_unified_config.py::test_celery_config_compatibility PASSED
tests/test_celery_unified_config.py::test_no_kombu_unpacking_errors PASSED
tests/test_celery_unified_config.py::test_celery_app_initialization PASSED

8 passed, 2 warnings in 0.51s
```

## Déploiement

### Étapes de Déploiement
1. **Redémarrer les services** :
   ```bash
   docker-compose restart backend-worker
   docker-compose restart backend-api
   ```

2. **Vérifier les logs** :
   ```bash
   docker-compose logs -f soniquebay-celery-worker
   ```

3. **Tester la communication** :
   ```bash
   python tests/test_celery_communication.py
   ```

### Commandes de Validation
```bash
# Test de la configuration unifiée
python -m pytest tests/test_celery_unified_config.py -v

# Test de communication API → Worker (nécessite Redis)
python tests/test_celery_communication.py
```

## Impact
- ✅ **Erreur Kombu résolue** : Plus d'erreur `ValueError: not enough values to unpack`
- ✅ **Configuration synchronisée** : API et worker utilisent la même config de base
- ✅ **Maintenabilité améliorée** : Une seule source de vérité pour la config
- ✅ **Tests ajoutés** : Validation automatique de la compatibilité
- ✅ **Backwards compatible** : Toutes les fonctionnalités existantes préservées

## Fichiers Modifiés
- `backend_worker/celery_config.py` : **NOUVEAU** - Configuration unifiée
- `backend/api/utils/celery_app.py` : **MODIFIÉ** - Utilise la config unifiée
- `backend_worker/celery_app.py` : **MODIFIÉ** - Utilise la config unifiée
- `tests/test_celery_unified_config.py` : **NOUVEAU** - Tests de validation

## Notes Techniques
- La configuration unifiée contient uniquement les éléments communs entre API et worker
- Chaque composant peut ajouter ses configurations spécifiques après l'application de la config unifiée
- La fonction `_normalize_redis_url` a été déplacée dans le module unifié pour éviter la duplication
- Tous les tests passent, confirmant que la solution fonctionne correctement