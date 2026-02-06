# Plan d'Évolution du Modèle Track - SoniqueBay

## Vue d'ensemble

Ce plan détaille l'évolution du modèle de données `Track` de manière **non destructive**, en améliorant la séparation des responsabilités et en préparant l'architecture pour l'analyse audio avancée, les recommandations intelligentes et la recherche vectorielle & NLP.

## Objectifs

1. **Séparation stricte des responsabilités** - Créer des tables dédiées pour l'analyse audio, les embeddings et les métadonnées enrichies
2. **Optimisation des performances** - Indexation, requêtes optimisées, cache Redis
3. **Préparation pour de nouvelles fonctionnalités IA** - Recommandations avancées, NLP, chat

---

## État Actuel - Analyse

### Problèmes Identifiés

#### 1. Mélange de responsabilités dans Track

Le modèle [`Track`](backend/api/models/tracks_model.py:12) contient actuellement:

| Catégorie | Champs | Problème |
|-----------|--------|----------|
| **Métadonnées fichier** | `path`, `duration`, `track_number`, `disc_number`, `year`, `file_type`, `bitrate`, `file_mtime`, `file_size` | OK - Métadonnées de base |
| **Métadonnées MusicBrainz** | `musicbrainz_id`, `musicbrainz_albumid`, `musicbrainz_artistid`, `musicbrainz_albumartistid`, `musicbrainz_genre`, `acoustid_fingerprint` | OK - Métadonnées externes |
| **Métadonnées de base** | `title`, `album_id`, `track_artist_id`, `featured_artists`, `genre` | OK - Métadonnées de base |
| **Couvertures** | `cover_data`, `cover_mime_type` | **REDONDANT** - Table [`Cover`](backend/api/models/covers_model.py) existe déjà |
| **Recherche** | `vector`, `search` | **MÉLANGÉ** - Devrait être dans une table dédiée |
| **Analyse audio** | `bpm`, `key`, `scale`, `danceability`, `mood_*`, `instrumental`, `acoustic`, `tonal`, `genre_main`, `camelot_key` | **MÉLANGÉ** - Devrait être dans une table dédiée |

#### 2. Redondances

- `cover_data` et `cover_mime_type` dans [`Track`](backend/api/models/tracks_model.py:31-32) vs table [`Cover`](backend/api/models/covers_model.py)
- `genre` (String) vs `genres` (relation many-to-many)
- `musicbrainz_genre` vs `genre_tags` (relation)

#### 3. Pas de séparation pour l'analyse audio

Les champs d'analyse audio sont directement dans [`Track`](backend/api/models/tracks_model.py:44-56):
- Difficile d'ajouter de nouvelles caractéristiques audio sans modifier Track
- Pas de versioning des analyses audio
- Pas de traçabilité de la source d'analyse (Librosa, AcoustID, Tags standards)

#### 4. Pas de table dédiée pour les embeddings

Le vecteur est directement dans [`Track`](backend/api/models/tracks_model.py:40):
- Difficile de gérer plusieurs types d'embeddings (audio, texte, etc.)
- Pas de versioning des embeddings
- Pas de traçabilité de la source de vectorisation (Ollama, etc.)

---

## Architecture Cible

### Diagramme Mermaid

```mermaid
erDiagram
    Track ||--|| TrackAudioFeatures : "1:1"
    Track ||--o{ TrackEmbeddings : "1:N"
    Track ||--o{ TrackMetadata : "1:N"
    Track ||--o{ Cover : "1:N"
    Track }o--|| Artist : "N:1"
    Track }o--o| Album : "N:1"
    Track }o--o{ Genre : "N:N"
    Track }o--o{ GenreTag : "N:N"
    Track }o--o{ MoodTag : "N:N"

    Track {
        int id PK
        string title
        string path UK
        int track_artist_id FK
        int album_id FK
        int duration
        string track_number
        string disc_number
        string year
        string file_type
        int bitrate
        float file_mtime
        int file_size
        string featured_artists
        string musicbrainz_id UK
        string musicbrainz_albumid
        string musicbrainz_artistid
        string musicbrainz_albumartistid
        string acoustid_fingerprint
        datetime date_added
        datetime date_modified
    }

    TrackAudioFeatures {
        int id PK
        int track_id FK UK
        float bpm
        string key
        string scale
        float danceability
        float mood_happy
        float mood_aggressive
        float mood_party
        float mood_relaxed
        float instrumental
        float acoustic
        float tonal
        string genre_main
        string camelot_key
        string analysis_source
        datetime analyzed_at
        datetime date_added
        datetime date_modified
    }

    TrackEmbeddings {
        int id PK
        int track_id FK
        string embedding_type
        vector vector 512
        string embedding_source
        string embedding_model
        datetime created_at
        datetime date_added
        datetime date_modified
    }

    TrackMetadata {
        int id PK
        string metadata_key
        string metadata_value
        string metadata_source
        datetime created_at
        datetime date_added
        datetime date_modified
    }

    Artist {
        int id PK
        string name UK
        string musicbrainz_artistid
        vector vector 512
        string search
    }

    Album {
        int id PK
        string title
        int album_artist_id FK
        string release_year
        string musicbrainz_albumid
    }

    Cover {
        int id PK
        string entity_type
        int entity_id
        string cover_data
        string mime_type
        string url
    }

    Genre {
        int id PK
        string name UK
    }

    GenreTag {
        int id PK
        string name UK
    }

    MoodTag {
        int id PK
        string name UK
    }
```

### Nouvelles Tables

#### 1. TrackAudioFeatures

Table dédiée pour les caractéristiques audio extraites:

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers [`Track.id`](backend/api/models/tracks_model.py:15) (UNIQUE) |
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
| `date_added` | DateTime | Date d'ajout |
| `date_modified` | DateTime | Date de modification |

**Index:**
- `idx_track_audio_features_track_id` sur `track_id` (UNIQUE)
- `idx_track_audio_features_bpm` sur `bpm`
- `idx_track_audio_features_key` sur `key`
- `idx_track_audio_features_camelot_key` sur `camelot_key`

#### 2. TrackEmbeddings

Table dédiée pour les embeddings vectoriels:

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers [`Track.id`](backend/api/models/tracks_model.py:15) |
| `embedding_type` | String | Type d'embedding (semantic, audio, text, etc.) |
| `vector` | Vector(512) | Vecteur d'embedding |
| `embedding_source` | String | Source de vectorisation (ollama, etc.) |
| `embedding_model` | String | Modèle utilisé (nomic-embed-text, etc.) |
| `created_at` | DateTime | Date de création |
| `date_added` | DateTime | Date d'ajout |
| `date_modified` | DateTime | Date de modification |

**Index:**
- `idx_track_embeddings_track_id` sur `track_id`
- `idx_track_embeddings_type` sur `embedding_type`
- `idx_track_embeddings_vector` sur `vector` (HNSW)

#### 3. TrackMetadata

Table dédiée pour les métadonnées enrichies (extensible):

| Champ | Type | Description |
|-------|------|-------------|
| `id` | Integer | Clé primaire |
| `track_id` | Integer FK | Référence vers [`Track.id`](backend/api/models/tracks_model.py:15) |
| `metadata_key` | String | Clé de métadonnée |
| `metadata_value` | String | Valeur de métadonnée |
| `metadata_source` | String | Source de métadonnée (lastfm, listenbrainz, etc.) |
| `created_at` | DateTime | Date de création |
| `date_added` | DateTime | Date d'ajout |
| `date_modified` | DateTime | Date de modification |

**Index:**
- `idx_track_metadata_track_id` sur `track_id`
- `idx_track_metadata_key` sur `metadata_key`
- `idx_track_metadata_source` sur `metadata_source`

---

## Impact GraphQL

### Analyse de l'impact

Le projet utilise **Strawberry (GraphQL)** avec les fichiers suivants pour Track:

| Fichier | Rôle | Impact de la migration |
|---------|------|------------------------|
| [`tracks_type.py`](backend/api/graphql/types/tracks_type.py) | Types GraphQL TrackType, TrackCreateInput, TrackUpdateInput | **CRITIQUE** - Contient tous les champs audio features |
| [`track_queries.py`](backend/api/graphql/queries/queries/track_queries.py) | Queries `track(id)` et `tracks(skip, limit, where)` | **MOYEN** - Utilise TrackService |
| [`track_mutations.py`](backend/api/graphql/queries/mutations/track_mutations.py) | Mutations create, update, upsert, batch | **CRITIQUE** - Passe tous les champs audio features |

### Champs audio features dans GraphQL

Les types GraphQL actuels contiennent directement les champs audio features:
- `bpm`, `key`, `scale`, `danceability`
- `mood_happy`, `mood_aggressive`, `mood_party`, `mood_relaxed`
- `instrumental`, `acoustic`, `tonal`
- `camelot_key`, `genre_main`

### Stratégie de migration GraphQL

**Approche: Compatibilité rétroactive avec propriétés calculées**

Pour ne pas cracker les requêtes GraphQL existantes, nous allons:

1. **Créer les nouveaux types GraphQL** pour les tables dédiées:
   - `TrackAudioFeaturesType`
   - `TrackEmbeddingsType`
   - `TrackMetadataType`

2. **Ajouter les relations** sur `TrackType`:
   - `audio_features: TrackAudioFeaturesType | None`
   - `embeddings: list[TrackEmbeddingsType]`
   - `metadata: list[TrackMetadataType]`

3. **Maintenir les champs existants** comme propriétés calculées:
   - Les champs audio features resteront dans `TrackType`
   - Ils liront les données depuis la relation `audio_features`
   - Cela assure la compatibilité avec les requêtes existantes

4. **Mettre à jour les inputs** pour supporter les nouvelles structures:
   - `TrackCreateInput` et `TrackUpdateInput` garderont les champs audio features
   - Les services mapperont ces champs vers les nouvelles tables

### Diagramme de flux GraphQL

```mermaid
graph TD
    A[Client GraphQL] -->|Query/Mutation| B[TrackType]
    B -->|Propriétés calculées| C[TrackAudioFeatures]
    B -->|Relation directe| C
    B -->|Relation directe| D[TrackEmbeddings]
    B -->|Relation directe| E[TrackMetadata]
    C -->|Données audio| B
    D -->|Données vectorielles| B
    E -->|Métadonnées enrichies| B
```

---

## Plan de Migration

### Phase 1: Création des nouvelles tables ✅ TERMINÉ

1. ✅ Créer le modèle [`TrackAudioFeatures`](backend/api/models/track_audio_features_model.py)
2. ✅ Créer le modèle [`TrackEmbeddings`](backend/api/models/track_embeddings_model.py)
3. ✅ Créer le modèle [`TrackMetadata`](backend/api/models/track_metadata_model.py)
4. ✅ Créer les schémas Pydantic correspondants
5. ✅ Créer la migration Alembic pour les nouvelles tables

### Phase 2: Migration des données existantes ✅ TERMINÉ

1. ✅ Créer la migration Alembic pour migrer les données:
   - ✅ Copier les champs audio de [`Track`](backend/api/models/tracks_model.py:44-56) vers [`TrackAudioFeatures`](backend/api/models/track_audio_features_model.py)
   - ✅ Copier le vecteur de [`Track`](backend/api/models/tracks_model.py:40) vers [`TrackEmbeddings`](backend/api/models/track_embeddings_model.py)
   - ✅ Créer des entrées [`TrackMetadata`](backend/api/models/track_metadata_model.py) pour les métadonnées enrichies

### Phase 3: Mise à jour du modèle Track ✅ TERMINÉ

1. ✅ Ajouter les relations avec les nouvelles tables dans [`Track`](backend/api/models/tracks_model.py)
2. ✅ Marquer les champs migrés comme `deprecated` (optionnel)
3. ✅ Mettre à jour les index

### Phase 4: Mise à jour des services ✅ TERMINÉ

1. ✅ Créer [`TrackAudioFeaturesService`](backend/api/services/track_audio_features_service.py)
2. ✅ Créer [`TrackEmbeddingsService`](backend/api/services/track_embeddings_service.py)
3. ✅ Créer [`TrackMetadataService`](backend/api/services/track_metadata_service.py)
4. ✅ Mettre à jour [`TrackService`](backend/api/services/track_service.py) pour utiliser les nouvelles tables

### Phase 5: Mise à jour des routers API ✅ TERMINÉ

1. ✅ Créer [`track_audio_features_api.py`](backend/api/routers/track_audio_features_api.py)
2. ✅ Créer [`track_embeddings_api.py`](backend/api/routers/track_embeddings_api.py)
3. ✅ Créer [`track_metadata_api.py`](backend/api/routers/track_metadata_api.py)
4. ✅ Mettre à jour [`tracks_api.py`](backend/api/routers/tracks_api.py) pour utiliser les nouvelles tables

### Phase 6: Mise à jour de GraphQL ✅ TERMINÉ

1. ✅ Créer les nouveaux types GraphQL:
   - ✅ [`TrackAudioFeaturesType`](backend/api/graphql/types/track_audio_features_type.py)
   - ✅ [`TrackEmbeddingsType`](backend/api/graphql/types/track_embeddings_type.py)
   - ✅ [`TrackMetadataType`](backend/api/graphql/types/track_metadata_type.py)
   - ✅ Inputs correspondants (Create/Update)

2. ✅ Mettre à jour [`TrackType`](backend/api/graphql/types/tracks_type.py):
   - ✅ Ajouter la relation `audio_features: TrackAudioFeaturesType | None`
   - ✅ Ajouter la relation `embeddings: list[TrackEmbeddingsType]`
   - ✅ Ajouter la relation `metadata: list[TrackMetadataType]`
   - ✅ **Garder les champs audio features existants** comme propriétés calculées (compatibilité rétroactive)

3. ✅ Mettre à jour [`track_queries.py`](backend/api/graphql/queries/queries/track_queries.py):
   - ✅ Mettre à jour les queries pour charger les relations audio_features, embeddings, metadata
   - ✅ Maintenir la compatibilité avec les champs existants

4. ✅ Mettre à jour [`track_mutations.py`](backend/api/graphql/queries/mutations/track_mutations.py):
   - ✅ Mettre à jour les mutations pour créer/mettre à jour les nouvelles tables
   - ✅ Mapper les champs audio features vers TrackAudioFeatures
   - ✅ Maintenir la compatibilité avec les inputs existants

5. ✅ Créer les queries et mutations pour les nouvelles tables:
   - ✅ Queries pour TrackAudioFeatures, TrackEmbeddings, TrackMetadata
   - ✅ Mutations pour TrackAudioFeatures, TrackEmbeddings, TrackMetadata

6. ✅ Mettre à jour le cache GraphQL pour les nouvelles tables

### Phase 7: Mise à jour des workers ✅ TERMINÉ

1. ✅ Mettre à jour [`audio_features_service.py`](backend_worker/services/audio_features_service.py) pour utiliser [`TrackAudioFeatures`](backend/api/models/track_audio_features_model.py)
2. ✅ Mettre à jour [`vectorization_service.py`](backend_worker/services/vectorization_service.py) pour utiliser [`TrackEmbeddings`](backend/api/models/track_embeddings_model.py)
3. ✅ Mettre à jour les tâches Celery correspondantes

### Phase 8: Optimisation des performances ✅ TERMINÉ

1. ✅ Créer les index PostgreSQL pour les nouvelles tables
2. ✅ Mettre à jour le cache Redis pour les nouvelles tables
3. ✅ Optimiser les requêtes SQL

### Phase 9: Tests et validation ✅ TERMINÉ

1. ✅ Écrire les tests unitaires pour les nouvelles tables
2. ✅ Écrire les tests d'intégration pour les nouvelles tables
3. ✅ Écrire les tests GraphQL pour les nouvelles tables:
   - ✅ Tests pour TrackAudioFeaturesType queries/mutations
   - ✅ Tests pour TrackEmbeddingsType queries/mutations
   - ✅ Tests pour TrackMetadataType queries/mutations
   - ✅ Tests de compatibilité rétroactive pour TrackType
4. ✅ Exécuter les tests et valider la migration
5. ✅ Valider le démarrage Docker et les 4 conteneurs

### Phase 10: Documentation ✅ TERMINÉ

1. ✅ Mettre à jour la documentation (README, architecture.md)
2. ✅ Documenter la migration
3. ✅ Créer un guide de migration pour les utilisateurs

---

## Avantages de la Nouvelle Architecture

### 1. Séparation des responsabilités

- **Track**: Métadonnées de base uniquement
- **TrackAudioFeatures**: Caractéristiques audio
- **TrackEmbeddings**: Embeddings vectoriels
- **TrackMetadata**: Métadonnées enrichies extensibles

### 2. Extensibilité

- Ajout facile de nouvelles caractéristiques audio
- Support de plusieurs types d'embeddings
- Métadonnées extensibles via clé/valeur

### 3. Performance

- Index optimisés pour chaque table
- Requêtes plus ciblées
- Cache Redis par table

### 4. Traçabilité

- Source d'analyse audio (librosa, acoustid, tags)
- Source de vectorisation (ollama, etc.)
- Date d'analyse et de création

### 5. Maintenance

- Code plus clair et modulaire
- Tests plus faciles à écrire
- Migrations plus simples

---

## Risques et Mitigations

### Risque 1: Régressions dans les tests

**Mitigation:** Exécuter tous les tests après chaque phase de migration

### Risque 2: Problèmes de performance

**Mitigation:** Profiler les requêtes après migration, optimiser les index

### Risque 3: Incohérence dans les données

**Mitigation:** Utiliser des transactions pour les migrations, valider les données après migration

### Risque 4: Impact sur les workers

**Mitigation:** Mettre à jour les workers progressivement, tester en isolation

---

## Checklist de Migration

### Phase 1: Création des nouvelles tables ✅
- [x] Créer le modèle TrackAudioFeatures
- [x] Créer le modèle TrackEmbeddings
- [x] Créer le modèle TrackMetadata
- [x] Créer les schémas Pydantic
- [x] Créer la migration Alembic

### Phase 2: Migration des données existantes ✅
- [x] Créer la migration Alembic pour les données
- [x] Migrer les caractéristiques audio
- [x] Migrer les embeddings
- [x] Créer les métadonnées enrichies

### Phase 3: Mise à jour du modèle Track ✅
- [x] Ajouter les relations
- [x] Marquer les champs comme deprecated
- [x] Mettre à jour les index

### Phase 4: Mise à jour des services ✅
- [x] Créer TrackAudioFeaturesService
- [x] Créer TrackEmbeddingsService
- [x] Créer TrackMetadataService
- [x] Mettre à jour TrackService

### Phase 5: Mise à jour des routers API ✅
- [x] Créer track_audio_features_api.py
- [x] Créer track_embeddings_api.py
- [x] Créer track_metadata_api.py
- [x] Mettre à jour tracks_api.py

### Phase 6: Mise à jour des workers ✅
- [x] Mettre à jour audio_features_service.py
- [x] Mettre à jour vectorization_service.py
- [x] Mettre à jour les tâches Celery

### Phase 7: Optimisation des performances ✅
- [x] Créer les index PostgreSQL
- [x] Mettre à jour le cache Redis
- [x] Optimiser les requêtes SQL

### Phase 8: Tests et validation ✅
- [x] Écrire les tests unitaires
- [x] Écrire les tests d'intégration
- [x] Exécuter les tests
- [x] Valider Docker

### Phase 9: Nettoyage ⏳
- [ ] Supprimer les champs redondants
- [ ] Supprimer les champs migrés

### Phase 10: Documentation ✅
- [x] Mettre à jour README
- [x] Mettre à jour architecture.md
- [x] Documenter la migration
- [x] Créer guide de migration

---

## Livrables

1. ✅ Nouveaux modèles SQLAlchemy (TrackAudioFeatures, TrackEmbeddings, TrackMetadata)
2. ✅ Nouveaux schémas Pydantic
3. ✅ Nouveaux services (TrackAudioFeaturesService, TrackEmbeddingsService, TrackMetadataService)
4. ✅ Nouveaux routers API
5. ✅ Migrations Alembic
6. ✅ Tests unitaires et d'intégration
7. ✅ Documentation mise à jour
8. ✅ Validation Docker réussie

---

## Fichiers Créés/Modifiés

### Modèles
- [`backend/api/models/track_audio_features_model.py`](backend/api/models/track_audio_features_model.py) ✅
- [`backend/api/models/track_embeddings_model.py`](backend/api/models/track_embeddings_model.py) ✅
- [`backend/api/models/track_metadata_model.py`](backend/api/models/track_metadata_model.py) ✅

### Services
- [`backend/api/services/track_audio_features_service.py`](backend/api/services/track_audio_features_service.py) ✅
- [`backend/api/services/track_embeddings_service.py`](backend/api/services/track_embeddings_service.py) ✅
- [`backend/api/services/track_metadata_service.py`](backend/api/services/track_metadata_service.py) ✅

### Routers API
- [`backend/api/routers/track_audio_features_api.py`](backend/api/routers/track_audio_features_api.py) ✅
- [`backend/api/routers/track_embeddings_api.py`](backend/api/routers/track_embeddings_api.py) ✅
- [`backend/api/routers/track_metadata_api.py`](backend/api/routers/track_metadata_api.py) ✅

### Schémas
- [`backend/api/schemas/track_audio_features_schema.py`](backend/api/schemas/track_audio_features_schema.py) ✅
- [`backend/api/schemas/track_embeddings_schema.py`](backend/api/schemas/track_embeddings_schema.py) ✅
- [`backend/api/schemas/track_metadata_schema.py`](backend/api/schemas/track_metadata_schema.py) ✅

### GraphQL Types
- [`backend/api/graphql/types/track_audio_features_type.py`](backend/api/graphql/types/track_audio_features_type.py) ✅
- [`backend/api/graphql/types/track_embeddings_type.py`](backend/api/graphql/types/track_embeddings_type.py) ✅
- [`backend/api/graphql/types/track_metadata_type.py`](backend/api/graphql/types/track_metadata_type.py) ✅

### GraphQL Queries
- [`backend/api/graphql/queries/track_audio_features_queries.py`](backend/api/graphql/queries/track_audio_features_queries.py) ✅
- [`backend/api/graphql/queries/track_embeddings_queries.py`](backend/api/graphql/queries/track_embeddings_queries.py) ✅
- [`backend/api/graphql/queries/track_metadata_queries.py`](backend/api/graphql/queries/track_metadata_queries.py) ✅

### GraphQL Mutations
- [`backend/api/graphql/mutations/track_audio_features_mutations.py`](backend/api/graphql/mutations/track_audio_features_mutations.py) ✅
- [`backend/api/graphql/mutations/track_embeddings_mutations.py`](backend/api/graphql/mutations/track_embeddings_mutations.py) ✅
- [`backend/api/graphql/mutations/track_metadata_mutations.py`](backend/api/graphql/mutations/track_metadata_mutations.py) ✅

### Migration Alembic
- [`alembic/versions/create_track_features_embeddings_metadata_tables.py`](alembic/versions/create_track_features_embeddings_metadata_tables.py) ✅

### Documentation
- [`docs/migration/track_model_migration_guide.md`](docs/migration/track_model_migration_guide.md) ✅
- [`docs/architecture/02-services.md`](docs/architecture/02-services.md) ✅
- [`docs/architecture/09-backend-api.md`](docs/architecture/09-backend-api.md) ✅
