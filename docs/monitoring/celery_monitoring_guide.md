# Guide de Monitoring Celery - Mesure de la Taille des Arguments

## Vue d'ensemble

Ce système de monitoring mesure automatiquement la taille des arguments de vos tâches Celery et recommande des limites optimales pour éviter les erreurs `Object of type ellipsis is not JSON serializable`.

## Fichiers du système

### 1. `backend_worker/utils/celery_monitor.py`
- **Fonction** : Module principal de monitoring
- **Fonctions clés** :
  - `measure_celery_task_size()` : Mesure la taille des arguments d'une tâche
  - `update_size_metrics()` : Met à jour les statistiques globales
  - `get_size_summary()` : Génère un rapport détaillé
  - `auto_configure_celery_limits()` : Propose une limite optimale

### 2. `backend_worker/celery_app.py` (modifié)
- **Intégration** : Signal `task_prerun` qui capture les tâches avant exécution
- **Mesure automatique** : Chaque tâche est mesurée et ses statistiques mises à jour
- **Rapport shutdown** : Statistiques complètes lors de l'arrêt du worker

### 3. `scripts/check_celery_metrics.py`
- **Utilisation** : Script autonome pour consulter les métriques
- **Commande** : `python scripts/check_celery_metrics.py`

## Comment ça marche

### Capture automatique
```python
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    size_metrics = measure_celery_task_size(task, task_id)
    update_size_metrics(size_metrics)
```

### Mesure de la taille
```python
def measure_json_size(obj: Any) -> int:
    json_str = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return len(json_str)
```

## Utilisation pratique

### 1. Monitoring passif
Le système fonctionne automatiquement. Les métriques s'accumulent dans `CELERY_SIZE_METRICS`.

### 2. Consultation des statistiques
```bash
# Voir le rapport complet
python scripts/check_celery_metrics.py
```

Exemple de sortie :
```
=== MÉTRIQUES DE TAILLE CELERY ===
Tâches analysées: 15
Taille max args: 45,678 caractères
Taille max kwargs: 12,345 caractères  
Taille moyenne args: 23,456 caractères
Taille moyenne kwargs: 5,678 caractères
Tâches tronquées: 2
Tâche la plus volumineuse: extract_metadata_batch (args)
Limite recommandée: 54,813 caractères

Recommandations:
- Si le max est < 100KB → limite = 131072 (128KB)
- Si le max est < 500KB → limite = 524288 (512KB)  
- Si le max est < 1MB → limite = 1048576 (1MB)
- Si le max est > 1MB → limite = 2097152 (2MB)
```

### 3. Application des recommandations
Si le rapport recommande une limite de 150,000 caractères :
```python
# Dans celery_app.py, remplacer :
celery.amqp.argsrepr_maxsize = 150000
celery.amqp.kwargsrepr_maxsize = 150000
```

### 4. Remise à zéro des métriques
```python
from backend_worker.utils.celery_monitor import reset_metrics
reset_metrics()
```

## Détection des problèmes

### Rapports d'alerte automatique
Les tâches avec des arguments > 1KB sont loggées avec un rapport détaillé :
```
[CELERY MONITOR] Tâche: extract_metadata_batch
[CELERY MONITOR] ID: 5ff7c033-b6c3-4a88-8b46-9d175f7a7b98
[CELERY MONITOR] Args: 45,678 caractères (⚠ TRONQUÉ)
[CELERY MONITOR] Kwargs: 0 caractères (✓)
[CELERY MONITOR] Limite actuelle: 1,024 caractères
```

### Rapport final du worker
À l'arrêt du worker, un rapport complet est généré :
```
[WORKER SHUTDOWN] Rapport final monitoring worker extract-worker-1@08bdfa40a251:
[WORKER SHUTDOWN] Tâches analysées: 127
[WORKER SHUTDOWN] Taille max args: 67,890 caractères
[WORKER SHUTDOWN] ...
[WORKER SHUTDOWN] Limite recommandée: 81,468 caractères
```

## Recommandations de limites

| Taille détectée | Limite recommandée | Justification |
|----------------|-------------------|---------------|
| < 100KB | 128KB (131072) | Standard pour la plupart des cas |
| 100KB - 500KB | 512KB (524288) | Bibliothèques musicales volumineuses |
| 500KB - 1MB | 1MB (1048576) | Collections très volumineuses |
| > 1MB | 2MB (2097152) | Très gros datasets ou lots massifs |

## Dépannage

### Le problème persiste
1. Vérifiez les métriques : `python scripts/check_celery_metrics.py`
2. Appliquez la limite recommandée
3. Redémarrez les workers Celery
4. Vérifiez que la limite est bien appliquée

### Aucune métrique n'est collectée
1. Vérifiez les logs pour les messages `[TASK PRERUN]`
2. Confirmez que les workers Celery tournent bien
3. Exécutez quelques tâches pour générer des métriques

### Interprétation des logs
- `✓` : Taille acceptable, pas de troncature
- `⚠ TRONQUÉ` : Dépasse la limite actuelle

## Bonnes pratiques

1. **Laissez tourner le monitoring** pendant quelques heures/jours pour avoir des métriques représentatives
2. **Consultez régulièrement** les rapports pour ajuster les limites
3. **Appliquez les recommandations** dès qu'une limite trop petite est détectée
4. **Remettez à zéro** après des modifications importantes de la logique métier

## Évolution future

Le système peut être étendu pour :
- Sauvegarder les métriques en base
- Envoyer des alertes automatiques
- Ajuster les limites dynamiquement
- Générer des graphiques de tendances