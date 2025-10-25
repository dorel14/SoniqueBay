# ARCHITECTURE DE SCAN OPTIMISÉE POUR SONIQUEBAY

## **PROBLÈMES IDENTIFIÉS DANS L'ARCHITECTURE ACTUELLE**

### **Goulots d'étranglement critiques :**

1. **Architecture monolithique** : Tout le scan dans une seule tâche `scan_music_task`
2. **Pas de parallélisation réelle** : Même avec l'optimiseur, tout reste dans un seul processus asyncio
3. **Goulot d'étranglement HTTP** : Appels HTTP constants vers l'API backend pour chaque insertion
4. **Configuration Celery sous-optimale** : Prefetch faible, pas de vraie distribution des tâches
5. **Pas de séparation des étapes** : Scan, extraction, et insertion mélangés

### **Impact sur les performances :**

- **10+ heures** pour scanner une bibliothèque sans résultat
- **Mémoire épuisée** avec les gros batches
- **CPU sous-utilisé** avec la configuration actuelle
- **I/O disque séquentiel** au lieu de parallèle

## **ARCHITECTURE OPTIMISÉE PROPOSÉE**

### **1. PIPELINE DISTRIBUÉ EN 4 ÉTAPES**

'''
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ÉTAPE 1       │    │   ÉTAPE 2       │    │   ÉTAPE 3       │    │   ÉTAPE 4       │
│   DISCOVERY     │───▶│   EXTRACTION    │───▶│   BATCHING      │───▶│   INSERTION     │
│   (I/O Bound)   │    │   (CPU Bound)   │    │   (Memory)      │    │   (DB Bound)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │                       │
        ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Queue: scan     │    │ Queue: extract  │    │ Queue: batch    │    │ Queue: insert   │
│ Workers: 8-16   │    │ Workers: 4-8    │    │ Workers: 2-4    │    │ Workers: 8-16   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
'''

### **2. CONFIGURATION CELERY OPTIMISÉE**

#### **Queues spécialisées :**

```python
# Queue DISCOVERY (I/O intensive)
'queue_scan': {
    'exchange': 'scan',
    'routing_key': 'scan',
    'worker_concurrency': 16,
    'worker_prefetch_multiplier': 8
}

# Queue EXTRACTION (CPU intensive)
'queue_extract': {
    'exchange': 'extract',
    'routing_key': 'extract',
    'worker_concurrency': 8,
    'worker_prefetch_multiplier': 2
}

# Queue BATCHING (Memory intensive)
'queue_batch': {
    'exchange': 'batch',
    'routing_key': 'batch',
    'worker_concurrency': 4,
    'worker_prefetch_multiplier': 1
}

# Queue INSERTION (DB intensive)
'queue_insert': {
    'exchange': 'insert',
    'routing_key': 'insert',
    'worker_concurrency': 16,
    'worker_prefetch_multiplier': 4
}
```

### **3. NOUVELLES TÂCHES OPTIMISÉES**

#### **Tâche 1: Discovery parallélisé**

```python
@celery.task(name='scan_directory_parallel', queue='scan')
def scan_directory_parallel(directory: str, batch_size: int = 10000):
    """Scan un répertoire et distribue les fichiers trouvés."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if is_music_file(filename):
                files.append(os.path.join(root, filename))
                if len(files) >= batch_size:
                    # Distribuer le batch à l'extraction
                    celery.send_task('extract_metadata_batch',
                                   args=[files], queue='extract')
                    files = []
    # Dernier batch
    if files:
        celery.send_task('extract_metadata_batch', args=[files], queue='extract')
```

#### **Tâche 2: Extraction massive**

```python
@celery.task(name='extract_metadata_batch', queue='extract')
def extract_metadata_batch(file_paths: List[str]):
    """Extrait les métadonnées de milliers de fichiers en parallèle."""
    results = []

    # Parallélisation massive avec ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = []
        for file_path in file_paths:
            future = executor.submit(extract_single_file_metadata, file_path)
            futures.append(future)

        # Collecter les résultats
        for future in concurrent.futures.as_completed(futures):
            try:
                metadata = future.result()
                if metadata:
                    results.append(metadata)
            except Exception as e:
                logger.error(f"Erreur extraction: {e}")

    # Envoyer vers le batching
    if results:
        celery.send_task('batch_entities', args=[results], queue='batch')
```

#### **Tâche 3: Batching intelligent**

```python
@celery.task(name='batch_entities', queue='batch')
def batch_entities(metadata_list: List[Dict]):
    """Groupe les métadonnées par artistes/albums pour insertion optimisée."""
    # Regrouper par artistes
    artists_by_name = {}
    albums_by_key = {}
    tracks_by_artist = {}

    for metadata in metadata_list:
        artist_name = metadata.get('artist', 'Unknown')
        if artist_name not in artists_by_name:
            artists_by_name[artist_name] = {
                'name': artist_name,
                'musicbrainz_artistid': metadata.get('musicbrainz_artistid')
            }

        # Regrouper les tracks par artiste
        if artist_name not in tracks_by_artist:
            tracks_by_artist[artist_name] = []
        tracks_by_artist[artist_name].append(metadata)

    # Préparer les batches d'insertion
    insertion_data = {
        'artists': list(artists_by_name.values()),
        'albums': [],  # À construire depuis les métadonnées
        'tracks': []
    }

    # Envoyer vers l'insertion directe
    celery.send_task('insert_batch_direct', args=[insertion_data], queue='insert')
```

#### **Tâche 4: Insertion directe en base**

```python
@celery.task(name='insert_batch_direct', queue='insert')
def insert_batch_direct(insertion_data: Dict):
    """Insère directement en base sans passer par l'API HTTP."""
    # Connexion directe à la base de données
    # Insertion en batch avec SQLAlchemy Core
    # Commit par transaction de 1000 éléments
```

### **4. OPTIMISATIONS TECHNIQUES**

#### **A. Configuration Celery haute performance :**

```python
celery.conf.update(
    # Optimisations générales
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Timeouts adaptés
    task_time_limit=3600,
    task_soft_time_limit=3300,

    # Sérialisation optimisée
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Redis optimisé
    redis_max_connections=100,
    broker_pool_limit=20,
)
```

#### **B. Pool de connexions base de données :**

```python
# Configuration SQLAlchemy pour haute concurrence
DATABASE_CONFIG = {
    'pool_size': 50,
    'max_overflow': 100,
    'pool_pre_ping': True,
    'pool_recycle': 3600,
}
```

#### **C. Cache Redis distribué :**

```python
# Cache pour éviter les recalculs
ARTIST_CACHE_TTL = 7200  # 2 heures
ALBUM_CACHE_TTL = 3600   # 1 heure
TRACK_CACHE_TTL = 1800   # 30 minutes
```

### **5. MÉTRIQUES ET MONITORING**

#### **Métriques de performance cibles :**

- **Temps de scan** : < 30 minutes pour 100k fichiers
- **Débit** : > 1000 fichiers/seconde
- **Utilisation CPU** : > 80% sur tous les cœurs
- **Utilisation mémoire** : < 2GB par worker
- **Taux d'erreur** : < 1%

#### **Monitoring en temps réel :**

```python
# Métriques collectées
SCAN_METRICS = {
    'files_discovered': 0,
    'files_processed': 0,
    'extraction_rate': 0.0,
    'insertion_rate': 0.0,
    'error_rate': 0.0,
    'memory_usage': 0.0,
    'queue_sizes': {}
}
```

### **6. DÉPLOIEMENT OPTIMISÉ**

#### **Docker Compose optimisé :**

```yaml
version: '3.8'
services:
  # Workers spécialisés
  scan_workers:
    image: soniquebay-worker
    command: celery -A backend_worker worker --queues=scan --concurrency=16
    deploy:
      replicas: 4

  extract_workers:
    image: soniquebay-worker
    command: celery -A backend_worker worker --queues=extract --concurrency=8
    deploy:
      replicas: 2

  batch_workers:
    image: soniquebay-worker
    command: celery -A backend_worker worker --queues=batch --concurrency=4
    deploy:
      replicas: 1

  insert_workers:
    image: soniquebay-worker
    command: celery -A backend_worker worker --queues=insert --concurrency=16
    deploy:
      replicas: 4
```

## **BÉNÉFICES ATTENDUS**

### **Performance :**

- **×20 à ×50** plus rapide (30 minutes au lieu de 10+ heures)
- **Utilisation optimale** des ressources CPU/mémoire/disque
- **Parallélisation massive** sur tous les cœurs disponibles

### **Fiabilité :**

- **Tolérance aux pannes** avec retry automatique
- **Monitoring avancé** avec métriques temps réel
- **Gestion d'erreurs** granulaire par étape

### **Maintenabilité :**

- **Séparation claire** des responsabilités
- **Tests unitaires** par composant
- **Évolution facile** du pipeline

## **PLAN DE MISE EN ŒUVRE**

### **Phase 1 : Architecture de base (1-2 jours)**

1. Créer les 4 nouvelles tâches Celery
2. Configurer les queues spécialisées
3. Implémenter le système de découverte parallélisé

### **Phase 2 : Optimisation extraction (2-3 jours)**

1. Paralléliser l'extraction des métadonnées
2. Optimiser la gestion mémoire
3. Ajouter le cache distribué

### **Phase 3 : Insertion directe (3-4 jours)**

1. Implémenter l'insertion directe en base
2. Optimiser les transactions
3. Ajouter le monitoring

### **Phase 4 : Tests et déploiement (2-3 jours)**

1. Tests de charge avec bibliothèque réelle
2. Monitoring et ajustements
3. Déploiement en production

## **CONCLUSION**

Cette architecture transforme un système de scan monolithique et lent en un pipeline distribué haute performance capable de traiter des centaines de milliers de fichiers en quelques minutes au lieu d'heures. L'approche modulaire permet une maintenance facile et une évolutivité horizontale.

**Résultat attendu** : Scan de bibliothèque musicale en **< 30 minutes** au lieu de **10+ heures**.
