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

## Objectif IA
Quand du code métier est généré, il doit :
- être implémenté dans le bon service
- **jamais** bypasser l’API pour DB
- envoyer la progression via Redis/SSE
