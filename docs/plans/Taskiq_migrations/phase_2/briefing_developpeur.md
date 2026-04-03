# Briefing Développeur — Phase 2 : Migration Pilote

## 🎯 Objectif
Migrer 1-2 tâches non critiques vers TaskIQ avec feature flag et shadow mode.

---

## 📋 Tâches à Réaliser

### T2.1 : Créer `backend_worker/taskiq_tasks/__init__.py`
**Fichier** : `backend_worker/taskiq_tasks/__init__.py` (nouveau)

**Contenu** :
```python
"""Tâches TaskIQ pour SoniqueBay.

Ce package contient les tâches migrées de Celery vers TaskIQ.
"""
```

**Validation** :
- [ ] Le fichier existe
- [ ] Le package est importable

---

### T2.2 : Créer `backend_worker/taskiq_tasks/maintenance.py`
**Fichier** : `backend_worker/taskiq_tasks/maintenance.py` (nouveau)

**Contenu** :
```python
"""Tâches TaskIQ de maintenance.

Migration de celery_tasks.py vers TaskIQ.
"""
from backend_worker.taskiq_app import broker
from backend_worker.utils.logging import logger
import os
import asyncio

# NOTE: Utiliser des imports ABSOLUS (backend_worker.xxx)
# Conformément aux règles AGENTS.md : "Préférer les imports absolus dans les modules internes"


@broker.task
async def cleanup_old_data_task(days_old: int = 30) -> dict:
    """Nettoie les anciennes données.
    
    Args:
        days_old: Nombre de jours pour considérer les données comme anciennes
        
    Returns:
        Résultat du nettoyage
    """
    logger.info(f"[TASKIQ] Nettoyage données > {days_old} jours")
    
    # Implémentation existante (à adapter depuis celery_tasks.py)
    # Note: Cette implémentation est un exemple
    # Il faut copier la logique métier depuis celery_tasks.py
    
    try:
        # Simuler le nettoyage
        await asyncio.sleep(0.1)  # Simuler un traitement
        
        result = {
            "cleaned": True,
            "days_old": days_old,
            "items_cleaned": 0,  # À implémenter
            "success": True
        }
        
        logger.info(f"[TASKIQ] Nettoyage terminé: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[TASKIQ] Erreur nettoyage: {e}")
        return {
            "cleaned": False,
            "days_old": days_old,
            "error": str(e),
            "success": False
        }
```

**Validation** :
- [ ] Le fichier existe
- [ ] La tâche est correctement définie
- [ ] Les logs utilisent le préfixe `[TASKIQ]`

---

### T2.3 : Ajouter le feature flag dans `backend_worker/celery_tasks.py`
**Fichier** : `backend_worker/celery_tasks.py`

**Action** : Ajouter le feature flag en haut du fichier (après les imports)

```python
import os

# Feature flags pour la migration TaskIQ
USE_TASKIQ_FOR_MAINTENANCE = os.getenv('USE_TASKIQ_FOR_MAINTENANCE', 'false').lower() == 'true'
```

**Action** : Modifier la tâche `cleanup_old_data` pour utiliser le feature flag

```python
@celery.task(name="maintenance.cleanup_old_data", queue="maintenance", bind=True)
def cleanup_old_data(self, days_old: int = 30):
    """Nettoie les anciennes données."""
    
    # Vérifier le feature flag
    if USE_TASKIQ_FOR_MAINTENANCE:
        logger.info(f"[CELERY→TASKIQ] Délégation à TaskIQ pour cleanup_old_data")
        
        # Déléguer à TaskIQ
        from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
        import asyncio
        
        try:
            # Obtenir ou créer une boucle d'événements
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Exécuter la tâche TaskIQ de manière synchrone
            result = loop.run_until_complete(cleanup_old_data_task(days_old=days_old))
            
            logger.info(f"[CELERY→TASKIQ] Résultat TaskIQ: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[CELERY→TASKIQ] Erreur délégation TaskIQ: {e}")
            # Fallback vers Celery
            logger.info(f"[CELERY→TASKIQ] Fallback vers Celery")
    
    # Code Celery existant (ne pas modifier)
    # ... existing implementation ...
```

**Validation** :
- [ ] Le feature flag est ajouté
- [ ] La tâche `cleanup_old_data` utilise le feature flag
- [ ] Le fallback vers Celery fonctionne

---

### T2.4 : Créer le wrapper sync/async pour TaskIQ
**Fichier** : `backend_worker/taskiq_utils.py` (nouveau)

**Contenu** :
```python
"""Utilitaires pour TaskIQ.

Fournit des wrappers pour exécuter des tâches TaskIQ de manière synchrone.
"""
import asyncio
from typing import Any, Callable
from backend_worker.utils.logging import logger


def run_taskiq_sync(task_func: Callable, *args, **kwargs) -> Any:
    """Exécute une tâche TaskIQ de manière synchrone.
    
    Args:
        task_func: Fonction de tâche TaskIQ
        *args: Arguments positionnels
        **kwargs: Arguments nommés
        
    Returns:
        Résultat de la tâche
    """
    try:
        # Obtenir ou créer une boucle d'événements
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Exécuter la tâche de manière synchrone
        result = loop.run_until_complete(task_func(*args, **kwargs))
        
        return result
        
    except Exception as e:
        logger.error(f"[TASKIQ] Erreur exécution synchrone: {e}")
        raise


async def run_taskiq_async(task_func: Callable, *args, **kwargs) -> Any:
    """Exécute une tâche TaskIQ de manière asynchrone.
    
    Args:
        task_func: Fonction de tâche TaskIQ
        *args: Arguments positionnels
        **kwargs: Arguments nommés
        
    Returns:
        Résultat de la tâche
    """
    try:
        result = await task_func(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"[TASKIQ] Erreur exécution asynchrone: {e}")
        raise
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les wrappers fonctionnent correctement
- [ ] Les logs sont corrects

> ⚠️ **Ce wrapper est un FALLBACK TEMPORAIRE**. Il sera remplacé par
> la conversion directe des fonctions en `async def` dans les phases suivantes.
> Ne pas créer de nouvelles fonctions sync qui utilisent ce wrapper.
> Voir `docs/plans/Taskiq_migrations/PLAN_CONVERSION_ASYNC.md` pour la stratégie.

---

### T2.5 : Ajouter le logging différencié
**Fichier** : `backend_worker/taskiq_tasks/maintenance.py`

**Action** : Ajouter des logs différenciés dans la tâche migrée

```python
@broker.task
async def cleanup_old_data_task(days_old: int = 30) -> dict:
    """Nettoie les anciennes données."""
    
    # Log différencié
    logger.info(f"[TASKIQ|MAINTENANCE] Démarrage cleanup_old_data (days_old={days_old})")
    
    # ... existing implementation ...
    
    logger.info(f"[TASKIQ|MAINTENANCE] Fin cleanup_old_data (success={result['success']})")
    return result
```

**Validation** :
- [ ] Les logs utilisent le préfixe `[TASKIQ|MAINTENANCE]`
- [ ] Les logs sont différenciés des logs Celery

---

## 🧪 Tests à Exécuter

### Vérifications de Qualité de Code
```bash
# Exécuter ruff check sur les fichiers modifiés
ruff check backend_worker/taskiq_tasks/ backend_worker/taskiq_utils.py backend_worker/celery_tasks.py

# Vérifier l'absence d'erreurs Pylance dans VS Code
# (Ouvrir les fichiers et vérifier la barre d'état)
```

### Tests Unitaires
```bash
# Exécuter les tests unitaires TaskIQ
python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v

# Exécuter les tests unitaires Celery existants (vérifier qu'ils passent toujours)
python -m pytest tests/unit/worker -q --tb=no
```

### Tests d'Intégration
```bash
# Exécuter les tests d'intégration workers
python -m pytest tests/integration/workers -q --tb=no
```

### Tests de Feature Flag
```bash
# Mode Celery (flag=false)
USE_TASKIQ_FOR_MAINTENANCE=false python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v

# Mode TaskIQ (flag=true)
USE_TASKIQ_FOR_MAINTENANCE=true python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v
```

---

## ✅ Critères d'Acceptation

- [ ] Le fichier `backend_worker/taskiq_tasks/__init__.py` existe
- [ ] Le fichier `backend_worker/taskiq_tasks/maintenance.py` existe
- [ ] Le feature flag `USE_TASKIQ_FOR_MAINTENANCE` est ajouté
- [ ] La tâche `cleanup_old_data` utilise le feature flag
- [ ] Le wrapper sync/async fonctionne
- [ ] Les logs sont différenciés
- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Les tests unitaires TaskIQ passent
- [ ] Les tests unitaires Celery existants passent (0 régression)
- [ ] Les tests d'intégration workers existants passent (0 régression)
- [ ] La tâche fonctionne en mode Celery (flag=false)
- [ ] La tâche fonctionne en mode TaskIQ (flag=true)

---

## 🚨 Points d'Attention

1. **Ne pas modifier** la logique métier existante
2. **Copier** la logique métier depuis `celery_tasks.py` vers `taskiq_tasks/maintenance.py`
3. **Tester** les deux modes (Celery et TaskIQ)
4. **Vérifier** que le fallback vers Celery fonctionne
5. **Logger** avec les préfixes `[TASKIQ]` et `[CELERY→TASKIQ]`

---

## 📞 Support

En cas de problème :
1. Consulter les logs : `docker logs soniquebay-taskiq-worker`
2. Vérifier la configuration Redis : `docker exec soniquebay-redis redis-cli info`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 2 (Migration Pilote)*
*Statut : En cours*
