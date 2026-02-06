## 1. Architecture

- **Framework** : FastAPI
- **Base de données** : PostgreSQL pour stockage robuste
- **Communication temps réel** : WebSocket avec le frontend
- **Tâches asynchrones** : `asyncio` ou Celery pour indexation et vectorisation

## 2. Endpoints principaux

### Tracks API

| Endpoint | Méthode | Description |
|----------|----------|-------------|
| `/tracks` | GET | Retourne la liste des pistes filtrables |
| `/tracks/{id}` | GET | Retourne une piste par ID |
| `/tracks` | POST | Crée une nouvelle piste |
| `/tracks/{id}` | PUT | Met à jour une piste |
| `/tracks/{id}` | DELETE | Supprime une piste |

### Track Audio Features API

| Endpoint | Méthode | Description |
|----------|----------|-------------|
| `/tracks/{track_id}/audio-features` | GET | Récupère les caractéristiques audio d'une piste |
| `/tracks/{track_id}/audio-features` | POST | Crée les caractéristiques audio |
| `/tracks/{track_id}/audio-features` | PUT | Met à jour les caractéristiques audio |
| `/tracks/{track_id}/audio-features` | DELETE | Supprime les caractéristiques audio |
| `/audio-features/search` | GET | Recherche par BPM, key, camelot_key, mood |
| `/audio-features/statistics` | GET | Statistiques d'analyse audio |
| `/tracks/{track_id}/similar-by-features` | GET | Trouve des pistes similaires |

### Track Embeddings API

| Endpoint | Méthode | Description |
|----------|----------|-------------|
| `/tracks/{track_id}/embeddings` | GET | Récupère tous les embeddings d'une piste |
| `/tracks/{track_id}/embeddings/{type}` | GET | Récupère un embedding spécifique |
| `/tracks/{track_id}/embeddings` | POST | Crée un embedding |
| `/tracks/{track_id}/embeddings/{type}` | PUT | Met à jour un embedding |
| `/tracks/{track_id}/embeddings/{type}` | DELETE | Supprime un embedding |
| `/embeddings/search` | POST | Recherche vectorielle par similarité |
| `/tracks/{track_id}/embeddings/search-similar` | POST | Trouve des pistes similaires |
| `/embeddings/statistics` | GET | Statistiques des embeddings |
| `/tracks/without-embeddings` | GET | Pistes sans embeddings |

### Track Metadata API

| Endpoint | Méthode | Description |
|----------|----------|-------------|
| `/tracks/{track_id}/metadata` | GET | Récupère toutes les métadonnées d'une piste |
| `/tracks/{track_id}/metadata/{key}` | GET | Récupère une métadonnée spécifique |
| `/tracks/{track_id}/metadata` | POST | Crée une métadonnée |
| `/tracks/{track_id}/metadata/{key}` | PUT | Met à jour une métadonnée |
| `/tracks/{track_id}/metadata/{key}` | DELETE | Supprime une métadonnée |
| `/metadata/search` | GET | Recherche par source, clé ou valeur |
| `/tracks/{track_id}/metadata-by-source` | GET | Métadonnées regroupées par source |
| `/tracks/{track_id}/metadata-batch` | POST | Création batch de métadonnées |
| `/tracks/{track_id}/metadata-stats` | GET | Statistiques des métadonnées |
| `/metadata/statistics` | GET | Statistiques globales |
| `/tracks/without-metadata` | GET | Pistes sans métadonnées |

### Autres Endpoints

| Endpoint | Méthode | Description |
|----------|----------|-------------|
| `/artists` | GET | Retourne la liste des artistes |
| `/albums` | GET | Retourne la liste des albums filtrables par artiste |
| `/playqueue` | GET/POST/DELETE | Gestion de la file de lecture |
| `/recommendations` | GET | Suggestions basées sur vecteurs et tags |
| `/search` | GET | Recherche hybride SQL + vectorielle |
| `/ws` | WS | WebSocket pour mises à jour temps réel |
| `/scan` | POST | Lancer un scan de bibliothèque |
| `/settings` | GET/PUT | Gestion des paramètres |

## 3. Gestion asynchrone

- Indexation musicale : lecture des métadonnées et génération des vecteurs.
- Téléchargements/synchronisation : Last.fm, ListenBrainz, Napster.
- Monitoring système : CPU, RAM, stockage pour ajuster la charge.

## 4. Sécurité

- API locale avec authentification par token.
- Limiter l'accès externe pour éviter les failles.

## 5. Bonnes pratiques

1. Pagination et lazy loading pour les réponses volumineuses.
2. Optimiser les requêtes SQL avec indexes.
3. Tester tous les endpoints sur Raspberry Pi avant déploiement.

## 6. Documentation API

La documentation Swagger est disponible à l'adresse : `/api/docs`

La documentation ReDoc est disponible à l'adresse : `/api/redoc`

## 7. GraphQL

L'endpoint GraphQL est disponible à l'adresse : `/graphql`

### Types principaux

- **TrackType** : Type principal pour les pistes (avec relations audio_features, embeddings, metadata)
- **TrackAudioFeaturesType** : Caractéristiques audio
- **TrackEmbeddingsType** : Embeddings vectoriels
- **TrackMetadataType** : Métadonnées enrichies

### Queries principales

```graphql
query {
  track(id: Int!): TrackType
  tracks(skip: Int, limit: Int, where: TrackFilter): [TrackType!]!
  audioFeatures(trackId: Int!): TrackAudioFeaturesType
  embeddings(trackId: Int!, type: String): [TrackEmbeddingsType!]!
  metadata(trackId: Int!): [TrackMetadataType!]!
}
```

### Mutations principales

```graphql
mutation {
  createTrack(input: TrackCreateInput!): TrackType!
  updateTrack(id: Int!, input: TrackUpdateInput!): TrackType!
  createAudioFeatures(input: TrackAudioFeaturesCreateInput!): TrackAudioFeaturesType!
  createEmbedding(input: TrackEmbeddingsCreateInput!): TrackEmbeddingsType!
  createMetadata(input: TrackMetadataCreateInput!): TrackMetadataType!
}
```
