# CONFIGURATION CELERY OPTIMISÉE POUR SCAN HAUTE PERFORMANCE

## **ANALYSE DE LA CONFIGURATION ACTUELLE**

### **Problèmes identifiés :**
1. **Prefetch multiplier trop faible** (1-4 au lieu de 8-16)
2. **Concurrency mal adaptée** (1-2 workers au lieu de 8-16)
3. **Pas de séparation des queues** par type de tâche
4. **Timeouts trop courts** pour les tâches longues
5. **Pas d'optimisation Redis** pour haute concurrence

## **CONFIGURATION OPTIMISÉE PROPOSÉE**

### **1. CONFIGURATION GLOBALE OPTIMISÉE**

```python
# backend_worker/celery_app.py - Configuration mise à jour
celery.conf.update(
    # === OPTIMISATIONS GÉNÉRALES ===
    # Acknowledgment optimisé pour éviter les pertes
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_ignore_result=False,  # Nécessaire pour le monitoring

    # === SÉRIALISATION OPTIMISÉE ===
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_accept_content=['json'],

    # === TIMEOUTS ADAPTÉS ===
    task_time_limit={
        'scan_directory_parallel': 7200,      # 2h pour découverte massive
        'extract_metadata_batch': 3600,       # 1h pour extraction intensive
        'batch_entities': 1800,               # 30min pour traitement mémoire
        'insert_batch_direct': 3600,          # 1h pour insertions DB
    },

    task_soft_time_limit={
        'scan_directory_parallel': 6600,      # 110min
        'extract_metadata_batch': 3300,       # 55min
        'batch_entities': 1500,               # 25min
        'insert_batch_direct': 3300,          # 55min
    },

    # === CONTRÔLE DE FLUX ===
    worker_prefetch_multiplier=1,  # Contrôlé dynamiquement par queue
    worker_max_tasks_per_child=1000,  # Éviter les fuites mémoire
    worker_disable_rate_limits=False,

    # === CONNEXIONS REDIS OPTIMISÉES ===
    redis_max_connections=200,        # Augmenté pour haute concurrence
    broker_pool_limit=50,             # Pool de connexions plus grand
    result_backend_transport_options={
        'master_name': 'mymaster',     # Si Redis Sentinel
        'socket_timeout': 30,
        'socket_connect_timeout': 30,
        'retry_on_timeout': True,
    },

    # === COMPRESSION POUR GROS MESSAGES ===
    task_compression='gzip',          # Compression des messages volumineux
    result_compression='gzip',

    # === ZONE TEMPORELLE ===
    timezone='Europe/Paris',
    enable_utc=True,
)
```

### **2. DÉFINITION DES QUEUES SPÉCIALISÉES**

```python
# Queues optimisées pour chaque étape du pipeline
task_queues = {
    # === QUEUE DISCOVERY (I/O BOUND) ===
    'scan': {
        'exchange': 'scan',
        'routing_key': 'scan',
        'delivery_mode': 2,  # Persistant
        'arguments': {
            'x-max-priority': 10,  # Priorité maximale
        }
    },

    # === QUEUE EXTRACTION (CPU BOUND) ===
    'extract': {
        'exchange': 'extract',
        'routing_key': 'extract',
        'delivery_mode': 1,  # Non-persistant (plus rapide)
        'arguments': {
            'x-max-priority': 8,
        }
    },

    # === QUEUE BATCHING (MEMORY BOUND) ===
    'batch': {
        'exchange': 'batch',
        'routing_key': 'batch',
        'delivery_mode': 1,
        'arguments': {
            'x-max-priority': 6,
        }
    },

    # === QUEUE INSERTION (DB BOUND) ===
    'insert': {
        'exchange': 'insert',
        'routing_key': 'insert',
        'delivery_mode': 2,  # Persistant pour fiabilité
        'arguments': {
            'x-max-priority': 9,  # Haute priorité
        }
    },

    # === QUEUE DIFFÉRÉE (BACKGROUND) ===
    'deferred': {
        'exchange': 'deferred',
        'routing_key': 'deferred',
        'delivery_mode': 1,
        'arguments': {
            'x-max-priority': 3,  # Basse priorité
        }
    }
}
```

### **3. ROUTAGE INTELLIGENT DES TÂCHES**

```python
# Routes optimisées selon le type de tâche
task_routes = {
    # === TÂCHES DE SCAN ===
    'scan_directory_parallel': {'queue': 'scan'},
    'scan_directory_chunk': {'queue': 'scan'},
    'scan_single_file': {'queue': 'scan'},

    # === TÂCHES D'EXTRACTION ===
    'extract_metadata_batch': {'queue': 'extract'},
    'extract_single_file': {'queue': 'extract'},
    'extract_audio_features_batch': {'queue': 'extract'},

    # === TÂCHES DE BATCHING ===
    'batch_entities': {'queue': 'batch'},
    'group_by_artist': {'queue': 'batch'},
    'prepare_insertion_batch': {'queue': 'batch'},

    # === TÂCHES D'INSERTION ===
    'insert_batch_direct': {'queue': 'insert'},
    'insert_artists_batch': {'queue': 'insert'},
    'insert_albums_batch': {'queue': 'insert'},
    'insert_tracks_batch': {'queue': 'insert'},
    'insert_covers_batch': {'queue': 'insert'},

    # === TÂCHES DIFFÉRÉES ===
    'enrich_*': {'queue': 'deferred'},
    'vectorize_*': {'queue': 'deferred'},
    'cleanup_*': {'queue': 'deferred'},
}
```

### **4. CONFIGURATION DYNAMIQUE PAR WORKER**

```python
# Configuration dynamique selon le type de worker
PREFETCH_MULTIPLIERS = {
    'scan': 16,        # I/O bound - prefetch élevé
    'extract': 4,      # CPU bound - prefetch modéré
    'batch': 2,        # Memory bound - prefetch faible
    'insert': 8,       # DB bound - prefetch moyen
    'deferred': 6,     # Mixed - prefetch moyen
}

CONCURRENCY_SETTINGS = {
    'scan': 16,        # 16 workers pour I/O parallèle
    'extract': 8,      # 8 workers pour CPU parallèle
    'batch': 4,        # 4 workers pour mémoire
    'insert': 16,      # 16 workers pour DB parallèle
    'deferred': 6,     # 6 workers pour tâches background
}

@worker_init.connect
def configure_worker_optimized(sender=None, **kwargs):
    """Configuration dynamique ultra-optimisée par worker."""
    worker_name = sender.hostname
    app = sender.app

    # Détection automatique du type de worker
    worker_type = 'unknown'
    for queue_name in PREFETCH_MULTIPLIERS:
        if queue_name in worker_name:
            worker_type = queue_name
            break

    if worker_type != 'unknown':
        # Appliquer les optimisations
        app.conf.worker_prefetch_multiplier = PREFETCH_MULTIPLIERS[worker_type]
        app.conf.worker_concurrency = CONCURRENCY_SETTINGS[worker_type]

        # Optimisations spécifiques par type
        if worker_type == 'scan':
            # Optimisations I/O
            app.conf.worker_max_memory_per_child = 512 * 1024 * 1024  # 512MB
        elif worker_type == 'extract':
            # Optimisations CPU
            app.conf.worker_max_tasks_per_child = 500
        elif worker_type == 'batch':
            # Optimisations mémoire
            app.conf.worker_max_memory_per_child = 1024 * 1024 * 1024  # 1GB
        elif worker_type == 'insert':
            # Optimisations DB
            app.conf.worker_max_tasks_per_child = 2000

        logger.info(f"[OPTIMIZED] {worker_name} → Type: {worker_type} | "
                   f"Prefetch: {PREFETCH_MULTIPLIERS[worker_type]} | "
                   f"Concurrency: {CONCURRENCY_SETTINGS[worker_type]}")
```

### **5. CONFIGURATION REDIS OPTIMISÉE**

```python
# Configuration Redis pour haute performance
REDIS_CONFIG = {
    'host': 'redis',
    'port': 6379,
    'db': 0,
    'password': os.getenv('REDIS_PASSWORD'),
    'socket_connect_timeout': 30,
    'socket_timeout': 30,
    'retry_on_timeout': True,
    'max_connections': 100,
    'decode_responses': True,
    'encoding': 'utf-8',
    'encoding_errors': 'strict'
}

# Configuration Celery avec Redis optimisé
celery.conf.update(
    broker_url=f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
    result_backend=f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
    redis_max_connections=REDIS_CONFIG['max_connections'],
    broker_transport_options={
        'socket_connect_timeout': REDIS_CONFIG['socket_connect_timeout'],
        'socket_timeout': REDIS_CONFIG['socket_timeout'],
        'retry_on_timeout': REDIS_CONFIG['retry_on_timeout'],
    },
    result_backend_transport_options={
        'socket_connect_timeout': REDIS_CONFIG['socket_connect_timeout'],
        'socket_timeout': REDIS_CONFIG['socket_timeout'],
        'retry_on_timeout': REDIS_CONFIG['retry_on_timeout'],
    }
)
```

### **6. DOCKER COMPOSE OPTIMISÉ**

```yaml
version: '3.8'

services:
  # === REDIS CLUSTER OPTIMISÉ ===
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2GB --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ulimits:
      nofile:
        soft: 65536
        hard: 65536

  # === WORKERS SCAN (I/O BOUND) ===
  scan-worker-1:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=scan-worker-1@%h --queues=scan --concurrency=16 --prefetch-multiplier=16
    environment:
      - WORKER_TYPE=scan
    volumes:
      - ./music_library:/music:ro
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  scan-worker-2:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=scan-worker-2@%h --queues=scan --concurrency=16 --prefetch-multiplier=16
    environment:
      - WORKER_TYPE=scan

  # === WORKERS EXTRACTION (CPU BOUND) ===
  extract-worker-1:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=extract-worker-1@%h --queues=extract --concurrency=8 --prefetch-multiplier=4
    environment:
      - WORKER_TYPE=extract
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

  # === WORKERS BATCHING (MEMORY BOUND) ===
  batch-worker:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=batch-worker@%h --queues=batch --concurrency=4 --prefetch-multiplier=2
    environment:
      - WORKER_TYPE=batch
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  # === WORKERS INSERTION (DB BOUND) ===
  insert-worker-1:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=insert-worker-1@%h --queues=insert --concurrency=16 --prefetch-multiplier=8
    environment:
      - WORKER_TYPE=insert

  insert-worker-2:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --hostname=insert-worker-2@%h --queues=insert --concurrency=16 --prefetch-multiplier=8
    environment:
      - WORKER_TYPE=insert

  # === MONITORING ===
  celery-monitor:
    image: celery:latest
    command: celery -A backend_worker events
    depends_on:
      - redis
```

## **COMMANDES DE DÉPLOIEMENT**

### **Démarrage des workers optimisés :**
```bash
# Workers Scan (I/O)
celery -A backend_worker worker --hostname=scan-1@%h --queues=scan --concurrency=16 --prefetch-multiplier=16 --loglevel=INFO

# Workers Extraction (CPU)
celery -A backend_worker worker --hostname=extract-1@%h --queues=extract --concurrency=8 --prefetch-multiplier=4 --loglevel=INFO

# Workers Insertion (DB)
celery -A backend_worker worker --hostname=insert-1@%h --queues=insert --concurrency=16 --prefetch-multiplier=8 --loglevel=INFO
```

### **Monitoring des performances :**
```bash
# Surveiller les queues
celery -A backend_worker inspect active_queues

# Surveiller les workers actifs
celery -A backend_worker inspect active

# Statistiques détaillées
celery -A backend_worker inspect stats
```

## **BÉNÉFICES ATTENDUS**

### **Performance :**
- **×10 à ×20** plus de débit grâce à la parallélisation massive
- **Utilisation CPU** : 80-90% au lieu de 10-20%
- **Latence réduite** : Files d'attente optimisées
- **Mémoire optimisée** : Pas de surcharge mémoire

### **Fiabilité :**
- **Tolérance aux pannes** : Workers peuvent redémarrer indépendamment
- **Reprise sur erreur** : Tâches automatiquement reroutées
- **Monitoring avancé** : Visibilité complète du pipeline

### **Évolutivité :**
- **Ajout facile** de nouveaux workers
- **Répartition de charge** automatique
- **Configuration dynamique** selon la charge

Cette configuration transforme Celery d'un système basique à une plateforme de traitement distribué haute performance capable de gérer des millions de fichiers musicaux efficacement.