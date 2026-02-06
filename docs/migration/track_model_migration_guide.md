# Guide de Migration du Modèle Track - SoniqueBay

## Vue d'ensemble

Ce guide documente l'évolution du modèle `Track` de SoniqueBay et explique comment migrer vers la nouvelle architecture avec les tables dédiées pour les caractéristiques audio, les embeddings et les métadonnées enrichies.

## Contexte

Le modèle `Track` original contenait de nombreuses responsabilités mélangées :
- Métadonnées de base (titre, chemin, durée, etc.)
- Caractéristiques audio (BPM, tonalité, mood, etc.)
- Vecteurs d'embedding
- Métadonnées externes redondantes

Cette architecture posait des problèmes de :
- **Maintenance** : Difficulté à modifier une catégorie sans impacter les autres
- **Extensibilité** : Ajout de nouvelles caractéristiques audio complexe
- **Performance** : Requêtes lourdes pour accéder à des données spécifiques

## Nouvelle Architecture

### Tables Créées

```
Track
├── TrackAudioFeatures (1:1) - Caractéristiques audio
├── TrackEmbeddings (1:N)    - Vecteurs d'embeddings
└── TrackMetadata (1:N)      - Métadonnées extensibles
```

### Structure des Nouvelles Tables

#### TrackAudioFeatures

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers Track (UNIQUE) |
| `bpm` | Float | Tempo en BPM |
| `key` | String | Tonalité (C, C#, D, etc.) |
| `scale` | String | Mode (major/minor) |
| `danceability` | Float | Score de dansabilité (0-1) |
| `mood_happy` | Float | Score mood happy (0-1) |
| `mood_aggressive` | Float | Score mood aggressive (0-1) |
| `mood_party` | Float | Score mood party (0-1) |
| `mood_relaxed` | Float | Score mood relaxed (0-1) |
| `instrumental` | Float | Score instrumental (0-1) |
| `acoustic` | Float | Score acoustic (0-1) |
| `tonal` | Float | Score tonal (0-1) |
| `genre_main` | String | Genre principal détecté |
| `camelot_key` | String | Clé Camelot pour DJ |
| `analysis_source` | String | Source d'analyse (librosa, acoustid, tags) |
| `analyzed_at` | DateTime | Date de l'analyse |

#### TrackEmbeddings

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers Track |
| `embedding_type` | String | Type d'embedding (semantic, audio, text, etc.) |
| `vector` | Vector(512) | Vecteur d'embedding |
| `embedding_source` | String | Source de vectorisation |
| `embedding_model` | String | Modèle utilisé |
| `created_at` | DateTime | Date de création |

#### TrackMetadata

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers Track |
| `metadata_key` | String | Clé de métadonnée |
| `metadata_value` | String | Valeur de métadonnée |
| `metadata_source` | String | Source (lastfm, listenbrainz, etc.) |
| `created_at` | DateTime | Date de création |

---

## Utilisation des Nouvelles API REST

### Caractéristiques Audio (TrackAudioFeatures)

#### Récupérer les caractéristiques audio d'une piste

```bash
GET /api/tracks/{track_id}/audio-features
```

**Réponse :**
```json
{
  "id": 1,
  "track_id": 123,
  "bpm": 128.5,
  "key": "C",
  "scale": "major",
  "danceability": 0.85,
  "mood_happy": 0.72,
  "mood_aggressive": 0.15,
  "mood_party": 0.68,
  "mood_relaxed": 0.25,
  "instrumental": 0.05,
  "acoustic": 0.12,
  "tonal": 0.88,
  "genre_main": "Electronic",
  "camelot_key": "8B",
  "analysis_source": "librosa",
  "analyzed_at": "2024-01-15T10:30:00Z"
}
```

#### Créer des caractéristiques audio

```bash
POST /api/tracks/{track_id}/audio-features
Content-Type: application/json

{
  "track_id": 123,
  "bpm": 128.5,
  "key": "C",
  "scale": "major",
  "danceability": 0.85,
  "mood_happy": 0.72,
  "analysis_source": "librosa"
}
```

#### Rechercher par BPM

```bash
GET /api/audio-features/search?min_bpm=120&max_bpm=140
```

#### Rechercher par clé Camelot

```bash
GET /api/audio-features/search?camelot_key=8B
```

#### Trouver des pistes similaires par caractéristiques audio

```bash
GET /api/tracks/{track_id}/similar-by-features?bpm_tolerance=5&limit=20
```

---

### Embeddings Vectoriels (TrackEmbeddings)

#### Récupérer les embeddings d'une piste

```bash
GET /api/tracks/{track_id}/embeddings
GET /api/tracks/{track_id}/embeddings?embedding_type=semantic
```

#### Créer un embedding

```bash
POST /api/tracks/{track_id}/embeddings
Content-Type: application/json

{
  "track_id": 123,
  "vector": [0.1, 0.2, 0.3, ...],  // 512 dimensions
  "embedding_type": "semantic",
  "embedding_source": "ollama",
  "embedding_model": "nomic-embed-text"
}
```

#### Recherche vectorielle par similarité

```bash
POST /api/embeddings/search
Content-Type: application/json

{
  "query_vector": [0.1, 0.2, 0.3, ...],  // 512 dimensions
  "embedding_type": "semantic",
  "limit": 10,
  "min_similarity": 0.8
}
```

#### Trouver des pistes similaires

```bash
POST /api/tracks/{track_id}/embeddings/search-similar
Content-Type: application/json

{
  "embedding_type": "semantic",
  "limit": 10,
  "exclude_self": true
}
```

---

### Métadonnées Enrichies (TrackMetadata)

#### Récupérer toutes les métadonnées d'une piste

```bash
GET /api/tracks/{track_id}/metadata
```

#### Récupérer une métadonnée spécifique

```bash
GET /api/tracks/{track_id}/metadata/{key}
GET /api/tracks/{track_id}/metadata/lyrics?metadata_source=lastfm
```

#### Créer une métadonnée

```bash
POST /api/tracks/{track_id}/metadata
Content-Type: application/json

{
  "track_id": 123,
  "metadata_key": "lyrics",
  "metadata_value": "Paroles de la chanson...",
  "metadata_source": "lastfm"
}
```

#### Créer plusieurs métadonnées en batch

```bash
POST /api/tracks/{track_id}/metadata-batch
Content-Type: application/json

{
  "metadata_dict": {
    "album_rating": "4.5",
    "playcount": "125000",
    "listeners": "52000"
  },
  "metadata_source": "lastfm",
  "replace_existing": false
}
```

#### Rechercher des métadonnées

```bash
GET /api/metadata/search?source=lastfm
GET /api/metadata/search?key=lyrics
GET /api/metadata/search?value=rock
```

---

## Utilisation via GraphQL

Les nouveaux types GraphQL sont disponibles avec **rétrocompatibilité** complète.

### Types GraphQL Créés

```graphql
# Nouveaux types dédiés
type TrackAudioFeatures {
  id: Int!
  trackId: Int!
  bpm: Float
  key: String
  scale: String
  danceability: Float
  moodHappy: Float
  moodAggressive: Float
  moodParty: Float
  moodRelaxed: Float
  instrumental: Float
  acoustic: Float
  tonal: Float
  genreMain: String
  camelotKey: String
  analysisSource: String
  analyzedAt: DateTime
}

type TrackEmbeddings {
  id: Int!
  trackId: Int!
  embeddingType: String!
  vector: [Float!]!
  embeddingSource: String
  embeddingModel: String
  createdAt: DateTime!
}

type TrackMetadata {
  id: Int!
  trackId: Int!
  metadataKey: String!
  metadataValue: String
  metadataSource: String
  createdAt: DateTime!
}
```

### Rétrocompatibilité avec TrackType

Le type `Track` conserve tous les champs audio existants comme **propriétés calculées** :

```graphql
type Track {
  # Champs de base Track (inchangés)
  id: Int!
  title: String!
  path: String!
  # ... autres champs de base

  # NOUVELLES RELATIONS
  audioFeatures: TrackAudioFeatures
  embeddings: [TrackEmbeddings!]!
  metadata: [TrackMetadata!]!

  # CHAMPS AUDIO MAINTENUS POUR RÉTROCOMPATIBILITÉ
  # (ces champs lisent maintenant depuis TrackAudioFeatures)
  bpm: Float
  key: String
  scale: String
  danceability: Float
  moodHappy: Float
  moodAggressive: Float
  moodParty: Float
  moodRelaxed: Float
  instrumental: Float
  acoustic: Float
  tonal: Float
  camelotKey: String
  genreMain: String
}
```

### Exemple de Requête GraphQL

```graphql
query GetTrackWithAllData($trackId: Int!) {
  track(id: $trackId) {
    id
    title
    path
    
    # Nouvelles relations
    audioFeatures {
      bpm
      key
      camelotKey
      analysisSource
    }
    embeddings(embeddingType: "semantic") {
      id
      embeddingType
    }
    metadata(source: "lastfm") {
      metadataKey
      metadataValue
    }
    
    # Champs rétrocompatibles (depuis audioFeatures)
    bpm
    key
  }
}
```

---

## Avantages de la Nouvelle Architecture

### 1. Séparation des Responsabilités

- **Track** : Métadonnées de base uniquement
- **TrackAudioFeatures** : Caractéristiques audio dédiées
- **TrackEmbeddings** : Gestion flexible des vecteurs
- **TrackMetadata** : Extensibilité sans modification du schéma

### 2. Extensibilité

- Ajout facile de nouvelles caractéristiques audio
- Support de plusieurs types d'embeddings
- Métadonnées extensibles via clé/valeur

### 3. Performance

- Index optimisés pour chaque table
- Requêtes plus ciblées
- Cache Redis par table

### 4. Traçabilité

- Source d'analyse audio documentée
- Source de vectorisation trackée
- Dates d'analyse et de création

---

## Migration depuis l'Ancien Schema

### Pour les Développeurs

Les données existantes ont été migrées automatiquement via Alembic :
1. Les champs audio ont été copiés vers `TrackAudioFeatures`
2. Les vecteurs ont été copiés vers `TrackEmbeddings`
3. Les métadonnées enrichies ont été créées dans `TrackMetadata`

### Pour les Utilisateurs de l'API

**AUCUNE ACTION REQUISE** - L'API REST et GraphQL sont pleinement rétrocompatibles :
- Les requêtes existantes continuent de fonctionner
- Les nouveaux endpoints sont disponibles pour des fonctionnalités avancées
- Les champs audio dans `Track` sont automatiquement remplis depuis `TrackAudioFeatures`

---

## Fichiers Sources

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Modèle | [`backend/api/models/track_audio_features_model.py`](backend/api/models/track_audio_features_model.py) | Modèle SQLAlchemy TrackAudioFeatures |
| Modèle | [`backend/api/models/track_embeddings_model.py`](backend/api/models/track_embeddings_model.py) | Modèle SQLAlchemy TrackEmbeddings |
| Modèle | [`backend/api/models/track_metadata_model.py`](backend/api/models/track_metadata_model.py) | Modèle SQLAlchemy TrackMetadata |
| Service | [`backend/api/services/track_audio_features_service.py`](backend/api/services/track_audio_features_service.py) | Service métier audio features |
| Service | [`backend/api/services/track_embeddings_service.py`](backend/api/services/track_embeddings_service.py) | Service métier embeddings |
| Service | [`backend/api/services/track_metadata_service.py`](backend/api/services/track_metadata_service.py) | Service métier metadata |
| Router API | [`backend/api/routers/track_audio_features_api.py`](backend/api/routers/track_audio_features_api.py) | Endpoints REST audio features |
| Router API | [`backend/api/routers/track_embeddings_api.py`](backend/api/routers/track_embeddings_api.py) | Endpoints REST embeddings |
| Router API | [`backend/api/routers/track_metadata_api.py`](backend/api/routers/track_metadata_api.py) | Endpoints REST metadata |
| GraphQL Types | [`backend/api/graphql/types/track_audio_features_type.py`](backend/api/graphql/types/track_audio_features_type.py) | Types GraphQL audio features |
| GraphQL Types | [`backend/api/graphql/types/track_embeddings_type.py`](backend/api/graphql/types/track_embeddings_type.py) | Types GraphQL embeddings |
| GraphQL Types | [`backend/api/graphql/types/track_metadata_type.py`](backend/api/graphql/types/track_metadata_type.py) | Types GraphQL metadata |
| Migration | [`alembic/versions/create_track_features_embeddings_metadata_tables.py`](alembic/versions/create_track_features_embeddings_metadata_tables.py) | Migration Alembic |

---

## Notes de Version

- **Version** : 2.0.0
- **Date** : Janvier 2024
- **Breaking Changes** : Aucun (rétrocompatibilité complète)
- **Dépendances** : pgvector pour les embeddings PostgreSQL
