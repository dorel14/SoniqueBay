# Architecture des Workers Celery - SoniqueBay

## Vue d'ensemble

SoniqueBay utilise une architecture Celery moderne avec **un seul worker autoscale** pour optimiser les ressources du Raspberry Pi 4 tout en maintenant d'excellentes performances.

## Architecture Actuelle (Post-Refactor)

### Worker Unifié avec Autoscale

```yaml
celery-worker:
  command: >
    celery -A backend_worker.celery_app worker
    --autoscale=4,1
    --loglevel=INFO
```

**Caractéristiques :**

- **1 seul conteneur** remplace 9 services spécialisés
- **Autoscale intelligent** : 1 à 4 processus selon la charge
- **Toutes les queues gérées** automatiquement
- **Vectorisation intégrée** : appel direct depuis l'API FastAPI
- **Optimisé RPi4** : mémoire et CPU adaptés

### Simplification Vectorisation (v2.0)

**Avant :** Service séparé `vectorization_listener` + Redis PubSub

```
API FastAPI → Redis Pub → Vectorization Listener → Celery Worker
```

**Après :** Intégration directe dans l'API

```
API FastAPI → Celery Worker
```

**Avantages :**

- ✅ **-1 conteneur** : économie de 256MB RAM
- ✅ **Latence réduite** : pas d'intermédiaire Redis
- ✅ **Maintenance simplifiée** : logique centralisée
- ✅ **Fiabilité accrue** : moins de points de défaillance

## Queues et Routage

| Queue | Description | Priorité | Type |
|-------|-------------|----------|------|
| `scan` | Découverte fichiers audio | Haute | I/O intensive |
| `extract` | Extraction métadonnées | Haute | CPU intensive |
| `batch` | Regroupement données | Haute | Memory intensive |
| `insert` | Insertion base de données | Haute | DB intensive |
| `vector` | Vectorisation audio | Moyenne | CPU intensive |
| `deferred` | Tâches différées | Basse | Mixed |
| `covers` | Téléchargement covers | Basse | API intensive |
| `maintenance` | Tâches maintenance | Basse | Light |

## Optimisations RPi4 Préservées

### Gestion Mémoire

- `worker_max_memory_per_child=524288000` (500MB/processus)
- `worker_max_tasks_per_child=500` (restart fréquent)

### Timeouts Adaptés

- `task_time_limit=7200` (2h pour tâches longues)
- `worker_heartbeat=300` (5 min pour stabilité)

### Communication Optimisée

- SSE pour progression temps réel
- Compression gzip pour gros messages
- Pool Redis optimisé

## Architecture Avant (Legacy)

### 9 Services Spécialisés (Supprimés)

- `scan-worker-1/2` : Découverte fichiers
- `extract-worker-1/2` : Extraction métadonnées
- `batch-worker` : Regroupement données
- `insert-worker-1/2` : Insertion DB
- `vector-worker` : Vectorisation
- `deferred-worker` : Tâches différées
- `vectorization_listener` : Service intermédiaire (supprimé v2.0)

**Problèmes résolus :**

- Consommation RAM élevée (~2.3GB minimum → ~1.5GB)
- Workers idle consommateurs de ressources
- Complexité de déploiement et maintenance
- Latence vectorisation réduite

## Pipeline de Traitement

### Flux de Scan Complet

```
1. scan.discovery() → Queue: scan
   ↓
2. metadata.extract_batch() → Queue: extract
   ↓
3. batch.process_entities() → Queue: batch
   ↓
4. insert.direct_batch() → Queue: insert
   ↓
5. Tâches d'enrichissement → Queue: deferred
```

### Optimisations Pipeline

- **ThreadPoolExecutor** limité à 2 workers (RPi4)
- **Batches intelligents** avec déduplication MusicBrainz
- **Insertion via API uniquement** (architecture respectée)
- **Progression SSE** temps réel

## Monitoring et Observabilité

### Flower Dashboard

- **URL** : <http://localhost:5555>
- **Monitoring** : tâches actives, queues, workers
- **Métriques** : taux de succès, temps d'exécution

### Logs Structurés

```bash
# Suivre l'autoscale
docker logs celery-worker | grep -i autoscale

# Monitorer les processus
docker exec celery-worker ps aux | grep celery
```

### Métriques Clés

- **Nombre de processus** : 1-4 selon charge
- **Utilisation RAM** : < 1.5GB total (simplification vectorisation)
- **Temps de scan** : ~50-100 fichiers/minute
- **Taux de succès** : > 99%
- **Latence vectorisation** : réduite de ~50ms

## Commandes de Gestion

### Démarrage

```bash
# Build et démarrage complet
docker-compose build
docker-compose up -d

# Suivre les logs
docker-compose logs -f celery-worker
```

### Diagnostic

```bash
# Vérifier les processus actifs
docker exec soniquebay-celery-worker ps aux

# Monitorer les queues Redis
docker exec soniquebay-redis redis-cli KEYS "celery*"
```

### Maintenance

```bash
# Redémarrage propre
docker-compose restart celery-worker

# Scale manuel si besoin
docker-compose up -d --scale celery-worker=2
```

## Recommandations d'Utilisation

### Scans Massifs

- L'autoscale monte automatiquement à 4 processus
- Monitorer RAM (< 2GB)
- Éviter scans simultanés multiples

### Usage Normal

- 1 processus minimum = faible consommation
- Scale-up automatique si tâches arrivent
- Retour automatique à 1 processus

## Documentation Liée

- **[Refactor Autoscale](celery_autoscale_refactor.md)** : Détails techniques de la migration
- **[Optimisation Celery](celery_optimization_config.md)** : Configurations de performance
- **[Monitoring Flower](README_FLOWER_MONITORING.md)** : Guide complet monitoring

## Support et Maintenance

### Contacts

- **Issues GitHub** : Signaler bugs ou problèmes
- **Logs détaillés** : Tous les événements tracés
- **Métriques Flower** : Observabilité complète

### Bonnes Pratiques

- Toujours tester sur RPi4 avant déploiement
- Monitorer régulièrement les performances
- Garder les optimisations RPi4 à jour

---

**Architecture optimisée pour Raspberry Pi 4 avec autoscale intelligent**
