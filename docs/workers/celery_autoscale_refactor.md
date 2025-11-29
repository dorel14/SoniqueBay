# Refactorisation Celery - Architecture Autoscale Unifiée

## Vue d'ensemble

Cette refactorisation remplace les **9 services worker spécialisés** par un **seul worker Celery avec autoscale** pour optimiser l'utilisation des ressources du Raspberry Pi 4.

## Architecture Avant (9 services)

### Services supprimés :
- `scan-worker-1` et `scan-worker-2` (queues: scan)
- `extract-worker-1` et `extract-worker-2` (queues: extract)
- `batch-worker` (queue: batch)
- `insert-worker-1` et `insert-worker-2` (queues: insert)
- `vector-worker` (queue: vector)
- `deferred-worker` (queue: deferred)

### Problèmes identifiés :
- **Consommation mémoire élevée** : 9 conteneurs × ~256MB = ~2.3GB RAM minimum
- **Sous-utilisation CPU** : Workers idle consomment des ressources inutilement
- **Complexité de déploiement** : Gestion de 9 services différents
- **Limites RPi4** : 4 cœurs max, mémoire limitée

## Nouvelle Architecture (1 service autoscale)

### Service unifié :
```yaml
celery-worker:
  command: >
    celery -A backend_worker.celery_app worker
    --autoscale=4,1
    --loglevel=INFO
    --hostname=celery-worker@%h
```

### Avantages :
- **Adaptation automatique** : 1 processus minimum, jusqu'à 4 maximum selon charge
- **Optimisation ressources** : Pas de workers idle
- **Simplicité** : 1 seul service à gérer
- **Performance préservée** : Toutes les optimisations RPi4 maintenues

## Configuration Autoscale

### Paramètres optimaux pour RPi4 :
```bash
--autoscale=4,1  # Max 4 processus, min 1
```

### Logique de scaling :
- **Scale-up** : Quand des tâches arrivent dans les queues
- **Scale-down** : Quand il n'y a plus de tâches (retour à 1 processus)
- **Limites RPi4** : Maximum 4 processus (4 cœurs)

## Queues Gérées

Le worker unifié gère automatiquement toutes les queues :

| Queue | Type | Priorité | Description |
|-------|------|----------|-------------|
| `scan` | I/O bound | Haute | Découverte fichiers |
| `extract` | CPU bound | Haute | Extraction métadonnées |
| `batch` | Memory bound | Haute | Regroupement données |
| `insert` | DB bound | Haute | Insertion base |
| `vector` | CPU bound | Moyenne | Vectorisation |
| `deferred` | Mixed | Basse | Tâches différées |
| `covers` | API bound | Basse | Téléchargement covers |
| `maintenance` | Light | Basse | Tâches maintenance |

## Optimisations RPi4 Préservées

### Gestion mémoire :
- `worker_max_memory_per_child=524288000` (500MB par processus)
- `worker_max_tasks_per_child=500` (restart fréquent)

### Timeouts optimisés :
- `task_time_limit=7200` (2h pour tâches longues)
- `worker_heartbeat=300` (5 min pour stabilité RPi4)

### Communication optimisée :
- SSE pour progression temps réel
- Compression gzip pour gros messages
- Pool Redis optimisé

## Migration Technique

### Code modifié :
1. **`docker-compose.yml`** : Remplacement des 9 services par 1
2. **`celery_app.py`** : Suppression configurations spécifiques par worker
3. **`worker_init`** : Adaptation pour autoscale

### Compatibilité :
- **Toutes les tâches existantes** fonctionnent sans modification
- **Routage par queue** préservé
- **API et fonctionnalités** inchangées

## Monitoring et Observabilité

### Métriques à surveiller :
- **Nombre de processus actifs** : Via Flower ou logs
- **Utilisation CPU/RAM** : Pendant les scans
- **Temps de traitement** : Files/seconde
- **Scale-up/down events** : Dans les logs

### Commandes de diagnostic :
```bash
# Vérifier le nombre de processus
docker exec celery-worker ps aux | grep celery

# Monitorer via Flower
# http://localhost:5555

# Logs autoscale
docker logs celery-worker | grep -i autoscale
```

## Recommandations d'Utilisation

### Pour scans massifs :
- Le worker scale automatiquement à 4 processus
- Monitorer la RAM (max 2GB alloué)
- Éviter scans simultanés multiples

### Pour usage normal :
- 1 processus minimum = faible consommation
- Scale-up automatique si besoin
- Retour à 1 processus après inactivité

### Maintenance :
- Redémarrage propre : `docker-compose restart celery-worker`
- Logs détaillés pour diagnostic
- Monitoring Flower pour observabilité

## Tests et Validation

### Tests à effectuer :
1. **Scan bibliothèque** : Vérifier scale-up automatique
2. **Performance** : Comparer temps de traitement
3. **Stabilité** : Surveiller mémoire et CPU
4. **Recovery** : Test redémarrage automatique

### Métriques de succès :
- **Temps de scan** : Préservé ou amélioré
- **Consommation RAM** : Réduite de ~60%
- **Utilisation CPU** : Plus efficace
- **Fiabilité** : Pas de crashes ou timeouts

## Conclusion

Cette refactorisation apporte :
- **Optimisation ressources** : -60% RAM, meilleure utilisation CPU
- **Simplicité opérationnelle** : 1 service au lieu de 9
- **Performance préservée** : Toutes optimisations RPi4 maintenues
- **Évolutivité** : Architecture prête pour futures extensions

L'autoscale permet une **adaptation intelligente** à la charge tout en respectant les contraintes matérielles du Raspberry Pi 4.