# Plan de Migration Sync vers Async - Backend API

## Vue d'ensemble

Ce plan détaille la migration complète des services et routers du backend API de SoniqueBay vers une architecture asynchrone complète, en cohérence avec les patterns existants du projet.

## État Actuel de la Migration

### Services Déjà Migrés en Async ✓

- `artist_service.py` - Totalement migré
- `album_service.py` - Totalement migré
- `covers_service.py` - Totalement migré

### Services Partiellement Migrés ⚠️

- `track_service.py` - 3 méthodes restantes en sync
- `settings_service.py` - 1 méthode async, autres en sync

### Services Totalement en Sync ✗

- `genres_service.py` - Toutes les méthodes en sync
- `tags_service.py` - Toutes les méthodes en sync
- `scan_service.py` - Toutes les méthodes en sync
- `search_service.py` - Toutes les méthodes en sync
- `playqueue_service.py` - Toutes les méthodes en sync
- `artist_similar_service.py` - Toutes les méthodes en sync
- `artist_embedding_service.py` - Toutes les méthodes en sync

### Routers Partiellement Migrés ⚠️

- `tracks_api.py` - Endpoints async mais appels services non awaités
- `artists_api.py` - Mixte async/sync
- `albums_api.py` - Mixte async/sync

## Architecture Cible

```mermaid
graph TD
    A[Frontend NiceGUI] --> B[API FastAPI]
    B --> C[Services Layer]
    C --> D[PostgreSQL]
    C --> E[Redis Cache]
    
    subgraph Services
        C1[Artist Service] -.->|Async|-. C
        C2[Album Service] -.->|Async|-. C
        C3[Track Service] -.->|Partiel|-. C
        C4[Genre Service] -.->|Sync|-. C
        C5[Tag Service] -.->|Sync|-. C
        C6[Scan Service] -.->|Sync|-. C
        C7[Search Service] -.->|Sync|-. C
        C8[PlayQueue Service] -.->|Sync|-. C
        C9[Settings Service] -.->|Partiel|-. C
        C10[Artist Similar Service] -.->|Sync|-. C
        C11[Artist Embedding Service] -.->|Sync|-. C
        C12[Covers Service] -.->|Async|-. C
    end
```

## Principes de Migration

### 1. Pattern AsyncSession

Tous les services doivent utiliser `AsyncSession` de SQLAlchemy au lieu de `Session` synchrone.

**Avant (Sync):**

```python
from sqlalchemy.orm import Session

class Service:
    def __init__(self, db: Session):
        self.db = db
    
    def get_items(self):
        items = self.db.query(Model).all()
        return items
```

**Après (Async):**

```python
from sqlalchemy.ext.asyncio import AsyncSession

class Service:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_items(self):
        query = select(Model)
        result = await self.db.execute(query)
        items = result.scalars().all()
        return items
```

### 2. Pattern de Requêtes SQL

Remplacer `self.db.query(Model)` par `select(Model)` avec `await self.db.execute()`.

**Avant:**

```python
items = self.db.query(Model).filter(Model.id == id).first()
```

**Après:**

```python
query = select(Model).where(Model.id == id)
result = await self.db.execute(query)
item = result.scalars().first()
```

### 3. Gestion des Transactions

Utiliser `await self.db.commit()` et `await self.db.rollback()` au lieu des versions synchrones.

### 4. Pattern de Routers

Les routers doivent être `async def` et utiliser `await` sur les appels de services.

**Avant:**

```python
@router.get("/")
def get_items(db: Session = Depends(get_db)):
    service = Service(db)
    items = service.get_items()
    return items
```

**Après:**

```python
@router.get("/")
async def get_items(db: AsyncSession = Depends(get_db)):
    service = Service(db)
    items = await service.get_items()
    return items
```

## Plan de Migration Détaillé

### Phase 1: Services Critiques (Priorité Haute)

#### 1.1 Migrer track_service.py

**Fichier:** `backend/api/services/track_service.py`

**Méthodes à migrer:**

- `_create_tracks_batch_optimized()` (lignes 202-364)
  - Remplacer `self.session.query()` par `await self.session.execute()`
  - Remplacer `self.session.commit()` par `await self.session.commit()`
  - Remplacer `self.session.refresh()` par `await self.session.refresh()`
  - Remplacer `self.session.rollback()` par `await self.session.rollback()`

- `_update_tracks_batch_optimized()` (lignes 366-419)
  - Même pattern que ci-dessus

- `search_tracks()` (lignes 421-464)
  - Convertir en async
  - Remplacer `self.session.query()` par `select()` + `await self.session.execute()`

**Impact:** Critique - Utilisé par le scan et les opérations batch

#### 1.2 Migrer genres_service.py

**Fichier:** `backend/api/services/genres_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `search_genres()` - Convertir en async
- `create_genre()` - Convertir en async
- `read_genres()` - Convertir en async
- `read_genre()` - Convertir en async
- `update_genre()` - Convertir en async
- `delete_genre()` - Convertir en async

**Impact:** Moyen - Utilisé par les endpoints de recherche et gestion des genres

#### 1.3 Migrer tags_service.py

**Fichier:** `backend/api/services/tags_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `get_genre_tags()` - Convertir en async
- `get_mood_tags()` - Convertir en async
- `get_genre_tag()` - Convertir en async
- `get_mood_tag()` - Convertir en async
- `create_genre_tag()` - Convertir en async
- `create_mood_tag()` - Convertir en async

**Impact:** Moyen - Utilisé par la gestion des tags de pistes

### Phase 2: Services de Recherche et Scan (Priorité Haute)

#### 2.1 Migrer search_service.py

**Fichier:** `backend/api/services/search_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `search()` - Convertir en async
- `_text_search()` - Convertir en async
- `_vector_search()` - Convertir en async
- `_combine_results()` - Déjà statique, pas de changement
- `_get_facets()` - Convertir en async
- `_get_facets_fallback()` - Convertir en async
- `typeahead_search()` - Convertir en async

**Impact:** Critique - Utilisé par la recherche hybride et les facettes

#### 2.2 Migrer scan_service.py

**Fichier:** `backend/api/services/scan_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `convert_path_to_docker()` - Déjà statique, pas de changement
- `validate_base_directory()` - Déjà statique, pas de changement
- `launch_scan()` - Convertir en async
  - Remplacer `db.query()` par `await db.execute()`
  - Remplacer `db.commit()` par `await db.commit()`

**Impact:** Critique - Utilisé par le scan de bibliothèque

### Phase 3: Services de Gestion (Priorité Moyenne)

#### 3.1 Migrer playqueue_service.py

**Fichier:** `backend/api/services/playqueue_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `get_queue()` - Convertir en async
- `add_track()` - Convertir en async
- `remove_track()` - Convertir en async
- `move_track()` - Convertir en async
- `clear_queue()` - Convertir en async

**Impact:** Moyen - Utilisé par le player et la file de lecture

#### 3.2 Migrer settings_service.py

**Fichier:** `backend/api/services/settings_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `get_path_variables()` - Déjà statique, pas de changement
- `validate_template()` - Déjà statique, pas de changement
- `create_setting()` - Convertir en async
- `read_settings()` - Convertir en async
- `read_setting()` - Convertir en async
- `update_setting()` - Convertir en async

**Impact:** Moyen - Utilisé par la gestion des paramètres système

### Phase 4: Services IA et Recommandations (Priorité Moyenne)

#### 4.1 Migrer artist_similar_service.py

**Fichier:** `backend/api/services/artist_similar_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `create_similar_relationship()` - Convertir en async
- `get_similar_artists()` - Convertir en async
- `get_similar_artists_with_details()` - Convertir en async
- `update_similar_relationship()` - Convertir en async
- `delete_similar_relationship()` - Convertir en async
- `get_all_relationships_paginated()` - Convertir en async
- `find_similar_artists_by_name()` - Convertir en async
- `get_relationship_by_ids()` - Convertir en async

**Impact:** Moyen - Utilisé par les recommandations d'artistes

#### 4.2 Migrer artist_embedding_service.py

**Fichier:** `backend/api/services/artist_embedding_service.py`

**Méthodes à migrer:**

- `__init__()` - Changer `Session` en `AsyncSession`
- `create_embedding()` - Convertir en async
- `get_embedding_by_artist()` - Convertir en async
- `update_embedding()` - Convertir en async
- `get_all_embeddings()` - Convertir en async
- `get_embeddings_by_cluster()` - Convertir en async
- `delete_embedding()` - Convertir en async
- `train_gmm()` - Convertir en async
- `_save_gmm_model()` - Convertir en async
- `get_similar_artists()` - Convertir en async
- `generate_artist_embeddings()` - Convertir en async
- `_aggregate_track_embeddings()` - Convertir en async
- `find_similar_artists_vector()` - Convertir en async
- `get_cluster_info()` - Convertir en async

**Impact:** Moyen - Utilisé par les embeddings et le clustering GMM

### Phase 5: Mise à jour des Routers

#### 5.1 Migrer tracks_api.py

**Fichier:** `backend/api/routers/tracks_api.py`

**Endpoints à migrer:**

- `get_tracks_count()` - Ajouter `await` sur `service.get_tracks_count()`
- `search_tracks()` - Ajouter `await` sur `service.search_tracks()`
- `create_or_update_tracks_batch()` - Ajouter `await` sur `service.create_or_update_tracks_batch()`
- `create_track()` - Ajouter `await` sur `service.create_track()`
- `read_tracks()` - Ajouter `await` sur `service.read_tracks()`
- `read_track()` - Ajouter `await` sur `service.read_track()`
- `update_track()` - Ajouter `await` sur `service.update_track()`
- `update_track_tags()` - Ajouter `await` sur `service.update_track_tags()`
- `delete_track()` - Ajouter `await` sur `service.delete_track()`
- `read_artist_tracks_by_album()` - Ajouter `await` sur `service.get_artist_tracks()`
- `read_artist_tracks()` - Ajouter `await` sur `service.get_artist_tracks()`
- `update_track_features()` - Ajouter `await` sur `service.read_track()` et `service.update_track()`

**Impact:** Critique - Router principal pour les pistes

#### 5.2 Migrer artists_api.py

**Fichier:** `backend/api/routers/artists_api.py`

**Endpoints à migrer:**

- `search_artists()` - Ajouter `await` sur `service.search_artists()`
- `create_artists_batch()` - Convertir en async et ajouter `await`
- `create_artist()` - Convertir en async et ajouter `await`
- `get_artists_count()` - Convertir en async et ajouter `await`
- `read_artists()` - Convertir en async et ajouter `await`
- `update_artist()` - Convertir en async et ajouter `await`
- `delete_artist()` - Convertir en async et ajouter `await`
- `read_artist_tracks()` - Ajouter `await` sur `service.get_artist_tracks()`
- `get_similar_artists()` - Ajouter `await` sur `service.get_similar_artists_with_details()`
- `create_similar_relationship()` - Convertir en async et ajouter `await`
- `update_similar_relationship()` - Convertir en async et ajouter `await`
- `delete_similar_relationship()` - Convertir en async et ajouter `await`
- `get_all_similar_relationships()` - Convertir en async et ajouter `await`
- `fetch_artist_lastfm_info()` - Convertir en async et ajouter `await`
- `update_artist_lastfm_info()` - Convertir en async et ajouter `await`
- `fetch_similar_artists()` - Convertir en async et ajouter `await`
- `update_artist_similar()` - Convertir en async et ajouter `await`
- `search_similar_artists_by_name()` - Convertir en async et ajouter `await`

**Impact:** Critique - Router principal pour les artistes

#### 5.3 Migrer albums_api.py

**Fichier:** `backend/api/routers/albums_api.py`

**Endpoints à migrer:**

- `search_albums()` - Ajouter `await` sur `service.search_albums()`
- `create_albums_batch()` - Convertir en async et ajouter `await`
- `create_album()` - Convertir en async et ajouter `await`
- `read_albums()` - Convertir en async et ajouter `await`
- `read_album()` - Ajouter `await` sur `service.read_album()`
- `read_artist_albums()` - Convertir en async et ajouter `await`
- `update_album()` - Convertir en async et ajouter `await`
- `read_album_tracks()` - Convertir en async et ajouter `await`
- `delete_album()` - Convertir en async et ajouter `await`

**Impact:** Critique - Router principal pour les albums

#### 5.4 Migrer autres routers

**Fichiers à vérifier et migrer:**

- `genres_api.py` - Migrer tous les endpoints
- `tags_api.py` - Migrer tous les endpoints
- `scan_api.py` - Migrer tous les endpoints
- `search_api.py` - Migrer tous les endpoints
- `playqueue_api.py` - Migrer tous les endpoints
- `settings_api.py` - Migrer tous les endpoints
- `artist_embeddings_api.py` - Migrer tous les endpoints
- `artist_similar_api.py` - Migrer tous les endpoints

### Phase 6: Mise à jour des Dépendances

#### 6.1 Mettre à jour get_db()

**Fichier:** `backend/api/utils/database.py`

**Action:** S'assurer que `get_db()` retourne une `AsyncSession` au lieu de `Session`

#### 6.2 Vérifier les imports

**Action:** Mettre à jour tous les imports de `Session` vers `AsyncSession` dans les services et routers

### Phase 7: Tests et Validation

#### 7.1 Exécuter les tests existants

**Commande:** `python -m pytest ./tests/ -x --tb=no -q --snapshot-update -n auto`

#### 7.2 Tester les endpoints critiques

**Endpoints à tester:**

- `/api/tracks/*`
- `/api/artists/*`
- `/api/albums/*`
- `/api/search`
- `/api/scan`

#### 7.3 Valider Docker

**Commande:** `docker-compose build && docker-compose up`

**Vérifications:**

- Les 4 conteneurs démarrent sans erreur
- Les endpoints FastAPI/GraphQL répondent
- L'UI NiceGUI fonctionne

## Checklist de Migration

### Services

- [ ] `track_service.py` - Migrer 3 méthodes restantes
- [ ] `artist_service.py` - Déjà migré ✓
- [ ] `album_service.py` - Déjà migré ✓
- [ ] `genres_service.py` - Migrer toutes les méthodes
- [ ] `tags_service.py` - Migrer toutes les méthodes
- [ ] `scan_service.py` - Migrer toutes les méthodes
- [ ] `search_service.py` - Migrer toutes les méthodes
- [ ] `playqueue_service.py` - Migrer toutes les méthodes
- [ ] `settings_service.py` - Migrer méthodes restantes
- [ ] `artist_similar_service.py` - Migrer toutes les méthodes
- [ ] `artist_embedding_service.py` - Migrer toutes les méthodes
- [ ] `covers_service.py` - Déjà migré ✓

### Routers

- [ ] `tracks_api.py` - Ajouter await sur tous les appels services
- [ ] `artists_api.py` - Migrer tous les endpoints en async
- [ ] `albums_api.py` - Migrer tous les endpoints en async
- [ ] `genres_api.py` - Migrer tous les endpoints
- [ ] `tags_api.py` - Migrer tous les endpoints
- [ ] `scan_api.py` - Migrer tous les endpoints
- [ ] `search_api.py` - Migrer tous les endpoints
- [ ] `playqueue_api.py` - Migrer tous les endpoints
- [ ] `settings_api.py` - Migrer tous les endpoints
- [ ] `artist_embeddings_api.py` - Migrer tous les endpoints
- [ ] `artist_similar_api.py` - Migrer tous les endpoints

### Infrastructure

- [ ] Mettre à jour `get_db()` pour retourner AsyncSession
- [ ] Vérifier tous les imports Session → AsyncSession
- [ ] Exécuter les tests existants
- [ ] Valider le démarrage Docker
- [ ] Vérifier les logs pour s'assurer qu'il n'y a pas d'erreurs

## Notes Importantes

### Contraintes RPi4

- Éviter les boucles bloquantes dans les méthodes async
- Utiliser `asyncio.gather()` pour les opérations parallèles
- Attention aux chargements en mémoire (pagination obligatoire)

### Règles de Codage

- Respecter PEP8
- Utiliser les annotations de type (`typing`)
- Ajouter des docstrings claires
- Utiliser `utils/logging.py` pour les logs (pas de `print`)
- Gestion d'erreurs explicites avec exceptions

### Séparation des Préoccupations

- Services critiques (track, search, scan) en priorité
- Services de gestion (playqueue, settings) en priorité moyenne
- Services IA (artist_similar, artist_embedding) en priorité moyenne
- Routers mis à jour après les services correspondants

## Risques et Mitigations

### Risque 1: Régressions dans les tests

**Mitigation:** Exécuter tous les tests après chaque phase de migration

### Risque 2: Problèmes de performance

**Mitigation:** Profiler les endpoints critiques après migration

### Risque 3: Incohérence dans les routers

**Mitigation:** Vérifier que tous les endpoints utilisent `await` de manière cohérente

## Livrables

1. Tous les services migrés en async
2. Tous les routers mis à jour pour utiliser await
3. Tests passants sans régression
4. Documentation mise à jour si nécessaire
5. Validation Docker réussie
