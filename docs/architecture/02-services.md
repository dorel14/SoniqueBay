# Rôle des Services (Persona)

## Frontend (NiceGUI)
- Affichage bibliothèque
- Navigation Artist/Album/Track
- File de lecture temps réel via WS
- Barre de progression via SSE
- Animations & transitions fluides

## API FastAPI + GraphQL
- Interface unique vers DB
- CRUD artistes/albums/tracks
- Mutations batch (scan)
- SSE pour progression
- WebSocket compatibilité

## Workers Celery
### Scan Worker
- Découverte fichiers audio
- Extraction metadata
- Communication batch GraphQL
### Audio Analysis Worker
- BPM, key, tonalité
- Features manquantes
### Vectorization Worker
- Génération embeddings
- Stockage track_vectors
### Enrichment Worker
- Last.fm / ListenBrainz / Napster enrichissement

## Data Layer
- DB = PostgreSQL
- Redis = cache + pub/sub SSE
- Access DB uniquement via API

## Services - Track Modèle Évolué

Les services suivants gèrent les données des pistes musicales avec une architecture dédiée :

### TrackAudioFeaturesService

**Rôle** : Gestion des caractéristiques audio des pistes (BPM, tonalité, mood, etc.)

**Fichier** : [`backend/api/services/track_audio_features_service.py`](backend/api/services/track_audio_features_service.py)

**Méthodes principales** :

| Méthode | Description |
|---------|-------------|
| `get_by_track_id(track_id)` | Récupère les caractéristiques audio d'une piste |
| `create(...)` | Crée de nouvelles caractéristiques audio |
| `create_or_update(...)` | Crée ou met à jour les caractéristiques |
| `update(...)` | Met à jour les caractéristiques existantes |
| `delete(track_id)` | Supprime les caractéristiques audio |
| `search_by_bpm_range(min_bpm, max_bpm)` | Recherche par plage BPM |
| `search_by_key(key, scale)` | Recherche par tonalité |
| `search_by_camelot_key(camelot_key)` | Recherche par clé Camelot |
| `search_by_mood(...)` | Recherche par critères de mood |
| `get_similar_by_bpm_and_key(track_id, ...)` | Trouve des pistes similaires |
| `get_analysis_statistics()` | Statistiques d'analyse audio |
| `get_tracks_without_features(limit)` | Pistes sans analyse |

### TrackEmbeddingsService

**Rôle** : Gestion des embeddings vectoriels pour les recommandations sémantiques

**Fichier** : [`backend/api/services/track_embeddings_service.py`](backend/api/services/track_embeddings_service.py)

**Méthodes principales** :

| Méthode | Description |
|---------|-------------|
| `get_by_track_id(track_id, embedding_type)` | Récupère les embeddings d'une piste |
| `create(track_id, vector, ...)` | Crée un nouvel embedding |
| `create_or_update(...)` | Crée ou met à jour un embedding |
| `delete(track_id, embedding_type)` | Supprime les embeddings |
| `find_similar(query_vector, ...)` | Recherche par similarité vectorielle |
| `find_similar_by_track_id(track_id, ...)` | Trouve des pistes similaires |
| `find_similar_batch(query_vectors, ...)` | Recherche batch |
| `find_tracks_in_vector_range(...)` | Recherche par sphère vectorielle |
| `get_average_vector(track_ids, ...)` | Calcule le vecteur moyen |
| `get_models_statistics()` | Statistiques des embeddings |
| `get_tracks_without_embeddings(limit)` | Pistes sans embeddings |

### TrackMetadataService

**Rôle** : Gestion des métadonnées enrichies extensibles (clé-valeur)

**Fichier** : [`backend/api/services/track_metadata_service.py`](backend/api/services/track_metadata_service.py)

**Méthodes principales** :

| Méthode | Description |
|---------|-------------|
| `get_by_track_id(track_id, ...)` | Récupère les métadonnées d'une piste |
| `get_single_metadata(track_id, key, ...)` | Récupère une métadonnée spécifique |
| `create(track_id, key, value, ...)` | Crée une métadonnée |
| `create_or_update(...)` | Crée ou met à jour une métadonnée |
| `update(...)` | Met à jour une métadonnée |
| `delete(track_id, key, ...)` | Supprime les métadonnées |
| `search_by_key(key, ...)` | Recherche par clé |
| `search_by_key_prefix(prefix, ...)` | Recherche par préfixe de clé |
| `search_by_value(value, ...)` | Recherche par valeur |
| `search_by_source(source, ...)` | Recherche par source |
| `batch_create(track_id, metadata_dict, ...)` | Création batch |
| `get_metadata_as_dict(track_id)` | Retourne un dictionnaire |
| `get_metadata_statistics()` | Statistiques des métadonnées |
| `get_tracks_without_metadata(limit)` | Pistes sans métadonnées |

## Services Existants

### TrackService
- CRUD de base pour les pistes
- Gestion des relations Artist/Album

### AlbumService
- Gestion des albums
- Couverture automatique

### ArtistService
- Gestion des artistes
- Embeddings d'artistes

### GenreService
- Gestion des genres
- Relations many-to-many

### CoverService
- Extraction de couvertures
- Stockage et caching

### SearchService
- Recherche full-text PostgreSQL
- Recherche hybride SQL + vectorielle

### VectorSearchService
- Recherche par similarité vectorielle
- Gestion des index HNSW

### OllamaService
- Intégration Ollama pour embeddings
- Modèles LLM locaux

### EnrichmentService
- Enrichissement Last.fm
- Enrichissement ListenBrainz

### AudioFeaturesService (Worker)
- Analyse audio avec Librosa
- Extraction BPM, tonalité

### VectorizationService (Worker)
- Vectorisation des pistes
- Stockage embeddings

## Objectif IA
Quand du code métier est généré, il doit :
- être implémenté dans le bon service
- **jamais** bypasser l'API pour DB
- envoyer la progression via Redis/SSE
