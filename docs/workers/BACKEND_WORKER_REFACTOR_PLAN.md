# Plan de Refactoring Backend Worker

## Problèmes Identifiés

1. **Modules non utilisés** : `optimized_batch.py`, `optimized_scan.py`, `optimized_extract.py` ne sont jamais importés
2. **Noms incohérents** : Mélange de conventions (`worker_metadata.py`, `scan_worker.py`, `tasks.py`)
3. **Mélange de responsabilités** : Tout dans `background_tasks/` sans séparation
4. **Duplication** : Fonctionnalités duplicées entre fichiers
5. **Configuration dispersée** : Tâches Celery définies à plusieurs endroits

## Nouvelle Architecture

### Structure Proposée

```
backend_worker/
├── workers/                    # Tous les workers organisés par type
│   ├── scan/                   # Workers de découverte et scan
│   │   ├── __init__.py
│   │   ├── scan_worker.py      # Découverte fichiers (rename: scan_worker.py)
│   │   ├── metadata_extractor.py # Extraction métadonnées (rename: extract_metadata_batch)
│   │   └── batch_processor.py  # Traitement par batches (rename: batch_entities)
│   ├── metadata/              # Workers d'enrichissement
│   │   ├── __init__.py
│   │   ├── enrichment_worker.py # Enrichissement BPM, genres (extract from worker_metadata.py)
│   │   ├── audio_analysis.py    # Analyse audio (extract from worker_metadata.py)
│   │   └── genres_tags.py       # Gestion genres/tags (extract from worker_metadata.py)
│   ├── covers/                # Workers covers/images
│   │   ├── __init__.py
│   │   ├── embedded_covers.py   # Covers intégrées (rename: extract_embedded_covers_batch)
│   │   ├── artist_images.py     # Images d'artistes (rename: extract_artist_images_batch)
│   │   └── cover_processor.py   # Traitement covers (rename: process_track_covers_batch)
│   ├── vectorization/         # Workers vectorisation
│   │   ├── __init__.py
│   │   ├── vector_worker.py     # Calcul vecteurs (rename: calculate_vector)
│   │   ├── model_training.py    # Entraînement modèles
│   │   └── monitoring.py        # Monitoring vectorisation (extract from worker_vectorization_monitoring.py)
│   └── deferred/              # Workers différés
│       ├── __init__.py
│       ├── enrichment_deferred.py # Enrichissement différé (extract from worker_deferred_enrichment.py)
│       ├── covers_deferred.py     # Covers différées (extract from worker_deferred_covers.py)
│       └── vectors_deferred.py    # Vecteurs différés (extract from worker_deferred_vectors.py)
│
├── celery_tasks.py            # TOUTES les tâches Celery centralisées
├── celery_beat_tasks.py       # Tâches planifiées centralisées
├── tasks/                     # Tasks legacy pour compatibilité
│   ├── __init__.py
│   └── main_tasks.py          # Tâches principales (extract from tasks.py)
│
├── services/                  # Services métier (existant, à conserver)
└── utils/                     # Utilitaires (existant, à conserver)
```

### Conventions de Nommage

1. **Workers** : Un fichier par responsabilité spécialisée
2. **Tâches Celery** : Toutes centralisées dans `celery_tasks.py`
3. **Noms de tâches** : Format `worker_type.function_name`
   - `scan.discovery` (anciennement `scan_music_task`)
   - `metadata.enrich_tracks_batch`
   - `covers.extract_embedded_covers_batch`
   - `vectorization.calculate_vector`

### Plan d'Exécution

#### Étape 1: Créer la nouvelle structure
- Créer les dossiers `workers/scan/`, `workers/metadata/`, etc.
- Créer `celery_tasks.py` centralisé

#### Étape 2: Migrer les fichiers
- **Supprimer** les modules non utilisés : `optimized_*.py`
- **Renommer et déplacer** les fichiers existants
- **Extraire** les responsabilités multiples en fichiers séparés

#### Étape 3: Corriger les imports
- Mettre à jour tous les imports dans le codebase
- Mettre à jour la configuration Celery

#### Étape 4: Tester
- Vérifier que toutes les tâches Celery fonctionnent
- Tester les workflows de scan → enrichissement → vectorisation

### Gains Attendus

1. **Maintenabilité** : Responsabilités clairement séparées
2. **Cohérence** : Convention de nommage uniforme
3. **Testabilité** : Chaque worker peut être testé indépendamment
4. **Évolutivité** : Ajout de nouveaux workers facilité
5. **Performance** : Pas de code inutilisé

## Fichiers à Supprimer

- `background_tasks/optimized_batch.py` (non utilisé)
- `background_tasks/optimized_scan.py` (non utilisé)  
- `background_tasks/optimized_extract.py` (non utilisé)

## Fichiers à Renommer/Déplacer

| Ancien | Nouveau | Action |
|--------|---------|--------|
| `background_tasks/scan_worker.py` | `workers/scan/scan_worker.py` | Déplacer |
| `background_tasks/worker_metadata.py` | Diviser en `workers/metadata/*.py` | Diviser |
| `background_tasks/covers_worker.py` | Diviser en `workers/covers/*.py` | Diviser |
| `background_tasks/tasks.py` | `tasks/main_tasks.py` | Déplacer |
| `background_tasks/worker_*.py` | `workers/*/worker_*.py` | Déplacer |

## Configuration Celery

Mettre à jour `celery_app.py` pour pointer vers les nouveaux modules :

```python
celery = Celery(
    'soniquebay',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=[
        'backend_worker.celery_tasks',           # Centralisé
        'backend_worker.celery_beat_tasks',      # Centralisé
        'backend_worker.workers.scan',
        'backend_worker.workers.metadata', 
        'backend_worker.workers.covers',
        'backend_worker.workers.vectorization',
        'backend_worker.workers.deferred',
    ]
)