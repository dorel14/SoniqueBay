# Architecture – Contexte Global (Persona)

## Objectif global
SoniqueBay est une application musicale modulaire (library + player + IA) fonctionnant sur Raspberry Pi 4 avec optimisation mémoire/CPU.

## Vue d'ensemble
- Frontend : NiceGUI + SSE & WebSocket pour le temps réel
- Backend principal : FastAPI + GraphQL
- Workers : Celery (scan / audio / vectorisation / enrichissement)
- Base : PostgreSQL + Redis cache
- Cible hardware : Raspberry Pi 4 (optimisations obligatoires)

## Principes d'architecture
- Separation of concerns (UI / API / Workers / DB)
- Tous les traitements lourds → workers Celery
- L'API est la *seule* couche qui touche la DB
- Vectorisation stockée pour éviter recalcul
- SSE préféré au WS pour la progress bar et scan

## Flux internes simplifiés
Frontend → API (GraphQL/REST) → Workers → DB/Redis → SSE vers UI

## Nouvelles Tables (Track Model Evolution)

### TrackAudioFeatures
Table dédiée pour les caractéristiques audio extraites (BPM, tonalité, mood, etc.).

**Champs principaux :**
- `track_id` (FK, UNIQUE) - Référence vers Track
- `bpm` - Tempo en BPM
- `key` - Tonalité musicale
- `camelot_key` - Clé Camelot pour DJ
- `danceability` - Score de dansabilité (0-1)
- `mood_happy`, `mood_aggressive`, `mood_party`, `mood_relaxed` - Scores de mood
- `instrumental`, `acoustic`, `tonal` - Caractéristiques audio
- `analysis_source` - Source d'analyse (librosa, acoustid, tags)
- `analyzed_at` - Date de l'analyse

### TrackEmbeddings
Table dédiée pour les embeddings vectoriels (512 dimensions).

**Champs principaux :**
- `track_id` (FK) - Référence vers Track
- `embedding_type` - Type (semantic, audio, text)
- `vector` - Vecteur pgvector (512 dimensions)
- `embedding_source` - Source (ollama, etc.)
- `embedding_model` - Modèle utilisé

### TrackMetadata
Table dédiée pour les métadonnées enrichies extensibles (clé-valeur).

**Champs principaux :**
- `track_id` (FK) - Référence vers Track
- `metadata_key` - Clé de métadonnée
- `metadata_value` - Valeur
- `metadata_source` - Source (lastfm, listenbrainz, etc.)

## Diagramme de Relations

```
Track
├── TrackAudioFeatures (1:1) - Caractéristiques audio
├── TrackEmbeddings (1:N)   - Vecteurs d'embeddings
└── TrackMetadata (1:N)     - Métadonnées extensibles
```

## Enjeux
- Cohérence entre services
- Performance RPi4
- Maintenabilité modulaire
- Support futur d'intégration Napster/Soulseek
- Recommandations basées sur BPM/tonalité/embeddings
