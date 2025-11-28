# Architecture de SoniqueBay - Version Optimisée

## Vue d'ensemble

SoniqueBay est une application de gestion de bibliothèque musicale avec une architecture moderne utilisant FastAPI, GraphQL, Celery et PostgreSQL/SQLite.

L'ensemble de cette applcation doit fonctionner sans problème sur un raspberry pi 4 ,  il faut donc optimiser le code pour gérer au mieux les ressources

## Architecture générale

```mermaid
graph TB
    subgraph "Frontend"
        UI[NiceGUI Interface]
    end

    subgraph "API Layer"
        FA[FastAPI Server]
        GQL[GraphQL API]
        REST[REST API]
    end

    subgraph "Worker Layer"
        CEL[Celery Workers]
        SCAN[Scan Service]
        AUDIO[Audio Analysis]
        VECT[Vectorization]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        FS[(File System)]
    end

    UI --> FA
    FA --> GQL
    FA --> REST
    FA --> CEL
    CEL --> SCAN
    CEL --> AUDIO
    CEL --> VECT
    SCAN --> PG
    AUDIO --> PG
    VECT --> PG
    FA --> PG
    FA --> REDIS
    CEL --> REDIS
```

## Composants principaux

### 1. API FastAPI

- **Endpoints REST** : Gestion CRUD des entités
- **GraphQL API** : Requêtes complexes et mutations batch
- **Server-Sent Events (SSE)** : Streaming de progression en temps réel
- **WebSocket** : Communications temps réel (conservé pour compatibilité)
- **Middleware** : CORS, logging, health checks

### 2. Workers Celery

- **Scan Worker** : Indexation des fichiers musicaux
- **Audio Analysis Worker** : Extraction des caractéristiques audio
- **Vectorization Worker** : Génération des embeddings
- **Enrichment Worker** : Enrichissement des métadonnées

### 3. Services métier

- **TrackService** : Gestion des pistes
- **ArtistService** : Gestion des artistes
- **AlbumService** : Gestion des albums
- **VectorizationService** : Gestion des vecteurs
- **AudioFeaturesService** : Analyse audio

## Optimisations implementées

### 1. Traitement par lots (Batch Processing)

- **GraphQL Mutations** : `create_artists`, `create_albums`, `create_tracks`
- **Chunk Size** : 500 éléments par lot (vs 200 précédemment)
- **Async/Await** : Traitement asynchrone complet

### 2. Index de base de données

```sql
-- Index optimisés pour les scans
CREATE INDEX idx_tracks_path ON tracks(path);
CREATE INDEX idx_tracks_artist_album ON tracks(track_artist_id, album_id);
CREATE INDEX idx_tracks_mb_id ON tracks(musicbrainz_id);
CREATE INDEX idx_tracks_missing_audio ON tracks(bpm, key);
CREATE INDEX idx_track_vectors_track_id ON track_vectors(track_id);
```

### 3. Métriques de performance

- **Temps de scan** : Mesuré par chunk et total
- **Débit** : Fichiers/seconde
- **Utilisation mémoire** : Monitoring des workers
- **Taux d'erreur** : Suivi des échecs

### 4. Gestion d'erreurs améliorée

- **Retry logic** : Mécanisme de reprise automatique
- **Circuit breaker** : Protection contre les pannes
- **Logging structuré** : Traces détaillées pour debugging

## Nouveaux endpoints

### API Track Vectors

```
POST   /api/track-vectors/          # Créer un vecteur
GET    /api/track-vectors/{id}      # Récupérer un vecteur
PUT    /api/track-vectors/{id}      # Mettre à jour un vecteur
DELETE /api/track-vectors/{id}      # Supprimer un vecteur
GET    /api/track-vectors/          # Lister les vecteurs
```

### API Audio Analysis

```
POST   /api/tracks/analyze-audio           # Lancer l'analyse audio
PUT    /api/tracks/{id}/features          # Mettre à jour les features
```

### GraphQL Mutations optimisées

```graphql
mutation CreateArtists($artists: [ArtistCreateInput!]!) {
    create_artists(data: $artists) {
        id
        name
        musicbrainz_artistid
    }
}

mutation CreateTracks($tracks: [TrackCreateInput!]!) {
    create_tracks(data: $tracks) {
        id
        title
        path
        bpm
        key
    }
}
```

## Workflows optimisés

### 1. Scan de bibliothèque

```mermaid
graph TD
    A[Déclenchement scan] --> B[Comptage fichiers]
    B --> C[Traitement par chunks de 500]
    C --> D[Mutations GraphQL batch]
    D --> E[Analyse audio parallèle]
    E --> F[Vectorisation]
    F --> G[Indexation Whoosh]
    G --> H[Métriques finales]
```

### 2. Analyse audio

```mermaid
graph TD
    A[Track sans features] --> B[Librosa analysis]
    B --> C[Extraction features]
    C --> D[Mise à jour DB]
    D --> E[Retry si échec]
    E --> F[Logging métriques]
```

### 3. Vectorisation

```mermaid
graph TD
    A[Track metadata] --> B[Génération embedding]
    B --> C[Stockage TrackVector]
    C --> D[Cache Redis]
    D --> E[Recherche sémantique]
```

## Streaming en Temps Réel (SSE)

### Architecture SSE

```mermaid
graph TD
    A[Frontend UI] --> B[register_sse_handler]
    B --> C[SSE Client]
    C --> D[HTTP GET /api/events]
    D --> E[Backend SSE Endpoint]
    E --> F[Redis PubSub]
    F --> G[Workers Celery]
    G --> H[publish_event progress]
    H --> F
    F --> E
    E --> D
    D --> C
    C --> B
    B --> A
```

### Composants SSE

#### 1. Backend SSE Endpoint

- **URL** : `/api/events`
- **Méthode** : GET
- **Format** : Server-Sent Events standard
- **Canaux Redis** : "progress", "notifications"

#### 2. Workers avec Progression

- **Fonction** : `publish_event("progress", data, channel="progress")`
- **Format** : JSON avec `type: "progress"`, `task_id`, `step`, `percent`
- **Fréquence** : Mise à jour toutes les 100 opérations

#### 3. Client SSE Frontend

- **Connexion** : HTTP persistante vers `/api/events`
- **Handlers** : `register_sse_handler(handler_function)`
- **Reconnexion** : Automatique en cas de déconnexion

### Avantages SSE vs WebSocket

| Critère | SSE | WebSocket |
|---------|-----|-----------|
| **Complexité** | Simple (HTTP) | Complexe (protocole binaire) |
| **Performance** | Excellent | Bon |
| **Reconnexion** | Automatique | Manuel |
| **Proxy/CDN** | Compatible | Problématique |
| **Implémentation** | Standard | Spécialisé |

## Configuration

### Variables d'environnement

```bash
# API
API_URL=http://backend:8001
GRAPHQL_URL=http://backend:8001/api/graphql
SSE_URL=http://backend:8001/api/events

# Worker
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Vectorisation
EMBEDDING_MODEL=mock-v1
EMBEDDING_DIMENSION=384

# Scan
CHUNK_SIZE=500
SCAN_TIMEOUT=300
```

### Indexes recommandés

```sql
-- Performance scan
CREATE INDEX CONCURRENTLY idx_tracks_scan_perf ON tracks(date_added, path);

-- Recherches fréquentes
CREATE INDEX CONCURRENTLY idx_tracks_search ON tracks(title, artist_name, album_title);

-- Vectorisation
CREATE INDEX CONCURRENTLY idx_track_vectors_search ON track_vectors USING ivfflat (vector_data vector_cosine_ops);
```

## Monitoring et observabilité

### Métriques collectées

- `scan_duration_seconds` : Durée totale du scan
- `scan_files_processed_total` : Nombre de fichiers traités
- `scan_chunks_processed_total` : Nombre de chunks traités
- `audio_analysis_duration_seconds` : Durée d'analyse audio
- `vectorization_duration_seconds` : Durée de vectorisation
- `api_request_duration_seconds` : Latence des API

### Événements Server-Sent Events (SSE)

```json
{
  "type": "progress",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "step": "Extraction en cours",
  "current": 150,
  "total": 1000,
  "percent": 15,
  "metrics": {
    "avg_chunk_time": 2.3,
    "files_per_second": 217.8
  }
}
```

### Nouveaux endpoints SSE

```
GET    /api/events              # Streaming SSE de progression
```

### Configuration SSE

```bash
# Variables d'environnement
SSE_URL=http://library:8001/api/events
WS_URL=ws://library:8001/api/ws  # Conservé pour compatibilité

# Redis channels
progress                        # Canal pour les messages de progression
notifications                   # Canal pour les notifications générales
```

## Tests et validation

### Tests d'intégration

- **test_graphql_batch_operations** : Validation GraphQL batch
- **test_vectorization_workflow** : Workflow complet vectorisation
- **test_scan_performance_metrics** : Métriques de performance
- **test_chunk_size_optimization** : Optimisation chunks

### Benchmarks cibles

- **Scan performance** : 500+ fichiers/minute
- **Audio analysis** : 50+ fichiers/minute
- **Vectorization** : 100+ fichiers/minute
- **Memory usage** : < 2GB pour 1000 fichiers
- **Error rate** : < 5%

## Évolutivité

### Scaling horizontal

- **Workers Celery** : Ajout de workers pour + de parallélisation
- **Database** : PostgreSQL avec pgvector pour scaling
- **Cache** : Redis cluster pour haute disponibilité

### Optimisations futures

- **GPU acceleration** : Pour l'analyse audio intensive
- **Distributed processing** : Apache Spark pour gros volumes
- **Real-time indexing** : Elasticsearch pour recherche instantanée

---

*Document mis à jour le 20 septembre 2025 - Optimisations d'intégration DB et scan*
