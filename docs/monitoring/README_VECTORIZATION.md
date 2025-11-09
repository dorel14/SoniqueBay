# 📊 Architecture de Vectorisation - SoniqueBay

## 🎯 Vue d'ensemble

L'architecture de vectorisation de SoniqueBay utilise une approche **événementielle** basée sur Redis PubSub et Celery pour calculer automatiquement les vecteurs d'embedding des tracks musicaux après leur intégration en base de données.

## 🏗️ Architecture

### Services impliqués

```
┌─────────────────┐    ┌─────────────┐    ┌─────────────────┐
│   Library API   │───▶│    Redis    │───▶│ Vector Listener  │
│   (FastAPI)     │    │   PubSub    │    │   (Python)      │
└─────────────────┘    └─────────────┘    └─────────────────┘
         │                        │                    │
         │                        │                    │
         ▼                        ▼                    ▼
┌─────────────────┐    ┌─────────────┐    ┌─────────────────┐
│  Track créée/   │    │ Celery Task │    │ Recommender API │
│  mise à jour    │    │ (calculate_ │    │ (SQLite-vec)    │
└─────────────────┘    │   vector)   │    └─────────────────┘
                       └─────────────┘
```

### Flux de données

1. **Création/Mise à jour de track** dans Library API
2. **Publication d'événement** Redis sur canal `vectorization`
3. **Vectorization Listener** écoute et déclenche tâche Celery
4. **Calcul du vecteur** via sentence-transformers + features audio
5. **Stockage** dans Recommender API (SQLite avec extension vec)

## 🔧 Configuration

### Variables d'environnement

```bash
# Redis
REDIS_URL=redis://redis:6379/0

# APIs
LIBRARY_API_URL=http://library:8001
RECOMMENDER_API_URL=http://recommender:8002

# Vectorisation
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DIMENSION=396  # 384 text + 12 numeric
```

### Docker Compose

```yaml
services:
  vectorization_listener:
    build: ./backend_worker
    depends_on:
      - redis
      - library_service
      - recommender_service
    command: ["python3", "/app/scripts/vectorization_listener.py"]

  worker:
    command: [
      "celery", "-A", "backend_worker.celery_app", "worker",
      "-Q", "scan,extract,metadata,batch,insert,vectorization,deferred",
      "--autoscale=4,1",  # Optimisé Raspberry Pi
      "--time-limit=3600"
    ]
```

## 📡 Événements Redis

### Canal: `vectorization`

#### track_created
```json
{
  "type": "track_created",
  "track_id": 123,
  "metadata": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "genre": "Rock",
    "bpm": 120,
    "key": "C",
    "duration": 180
  },
  "timestamp": 1640995200.0
}
```

#### track_updated
```json
{
  "type": "track_updated",
  "track_id": 123,
  "metadata": { ... },
  "timestamp": 1640995200.0
}
```

## 🚀 Tâches Celery

### calculate_vector
- **Queue**: `vectorization`
- **Fonction**: Calcule et stocke le vecteur d'une track
- **Retry**: Automatique avec backoff exponentiel
- **Timeout**: 60 minutes (Raspberry Pi friendly)

### calculate_vector_if_needed
- **Queue**: `vectorization`
- **Fonction**: Vérifie si le vecteur existe avant calcul
- **Priorité**: Plus basse que `calculate_vector`

## 🗄️ Stockage des vecteurs

### Base de données
- **SQLite** avec extension **sqlite-vec**
- **Table**: `track_vectors` (embedding, metadata)
- **Table virtuelle**: `track_vectors_virtual` (recherche vectorielle)

### Endpoints Recommender API

```bash
# Créer un vecteur
POST /api/track-vectors/
{
  "track_id": 123,
  "embedding": [0.1, 0.2, 0.3, ...]
}

# Récupérer un vecteur
GET /api/track-vectors/{track_id}

# Recherche de similarité
POST /api/track-vectors/search
{
  "embedding": [0.1, 0.2, 0.3, ...],
  "limit": 10
}
```

## 🔍 Recherche de similarité

### Algorithme
1. **Embedding de requête** : sentence-transformers + features numériques
2. **Recherche vectorielle** : cosine similarity via sqlite-vec
3. **Filtres** : genre, année, exclusion même artiste
4. **Résultats** : tracks similaires avec score de distance

### Exemple de requête
```python
# Recherche tracks similaires
similar_tracks = search_similar_tracks(
    query_track_id=123,
    limit=10,
    filters={
        "genre": "rock",
        "exclude_same_artist": True,
        "year_range": {"min": 2000, "max": 2020}
    }
)
```

## 🧪 Tests

### Tests unitaires
```bash
# Tests d'intégration vectorisation
pytest tests/worker/test_vectorization_integration.py -v

# Tests Redis PubSub
pytest tests/worker/test_redis_utils.py -v

# Tests Celery tasks
pytest tests/worker/test_worker_metadata.py::test_calculate_vector -v
```

### Tests d'intégration
```bash
# Test flux complet
pytest tests/test_vectorization_flow.py -v

# Test performance Raspberry Pi
pytest tests/benchmark/test_vectorization_performance.py -v
```

## 📈 Optimisations Raspberry Pi

### Ressources limitées
- **Workers**: 2 max (4 cœurs Raspberry Pi)
- **Timeouts**: 60s par fichier, 120s insertion
- **Batches**: 25 fichiers extraction, 100 artistes/albums
- **Connexions**: 10 Redis, 20 HTTP max

### Vectorisation CPU-friendly
- **Modèle**: all-MiniLM-L6-v2 (léger, 384 dimensions)
- **Threading**: Limité pour éviter surcharge CPU
- **Cache**: Redis pour éviter recalculs

## 🔧 Déploiement

### Démarrage des services
```bash
# 1. Démarrer l'infrastructure
docker-compose up -d redis library_service recommender_service

# 2. Démarrer les workers
docker-compose up -d worker vectorization_listener

# 3. Vérifier les logs
docker-compose logs vectorization_listener
docker-compose logs worker | grep vectorization
```

### Monitoring
```bash
# État Redis
redis-cli INFO

# Tâches Celery actives
celery -A backend_worker.celery_app inspect active

# Logs vectorisation
docker-compose logs vectorization_listener
```

## 🚨 Dépannage

### Problèmes courants

#### Vectorisation ne se déclenche pas
```bash
# Vérifier connexion Redis
docker-compose exec redis redis-cli PING

# Vérifier logs listener
docker-compose logs vectorization_listener

# Vérifier queue Celery
celery -A backend_worker.celery_app inspect registered
```

#### Erreurs de calcul de vecteurs
```bash
# Vérifier modèle sentence-transformers
python -c "from sentence_transformers import SentenceTransformer; print('OK')"

# Vérifier sqlite-vec
docker-compose exec recommender_service python -c "import sqlite_vec; print('OK')"
```

#### Performance lente
```bash
# Réduire batch size
# Augmenter timeouts si nécessaire
# Vérifier usage CPU/mémoire Raspberry Pi
```

## 🔮 Extensions futures

### Améliorations planifiées
- **Vectorisation covers**: Embeddings d'images d'albums
- **Vectorisation harmonique**: Clés musicales et gammes
- **Vectorisation temporelle**: BPM et structure rythmique
- **Recherche multi-modale**: Texte + audio + image

### APIs étendues
- **Recherche par playlist**: Vecteurs de playlists entières
- **Recommandations contextuelles**: Basées sur historique d'écoute
- **Clustering automatique**: Groupement de tracks similaires

## 📚 Références

- [Sentence Transformers](https://www.sbert.net/)
- [SQLite-vec](https://github.com/asg017/sqlite-vec)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis PubSub](https://redis.io/docs/manual/pubsub/)

---

**Auteur**: Kilo Code
**Version**: 1.0.0
**Date**: 2025-01-26