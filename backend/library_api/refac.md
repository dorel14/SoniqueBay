# REFAC.md — Migration vers MVC + Services (prompt pour GitHub Copilot)

> **But** : fournir à GitHub Copilot un seul fichier clair et exécutable (sans sections dispersées) pour refactoriser automatiquement les endpoints REST (FastAPI) et les resolvers GraphQL vers une architecture **MVC + Services**.

---

## Instructions générales (à Copilot)

Tu es un assistant de refactorisation automatique. Tu dois **transformer** le code existant pour extraire la logique métier hors des routers/rest endpoints et des resolvers GraphQL, et la placer dans une couche `services/`. Respecte strictement la structure et les règles ci-dessous.

### Contexte projet

* Framework web : **FastAPI** (routers `*_api.py`).
* ORM : **SQLAlchemy** (models dans `backend/api/models/`).
* Schemas/DTO : **Pydantic** (dans `backend/api/schemas/`).
* Tâches asynchrones : **Celery** (utilisé par `analysis_api.py`).
* Fichiers à modifier : `backend/api/routers/*` (ou `backend/api/*_api.py`) et resolvers GraphQL.

### Objectif

* Créer une couche `backend/services/` (une classe service par domaine) et déplacer **toute** la logique métier actuelle des routers vers ces services.
* Les routers REST ne doivent plus contenir de logique métier : seulement validation d'entrée, instantiation du service, appel de la méthode et conversion en schema Pydantic.
* Les resolvers GraphQL doivent réutiliser les mêmes services.

---

## Règles détaillées

1. **Structure des services**

   * Créer `backend/services/album_service.py`, `backend/services/artist_service.py`, `backend/services/analysis_service.py`.
   * Chaque fichier exporte une **classe** (`AlbumService`, `ArtistService`, `AnalysisService`) dont le constructeur prend `db: Session` (SQLAlchemy session).
   * Les méthodes doivent encapsuler toute la logique métier (DB queries complexes, vérifications d'existence, batch insert, gestion des conflits, lancement de tâches Celery, manipulation de TinyDB, etc.).
   * Les services lèvent des exceptions métiers (`ValueError`, `NotFoundError` — définir localement si besoin) ; les routers traduisent en `HTTPException`.

2. **Controllers / Routers**

   * Ne plus faire de `db.query(...)` ni de logique métier dans les routers.
   * Exemple de pattern à appliquer à chaque endpoint :

```python
# routers/albums_api.py (extrait)
from fastapi import APIRouter, Depends, HTTPException
from backend.utils.database import get_db
from backend.services.album_service import AlbumService
from backend.api.schemas.albums_schema import AlbumCreate, Album

router = APIRouter(prefix="/api/albums", tags=["albums"])

@router.post("/", response_model=Album)
def create_album(album: AlbumCreate, db=Depends(get_db)):
    service = AlbumService(db)
    try:
        created = service.create_album(album)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Album.model_validate(created)
```

3. **GraphQL resolvers**

   * Remplacer toute logique métier par appels aux services.
   * Regarder dans le dossier 'backend.api.graphql.strrtawchemy_exemple' pour voir comment utiliser correctemnt cette librairie

```python
# graphql/resolvers/album_resolver.py
from backend.services.album_service import AlbumService

def resolve_album(parent, info, id: int):
    db = info.context["db"]
    return AlbumService(db).get_album(id)
```

4. **Nommage et méthodes attendues (minimum)**

* `AlbumService`:

  * `search_albums(title=None, artist_id=None, musicbrainz_albumid=None, musicbrainz_albumartistid=None)`
  * `create_album(album_create: AlbumCreate)`
  * `create_albums_batch(albums: list[AlbumCreate])`
  * `get_albums(skip=0, limit=100)`
  * `get_album(album_id)`
  * `get_albums_by_artist(artist_id)`
  * `update_album(album_id, album_update: AlbumUpdate)`
  * `delete_album(album_id)`
  * `get_album_tracks(album_id)`

* `ArtistService`:

  * `search_artists(name=None, musicbrainz_artistid=None, genre=None)`
  * `create_artist(artist_create: ArtistCreate)`
  * `create_artists_batch(artists: list[ArtistCreate])`
  * `get_artists_paginated(skip, limit)`
  * `get_artist(artist_id)`
  * `update_artist(artist_id, artist_update: ArtistCreate)`
  * `delete_artist(artist_id)`

* `AnalysisService`:

  * `get_pending_tracks()`
  * `process_pending_tracks()`
  * `process_analysis_results()`
  * `update_features(track_id, features)`

5. **Transactions & intégrité**

   * Toutes les opérations d'écriture dans un service doivent **committer** ou **rollback** proprement et logger les erreurs.
   * Gérer les `IntegrityError` et, quand pertinent, renvoyer l'entité existante plutôt qu'une erreur (pattern présent dans le code actuel).

6. **Sérialisation**

   * Les services retournent des instances `Model` SQLAlchemy ou dicts compatibles. Les routers s'occupent de convertir en `Pydantic` via `Schema.model_validate(...)`.

7. **Logging**

   * Conserver/centraliser les logs dans la couche `services` (utiliser `backend.utils.logging.logger`).

8. **Tests**

   * Ne pas modifier les tests (si présents) inutilement. Préserver les contrats d'API (routes et schémas) — la surface REST ne doit pas changer.

---

## Exemples avant/après (concrets)

### Endpoint `POST /api/albums/` (création simple)

**Avant** (dans router)

```python
@router.post("/", response_model=Album)
def create_album(album: AlbumCreate, db: Session = Depends(get_db)):
    existing = db.query(AlbumModel).filter(...).first()
    if existing:
        return Album.model_validate(existing)
    db_album = AlbumModel(...)
    db.add(db_album); db.commit(); db.refresh(db_album)
    return Album.model_validate(db_album)
```

**Après**

```python
# services/album_service.py
class AlbumService:
    def create_album(self, album_create: AlbumCreate) -> AlbumModel:
        # ... logique extraite ici ...
        return db_album

# routers/albums_api.py
@router.post("/", response_model=Album)
def create_album(album: AlbumCreate, db=Depends(get_db)):
    service = AlbumService(db)
    created = service.create_album(album)
    return Album.model_validate(created)
```

### Endpoint `GET /api/albums/{album_id}` (lecture avec covers)

* Extraire la logique de `joinedload`, de constructions de `Cover` et de fallback dates dans le service `get_album(album_id)`.
* Retourner soit un `AlbumModel` enrichi, soit un dict prêt à être validé par `AlbumWithRelations`.

---

## Checklist pour l’exécution (pour Copilot)

1. Créer `backend/services/` si inexistant.
2. Générer `album_service.py`, `artist_service.py`, `analysis_service.py` avec les signatures listées et implémenter la logique extraite depuis `albums_api.py`, `artists_api.py`, `analysis_api.py`.
3. Adapter les routers existants pour appeler les services.
4. Adapter les resolvers GraphQL pour appeler les mêmes services.
5. Ne pas modifier les endpoints externes (routes et schémas restent inchangés).
6. Lancer une passe de recherche/replace pour supprimer les appels DB directs dans les routers et remplacer par `service = XService(db)` + `service.method(...)`.
7. Ajouter/importer `logger` et gestion d'erreurs dans les services.

---

## Contraintes / Interdits

* **Ne pas** : modifier les schémas Pydantic existants sans raison explicite.
* **Ne pas** : supprimer ou renommer les routes publiques.
* **Ne pas** : fusionner plusieurs services en un seul (1 service = 1 domaine logique).

---




