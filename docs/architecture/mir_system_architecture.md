# Architecture du Système MIR (Music Information Retrieval)

## Vue d'ensemble

Le système MIR de SoniqueBay est conçu pour extraire, normaliser et scorer les caractéristiques audio des pistes musicales. Il s'intègre dans l'architecture globale via l'API FastAPI et utilise Celery pour les traitements asynchrones.

## Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SoniqueBay Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │   NiceGUI    │    │  FastAPI +   │    │  Celery      │                 │
│   │   Frontend   │◄──►│   GraphQL    │◄──►│  Workers     │                 │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│           │                   │                   │                          │
│           │                   ▼                   ▼                          │
│           │           ┌──────────────┐    ┌──────────────┐                 │
│           │           │  PostgreSQL  │    │    Redis     │                 │
│           │           │   (Primary)  │    │ (Cache/Pub)  │                 │
│           │           └──────────────┘    └──────────────┘                 │
│           │                   │                                                  │
│           └───────────────────┼──────────────────────────────────────────────┘
│                               │
│                               ▼
│                  ┌─────────────────────────────┐
│                  │    MIR Pipeline Service     │
│                  │   (Audio Feature Extraction) │
│                  └─────────────────────────────┘
│                               │
│                               ▼
│                  ┌─────────────────────────────┐
│                  │  MIR Normalization Service  │
│                  │  (Value Normalization 0-1)   │
│                  └─────────────────────────────┘
│                               │
│                               ▼
│                  ┌─────────────────────────────┐
│                  │    MIR Scoring Service       │
│                  │  (Composite Score Calc)      │
│                  └─────────────────────────────┘
│                               │
│                               ▼
│                  ┌─────────────────────────────┐
│                  │  Synthetic Tags Service      │
│                  │  (High-level Tags)          │
│                  └─────────────────────────────┘
│                               │
│                               ▼
│                  ┌─────────────────────────────┐
│                  │     MIR LLM Service          │
│                  │  (Context for LLMs)         │
│                  └─────────────────────────────┘
│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Composants MIR

### 1. Modèles de Données

#### TrackMIRRaw
Stocke les données brutes issues des extracteurs audio.

| Champ | Type | Description |
|-------|------|-------------|
| id | Integer | Identifiant unique |
| track_id | Integer | Référence vers tracks |
| extractor | String | Nom de l'extracteur (acoustid, essentia, librosa) |
| version | String | Version de l'extracteur |
| tags_json | JSON | Tags bruts AcoustID |
| raw_data_json | JSON | Données brutes complètes |
| extraction_time | Float | Temps d'extraction (secondes) |
| confidence | Float | Confiance [0-1] |

#### TrackMIRNormalized
Valeurs normalisées [0.0-1.0] pour tous les descripteurs.

| Champ | Type | Description |
|-------|------|-------------|
| id | Integer | Identifiant unique |
| track_id | Integer | Référence vers tracks |
| loudness | Float | Normalisé: very_quiet [0] -> very_loud [1] |
| tempo | Float | Normalisé: slow [0] -> fast [1] |
| energy | Float | Normalisé: low [0] -> high [1] |
| danceability | Float | Normalisé: not_danceable [0] -> danceable [1] |
| valence | Float | Normalisé: negative [0] -> positive [1] |
| acousticness | Float | Normalisé: electronic [0] -> acoustic [1] |
| instrumentalness | Float | Normalisé: vocal [0] -> instrumental [1] |
| speechiness | Float | Normalisé: music [0] -> speech [1] |
| liveness | Float | Normalisé: studio [0] -> live [1] |

#### TrackMIRScores
Scores globaux composites [0.0-1.0].

| Champ | Type | Description |
|-------|------|-------------|
| id | Integer | Identifiant unique |
| track_id | Integer | Référence vers tracks |
| energy_score | Float | Score énergétique global |
| mood_valence | Float | Valence émotionnelle [-1 à 1] -> [0 à 1] |
| dance_score | Float | Score de danceabilité |
| acousticness_score | Float | Score acousticness |
| complexity_score | Float | Score de complexité musicale |
| emotional_intensity | Float | Intensité émotionnelle |
| groove_score | Score de groove/rythme |
| brightness_score | Float | Score de clarté/splendeur |
| darkness_score | Float | Score de sombres/majesté |

#### TrackMIRSyntheticTags
Tags synthétiques haut-niveau.

| Champ | Type | Description |
|-------|------|-------------|
| id | Integer | Identifiant unique |
| track_id | Integer | Référence vers tracks |
| tag_name | String | Nom du tag (dark, bright, energetic, chill) |
| tag_category | String | Catégorie (mood, genre, instrument, era) |
| confidence | Float | Confiance [0-1] |
| source | String | Source (taxonomy_fusion, llm, manual) |

### 2. Services

#### MIRPipelineService
Pipeline d'extraction des caractéristiques audio.

```python
class MIRPipelineService:
    async def process_track_mir(
        self,
        track_id: int,
        file_path: str,
        tags: dict,
    ) -> dict:
        """Traite une piste et retourne les données MIR brutes."""
        # 1. Extraction AcoustID
        # 2. Extraction Essentia/Librosa
        # 3. Fusion des données
        # 4. Sauvegarde en base
```

#### MIRNormalizationService
Normalisation des valeurs vers [0.0-1.0].

```python
class MIRNormalizationService:
    def normalize_binary_to_continuous(
        self,
        value: Union[bool, str, int],
        confidence: float = 1.0,
    ) -> float:
        """Convertit les valeurs binaires en score continu."""

    def normalize_bpm(self, bpm: Optional[float]) -> float:
        """Normalise le BPM vers [0-1] (60->0, 200->1)."""

    def normalize_key_scale(
        self,
        key: str,
        scale: str = "major",
    ) -> Tuple[str, str, str]:
        """Normalise la tonalité et retourne le code Camelot."""
```

#### MIRScoringService
Calcul des scores composites.

```python
class MIRScoringService:
    def calculate_energy_score(
        self,
        energy: float,
        loudness: float,
        tempo: float,
    ) -> float:
        """Calcule le score énergétique global."""

    def calculate_mood_valence(
        self,
        valence: float,
        mood_happy: float,
        mood_aggressive: float,
    ) -> float:
        """Calcule la valence émotionnelle."""

    def calculate_all_scores(
        self,
        normalized_data: dict,
    ) -> dict:
        """Calcule tous les scores en une fois."""
```

#### SyntheticTagsService
Génération des tags synthétiques.

```python
class SyntheticTagsService:
    def generate_synthetic_tags(
        self,
        normalized_data: dict,
        scores: dict,
    ) -> list[SyntheticTag]:
        """Génère les tags synthétiques depuis les données normalisées."""

    def map_energy_to_tags(self, energy: float) -> list[str]:
        """Map l'énergie vers des tags."""

    def map_mood_to_tags(self, valence: float, arousal: float) -> list[str]:
        """Map le mood vers des tags via le modèle circumplex."""
```

#### MIRLLMService
Exposition des données MIR aux LLM.

```python
class MIRLLMService:
    def generate_track_summary(self, track_id: int, mir_data: dict) -> str:
        """Génère un résumé de la track pour les LLM."""

    def generate_mir_context(self, track_id: int) -> dict:
        """Génère le contexte MIR pour les prompts LLM."""

    def generate_search_query_suggestions(self, mir_data: dict) -> list[str]:
        """Génère des suggestions de requêtes de recherche."""

    def generate_playlist_prompts(self, mir_data: dict) -> list[str]:
        """Génère des prompts pour la création de playlists."""
```

### 3. Tâches Celery

#### File: `backend_worker/tasks/mir_tasks.py`

| Tâche | Nom | Queue | Description |
|-------|-----|-------|-------------|
| process_track_mir | mir.process_track | mir | Traitement MIR complet d'une piste |
| process_batch_mir | mir.process_batch | mir | Traitement MIR en lot |
| reprocess_track_mir | mir.reprocess_track | mir | Re-traitement d'une piste |
| calculate_mir_scores | mir.calculate_scores | mir | Calcul des scores MIR |
| generate_synthetic_tags | mir.generate_synthetic_tags | mir | Génération des tags synthétiques |

### 4. Intégration API

#### Endpoints REST

```python
# POST /api/v1/mir/process
async def process_track_mir(track_id: int, file_path: str):
    """Lance le traitement MIR d'une piste."""

# POST /api/v1/mir/batch
async def process_batch_mir(tracks: list[TrackMIRRequest]):
    """Lance le traitement MIR en lot."""

# GET /api/v1/mir/{track_id}
async def get_mir_data(track_id: int) -> TrackMIRResponse:
    """Récupère toutes les données MIR d'une piste."""

# GET /api/v1/mir/{track_id}/scores
async def get_mir_scores(track_id: int) -> TrackMIRScoresResponse:
    """Récupère les scores MIR d'une piste."""

# GET /api/v1/mir/{track_id}/tags
async def get_synthetic_tags(track_id: int) -> list[SyntheticTagResponse]:
    """Récupère les tags synthétiques d'une piste."""
```

#### Mutations GraphQL

```graphql
type Mutation {
    processTrackMIR(trackId: ID!, filePath: String!): TrackMIRResult!
    processBatchMIR(tracks: [TrackMIRInput!]!): BatchMIRResult!
    recalculateMIRScores(trackId: ID!): TrackMIRScoresResult!
    regenerateSyntheticTags(trackId: ID!): [SyntheticTag!]!
}
```

## Flux de Données

```
1. Scan de fichier audio
   │
   ▼
2. Extraction des tags AcoustID (chromaprint)
   │
   ▼
3. Extraction Essentia/Librosa (descripteurs)
   │
   ▼
4. Sauvegarde TrackMIRRaw
   │
   ▼
5. Normalisation vers [0-1]
   │
   ▼
6. Sauvegarde TrackMIRNormalized
   │
   ▼
7. Calcul des scores composites
   │
   ▼
8. Sauvegarde TrackMIRScores
   │
   ▼
9. Génération des tags synthétiques
   │
   ▼
10. Sauvegarde TrackMIRSyntheticTags
    │
    ▼
11. Exposition via API/GraphQL
```

## Configuration

### Variables d'environnement

```bash
# Extraction MIR
MIR_EXTRACTOR=acoustid  # ou essentia, librosa
MIR_NORMALIZATION_VERSION=1.0
MIR_SCORING_ALGORITHM=v1

# Taxonomie des genres
GENRE_TAXONOMY_PATH=backend_worker/utils/genre-tree.yaml
GENRE_MAPPING_PATH=backend_worker/utils/genre.json

# Tags AcoustID
ACOUSTID_API_KEY=your_api_key
ACOUSTID_CACHE_TTL=86400
```

## Considérations de Performance

### Raspberry Pi 4

- **Mémoire**: Limiter la taille des lots pour éviter les OOM
- **CPU**: Utiliser des tâches asynchrones pour les I/O bound
- **Stockage**: Les index PostgreSQL sont cruciaux pour les requêtes

### Optimisations

```python
# Traitement par lots
BATCH_SIZE = 50  # Pour le RPi4

# Cache Redis
CACHE_TTL_MIR_RAW = 3600      # 1 heure
CACHE_TTL_MIR_NORMALIZED = 7200  # 2 heures
CACHE_TTL_MIR_SCORES = 7200     # 2 heures

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
```

## Tests

### Tests unitaires

```bash
# Tests des services MIR
pytest tests/backend/test_services/test_mir_normalization_service.py -v
pytest tests/backend/test_services/test_mir_scoring_service.py -v
pytest tests/backend/test_services/test_synthetic_tags_service.py -v
pytest tests/backend/test_services/test_mir_llm_service.py -v

# Tests des tâches Celery
pytest tests/worker/test_mir_tasks.py -v
```

### Tests d'intégration

```bash
# Tests d'intégration pipeline MIR
pytest tests/backend/test_integration/test_mir_pipeline_integration.py -v

# Tests d'intégration API
pytest tests/backend/test_integration/test_mir_api_integration.py -v
```

## Monitoring

### Métriques Celery

```python
# Tâches MIR
mir_process_track_total
mir_process_track_duration
mir_process_track_success
mir_process_track_failure

mir_process_batch_total
mir_process_batch_duration
mir_process_batch_size
```

### Health Checks

```python
# Endpoint de santé
GET /health/mir

{
    "status": "healthy",
    "components": {
        "pipeline": "up",
        "normalization": "up",
        "scoring": "up",
        "synthetic_tags": "up"
    },
    "last_run": "2026-02-03T19:00:00Z"
}
```
