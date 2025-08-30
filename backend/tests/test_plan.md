# Plan de Test pour SoniqueBay Backend

Ce document présente le plan de test complet pour le backend de SoniqueBay, couvrant les tests des endpoints REST, des requêtes GraphQL et des insertions en base de données.

## Table des matières

1. [Analyse du projet](#1-analyse-du-projet)
2. [Outils et frameworks de test](#2-outils-et-frameworks-de-test)
3. [Structure des fichiers de test](#3-structure-des-fichiers-de-test)
4. [Tests des endpoints REST](#4-tests-des-endpoints-rest)
5. [Tests des requêtes GraphQL](#5-tests-des-requêtes-graphql)
6. [Tests d'insertion en base de données](#6-tests-dinsertion-en-base-de-données)
7. [Fixtures et données de test](#7-fixtures-et-données-de-test)
8. [Tests d'intégration](#8-tests-dintégration)
9. [Stratégie d'exécution des tests](#9-stratégie-dexécution-des-tests)

## 1. Analyse du projet

### Structure générale
- Application backend FastAPI avec endpoints REST et GraphQL
- Utilisation de SQLAlchemy comme ORM pour la gestion de la base de données
- Strawberry pour l'implémentation GraphQL
- Architecture modulaire avec séparation des modèles, schémas, routeurs et services

### Composants principaux
1. **API REST** avec plusieurs endpoints:
   - Tracks API: gestion des pistes musicales (CRUD, recherche, filtrage)
   - Albums API, Artists API, etc.
   - Endpoints spécialisés (search, library, playqueue, etc.)

2. **API GraphQL** avec:
   - Requêtes (Query) pour récupérer des données (tracks, albums, artists)
   - Mutations pour modifier des données (create, update, upsert)
   - Types définis pour chaque entité

3. **Modèles de données** principaux:
   - Track: pistes musicales avec métadonnées et caractéristiques audio
   - Album, Artist, Genre, Cover, etc.
   - Relations complexes entre les entités (many-to-many, one-to-many)

4. **Fonctionnalités spécifiques**:
   - Gestion des tags (genre_tags, mood_tags)
   - Métadonnées musicales (BPM, key, scale, etc.)
   - Intégration avec des services externes (MusicBrainz, AcoustID)

## 2. Outils et frameworks de test

### Frameworks de test principaux

1. **pytest**
   - Framework de test principal pour Python
   - Support des fixtures, paramétrage et organisation modulaire des tests
   - Intégration avec d'autres outils de test

2. **pytest-asyncio**
   - Extension pour tester les fonctions asynchrones
   - Essentiel pour tester les endpoints FastAPI qui sont asynchrones

### Outils spécifiques pour les tests d'API

1. **TestClient de FastAPI**
   - Client de test intégré à FastAPI
   - Permet de simuler des requêtes HTTP sans serveur réel
   - Idéal pour tester les endpoints REST

2. **httpx**
   - Client HTTP asynchrone
   - Utile pour tester les requêtes HTTP complexes

3. **Strawberry Test Client**
   - Utilitaires de test pour les API GraphQL avec Strawberry
   - Permet de tester les requêtes et mutations GraphQL directement

### Outils pour les tests de base de données

1. **SQLAlchemy avec SQLite en mémoire**
   - Utilisation d'une base de données SQLite en mémoire pour les tests
   - Isolation complète entre les tests
   - Performances optimales pour les tests unitaires

2. **Alembic**
   - Gestion des migrations de base de données pour les tests
   - Permet de créer un schéma de base de données cohérent pour les tests

### Outils pour les mocks et fixtures

1. **pytest-mock**
   - Extension pour faciliter la création de mocks dans pytest
   - Utile pour isoler les composants et simuler des comportements

2. **Factory Boy**
   - Bibliothèque pour créer des objets de test (fixtures)
   - Permet de générer facilement des données de test cohérentes

### Outils d'analyse de couverture

1. **pytest-cov**
   - Extension pour mesurer la couverture de code des tests
   - Génère des rapports détaillés sur les parties du code testées

## 3. Structure des fichiers de test

```
backend/tests/
├── conftest.py                  # Fixtures partagées
├── test_api/                    # Tests des endpoints REST
│   ├── test_tracks_api.py
│   ├── test_albums_api.py
│   ├── test_artists_api.py
│   ├── test_genres_api.py
│   ├── test_covers_api.py
│   ├── test_tags_api.py
│   ├── test_search_api.py
│   ├── test_library_api.py
│   ├── test_playqueue_api.py
│   ├── test_scan_api.py
│   ├── test_settings_api.py
│   └── test_analysis_api.py
├── test_graphql/                # Tests GraphQL
│   ├── test_artist_queries.py
│   ├── test_artist_mutations.py
│   ├── test_album_queries.py
│   ├── test_album_mutations.py
│   ├── test_track_queries.py
│   ├── test_track_mutations.py
│   ├── test_genre_queries.py
│   ├── test_tag_queries.py
│   └── test_cover_queries.py
├── test_models/                 # Tests des modèles et insertions BDD
│   ├── test_tracks_model.py
│   ├── test_albums_model.py
│   ├── test_artists_model.py
│   ├── test_genres_model.py
│   ├── test_covers_model.py
│   ├── test_tags_model.py
│   └── test_relations.py
└── test_integration/            # Tests d'intégration
    ├── test_api_db.py
    ├── test_rest_graphql.py
    └── test_full_workflow.py
```

### Fichier conftest.py

Le fichier `conftest.py` contiendra les fixtures partagées par tous les tests:

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.utils.database import Base, get_db
from backend.api_app import create_api
import os
import tempfile
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track
from backend.api.models.genres_model import Genre
from backend.api.models.covers_model import Cover
from backend.api.models.tags_model import GenreTag, MoodTag

# Base de données SQLite en mémoire pour les tests
@pytest.fixture(scope="session")
def test_db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(test_db_engine):
    """Session de base de données pour les tests."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(db_session):
    """Client de test FastAPI avec une base de données de test."""
    app = create_api()
    
    # Override de la dépendance get_db pour utiliser notre session de test
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client

# Fixtures pour créer des données de test

@pytest.fixture
def create_test_artist(db_session):
    """Crée un artiste de test."""
    def _create_artist(name="Test Artist", musicbrainz_artistid=None):
        artist = Artist(name=name, musicbrainz_artistid=musicbrainz_artistid)
        db_session.add(artist)
        db_session.commit()
        return artist
    return _create_artist

@pytest.fixture
def create_test_artists(db_session):
    """Crée plusieurs artistes de test."""
    def _create_artists(count=3):
        artists = []
        for i in range(count):
            artist = Artist(name=f"Test Artist {i}", musicbrainz_artistid=f"test-mb-id-{i}")
            db_session.add(artist)
            artists.append(artist)
        db_session.commit()
        return artists
    return _create_artists

@pytest.fixture
def create_test_album(db_session):
    """Crée un album de test."""
    def _create_album(title="Test Album", artist_id=None, musicbrainz_albumid=None):
        album = Album(title=title, artist_id=artist_id, musicbrainz_albumid=musicbrainz_albumid)
        db_session.add(album)
        db_session.commit()
        return album
    return _create_album

@pytest.fixture
def create_test_albums(db_session):
    """Crée plusieurs albums de test."""
    def _create_albums(count=3, artist_id=None):
        albums = []
        for i in range(count):
            album = Album(title=f"Test Album {i}", artist_id=artist_id, musicbrainz_albumid=f"test-mb-album-id-{i}")
            db_session.add(album)
            albums.append(album)
        db_session.commit()
        return albums
    return _create_albums

@pytest.fixture
def create_test_track(db_session, create_test_artist):
    """Crée une piste de test."""
    def _create_track(title="Test Track", path="/path/to/test.mp3", artist_id=None, album_id=None, **kwargs):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id
        
        track_data = {
            "title": title,
            "path": path,
            "track_artist_id": artist_id,
            "album_id": album_id,
            **kwargs
        }
        
        track = Track(**track_data)
        db_session.add(track)
        db_session.commit()
        return track
    return _create_track

@pytest.fixture
def create_test_tracks(db_session, create_test_artist):
    """Crée plusieurs pistes de test."""
    def _create_tracks(count=3, artist_id=None, album_id=None):
        if artist_id is None:
            artist = create_test_artist()
            artist_id = artist.id
        
        tracks = []
        for i in range(count):
            track = Track(
                title=f"Test Track {i}",
                path=f"/path/to/test{i}.mp3",
                track_artist_id=artist_id,
                album_id=album_id
            )
            db_session.add(track)
            tracks.append(track)
        
        db_session.commit()
        return tracks
    return _create_tracks

@pytest.fixture
def create_test_album_with_artist(db_session, create_test_artist):
    """Crée un album avec son artiste."""
    def _create_album_with_artist():
        artist = create_test_artist()
        album = Album(title="Test Album", artist_id=artist.id)
        db_session.add(album)
        db_session.commit()
        return album, artist
    return _create_album_with_artist

@pytest.fixture
def create_test_track_with_relations(db_session, create_test_artist, create_test_album):
    """Crée une piste avec artiste et album."""
    def _create_track_with_relations():
        artist = create_test_artist()
        album = create_test_album(artist_id=artist.id)
        
        track = Track(
            title="Test Track with Relations",
            path="/path/to/relations_test.mp3",
            track_artist_id=artist.id,
            album_id=album.id
        )
        db_session.add(track)
        db_session.commit()
        
        return track, artist, album
    return _create_track_with_relations

@pytest.fixture
def create_test_artist_with_tracks(db_session, create_test_artist, create_test_tracks):
    """Crée un artiste avec plusieurs pistes."""
    def _create_artist_with_tracks(track_count=3):
        artist = create_test_artist()
        tracks = create_test_tracks(count=track_count, artist_id=artist.id)
        return artist, tracks
    return _create_artist_with_tracks

@pytest.fixture
def create_test_artist_album_tracks(db_session, create_test_artist, create_test_album, create_test_tracks):
    """Crée un artiste, un album et des pistes associées."""
    def _create_artist_album_tracks(track_count=3):
        artist = create_test_artist()
        album = create_test_album(artist_id=artist.id)
        tracks = create_test_tracks(count=track_count, artist_id=artist.id, album_id=album.id)
        return artist, album, tracks
    return _create_artist_album_tracks

@pytest.fixture
def create_test_tracks_with_metadata(db_session, create_test_artist, create_test_album):
    """Crée des pistes avec des métadonnées variées."""
    def _create_tracks_with_metadata():
        artist = create_test_artist()
        album = create_test_album(artist_id=artist.id)
        
        tracks = []
        # Piste Rock
        track1 = Track(
            title="Test Rock Track",
            path="/path/to/rock.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Rock",
            year="2023",
            bpm=120.5,
            key="C",
            scale="major"
        )
        db_session.add(track1)
        tracks.append(track1)
        
        # Piste Jazz
        track2 = Track(
            title="Test Jazz Track",
            path="/path/to/jazz.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Jazz",
            year="2022",
            bpm=90.0,
            key="D",
            scale="minor"
        )
        db_session.add(track2)
        tracks.append(track2)
        
        # Piste Electronic
        track3 = Track(
            title="Test Electronic Track",
            path="/path/to/electronic.mp3",
            track_artist_id=artist.id,
            album_id=album.id,
            genre="Electronic",
            year="2023",
            bpm=128.0,
            key="A",
            scale="minor"
        )
        db_session.add(track3)
        tracks.append(track3)
        
        db_session.commit()
        return tracks
    return _create_tracks_with_metadata

@pytest.fixture
def create_test_track_with_tags(db_session, create_test_track):
    """Crée une piste avec des tags."""
    def _create_track_with_tags():
        track = create_test_track()
        
        # Ajouter des genre_tags
        genre_tags = [
            GenreTag(name="rock"),
            GenreTag(name="indie"),
            GenreTag(name="alternative")
        ]
        for tag in genre_tags:
            db_session.add(tag)
        
        # Ajouter des mood_tags
        mood_tags = [
            MoodTag(name="happy"),
            MoodTag(name="energetic"),
            MoodTag(name="upbeat")
        ]
        for tag in mood_tags:
            db_session.add(tag)
        
        db_session.commit()
        
        # Associer les tags à la piste
        track.genre_tags = genre_tags
        track.mood_tags = mood_tags
        db_session.commit()
        
        return track
    return _create_track_with_tags
```

## 4. Tests des endpoints REST

### Endpoints Tracks API à tester

1. GET `/api/tracks/` - Récupération de la liste des pistes
2. GET `/api/tracks/{track_id}` - Récupération d'une piste par ID
3. GET `/api/tracks/search` - Recherche de pistes avec filtres
4. POST `/api/tracks/` - Création d'une piste
5. POST `/api/tracks/batch` - Création/mise à jour en batch
6. PUT `/api/tracks/{track_id}` - Mise à jour d'une piste
7. PUT `/api/tracks/{track_id}/tags` - Mise à jour des tags d'une piste
8. DELETE `/api/tracks/{track_id}` - Suppression d'une piste
9. GET `/api/tracks/artists/{artist_id}` - Récupération des pistes d'un artiste
10. GET `/api/tracks/artists/{artist_id}/albums/{album_id}` - Récupération des pistes d'un artiste pour un album

### Exemple de tests pour Tracks API

```python
# backend/tests/test_api/test_tracks_api.py

def test_get_tracks_empty(client, db_session):
    """Test de récupération d'une liste vide de pistes."""
    response = client.get("/api/tracks/")
    assert response.status_code == 200
    assert response.json() == []

def test_get_tracks_with_data(client, db_session, create_test_tracks):
    """Test de récupération d'une liste de pistes avec données."""
    tracks = create_test_tracks(5)  # Crée 5 pistes de test
    
    response = client.get("/api/tracks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    
    # Vérifier que les données correspondent
    track_ids = [track["id"] for track in data]
    for track in tracks:
        assert track.id in track_ids

def test_get_track_by_id_exists(client, db_session, create_test_track):
    """Test de récupération d'une piste existante par ID."""
    track = create_test_track()  # Crée une piste de test
    
    response = client.get(f"/api/tracks/{track.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == track.id
    assert data["title"] == track.title
    assert data["path"] == track.path

def test_create_track_minimal(client, db_session, create_test_artist):
    """Test de création d'une piste avec données minimales."""
    artist = create_test_artist()
    
    track_data = {
        "title": "Minimal Track",
        "path": "/path/to/minimal.mp3",
        "track_artist_id": artist.id
    }
    
    response = client.post("/api/tracks/", json=track_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Minimal Track"
    assert data["path"] == "/path/to/minimal.mp3"
    assert data["track_artist_id"] == artist.id
    
    # Vérifier que la piste a bien été créée en BDD
    db_track = db_session.query(Track).filter(Track.id == data["id"]).first()
    assert db_track is not None
    assert db_track.title == "Minimal Track"

def test_update_track_basic(client, db_session, create_test_track):
    """Test de mise à jour basique d'une piste."""
    track = create_test_track(title="Original Title")
    
    update_data = {
        "title": "Updated Title"
    }
    
    response = client.put(f"/api/tracks/{track.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == track.id
    assert data["title"] == "Updated Title"
    
    # Vérifier que la piste a bien été mise à jour en BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track.title == "Updated Title"

def test_delete_track(client, db_session, create_test_track):
    """Test de suppression d'une piste."""
    track = create_test_track()
    
    response = client.delete(f"/api/tracks/{track.id}")
    assert response.status_code == 204
    
    # Vérifier que la piste a bien été supprimée
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track is None
```

### Tests similaires pour les autres endpoints REST

Les autres fichiers de test REST suivront la même structure, adaptée à chaque type d'entité (albums, artists, genres, etc.).

## 5. Tests des requêtes GraphQL

### Requêtes GraphQL à tester

1. Requêtes (Queries):
   - `artist` / `artists` - Récupération d'artistes
   - `album` / `albums` - Récupération d'albums
   - `track` / `tracks` - Récupération de pistes

2. Mutations:
   - `create_artist` / `create_artists` - Création d'artistes
   - `update_artist_by_id` / `update_artists` - Mise à jour d'artistes
   - `upsert_artist` / `upsert_artists` - Insertion ou mise à jour d'artistes
   - `create_album` / `create_albums` - Création d'albums
   - `update_album_by_id` / `update_albums` - Mise à jour d'albums
   - `upsert_album` / `upsert_albums` - Insertion ou mise à jour d'albums
   - `create_track` / `create_tracks` - Création de pistes
   - `update_track_by_id` / `update_tracks` - Mise à jour de pistes
   - `upsert_track` - Insertion ou mise à jour d'une piste

### Exemple de tests pour les requêtes d'artistes

```python
# backend/tests/test_graphql/test_artist_queries.py

def test_get_artists_query(client, db_session, create_test_artists):
    """Test de récupération de la liste des artistes via GraphQL."""
    # Créer des artistes de test
    artists = create_test_artists(3)
    
    query = """
    query {
        artists {
            id
            name
            musicbrainz_artistid
        }
    }
    """
    
    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "artists" in data["data"]
    assert isinstance(data["data"]["artists"], list)
    assert len(data["data"]["artists"]) >= 3  # Au moins les 3 artistes créés
    
    # Vérifier que nos artistes sont bien présents
    artist_ids = [str(artist.id) for artist in artists]
    response_ids = [artist["id"] for artist in data["data"]["artists"]]
    for artist_id in artist_ids:
        assert artist_id in response_ids

def test_get_artist_by_id_query(client, db_session, create_test_artist):
    """Test de récupération d'un artiste par ID via GraphQL."""
    # Créer un artiste de test
    artist = create_test_artist(name="Test Artist", musicbrainz_artistid="test-mb-id")
    
    query = f"""
    query {{
        artist(id: {artist.id}) {{
            id
            name
            musicbrainz_artistid
        }}
    }}
    """
    
    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "artist" in data["data"]
    assert data["data"]["artist"]["id"] == str(artist.id)
    assert data["data"]["artist"]["name"] == "Test Artist"
    assert data["data"]["artist"]["musicbrainz_artistid"] == "test-mb-id"
```

### Exemple de tests pour les mutations d'artistes

```python
# backend/tests/test_graphql/test_artist_mutations.py

def test_create_artist_mutation(client, db_session):
    """Test de création d'un artiste via GraphQL."""
    mutation = """
    mutation {
        create_artist(input: {
            name: "GraphQL Artist",
            musicbrainz_artistid: "graphql-artist-id"
        }) {
            id
            name
            musicbrainz_artistid
        }
    }
    """
    
    response = client.post("/api/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "create_artist" in data["data"]
    assert data["data"]["create_artist"]["name"] == "GraphQL Artist"
    assert data["data"]["create_artist"]["musicbrainz_artistid"] == "graphql-artist-id"
    
    # Vérifier que l'artiste a bien été créé en BDD
    artist_id = data["data"]["create_artist"]["id"]
    db_artist = db_session.query(Artist).filter(Artist.id == int(artist_id)).first()
    assert db_artist is not None
    assert db_artist.name == "GraphQL Artist"

def test_update_artist_by_id_mutation(client, db_session, create_test_artist):
    """Test de mise à jour d'un artiste par ID via GraphQL."""
    # Créer un artiste de test
    artist = create_test_artist(name="Original Name")
    
    mutation = f"""
    mutation {{
        update_artist_by_id(input: {{
            id: {artist.id},
            name: "Updated Name",
            musicbrainz_artistid: "updated-mb-id"
        }}) {{
            id
            name
            musicbrainz_artistid
        }}
    }}
    """
    
    response = client.post("/api/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "update_artist_by_id" in data["data"]
    assert data["data"]["update_artist_by_id"]["id"] == str(artist.id)
    assert data["data"]["update_artist_by_id"]["name"] == "Updated Name"
    assert data["data"]["update_artist_by_id"]["musicbrainz_artistid"] == "updated-mb-id"
    
    # Vérifier que l'artiste a bien été mis à jour en BDD
    db_artist = db_session.query(Artist).filter(Artist.id == artist.id).first()
    assert db_artist.name == "Updated Name"
    assert db_artist.musicbrainz_artistid == "updated-mb-id"
```

## 6. Tests d'insertion en base de données

### Modèles à tester

1. Track
2. Album
3. Artist
4. Genre
5. Cover
6. Tags (GenreTag, MoodTag)
7. Relations entre modèles

### Exemple de tests pour le modèle Track

```python
# backend/tests/test_models/test_tracks_model.py

def test_create_track(db_session):
    """Test de création d'une piste en BDD."""
    # Créer d'abord un artiste et un album
    artist = Artist(name="Test Artist")
    db_session.add(artist)
    db_session.flush()
    
    album = Album(title="Test Album", artist_id=artist.id)
    db_session.add(album)
    db_session.flush()
    
    # Créer une piste
    track = Track(
        title="Test Track",
        path="/path/to/test.mp3",
        track_artist_id=artist.id,
        album_id=album.id,
        duration=180,
        track_number="1",
        disc_number="1",
        year="2023",
        genre="Rock"
    )
    db_session.add(track)
    db_session.commit()
    
    # Vérifier que la piste a été créée
    assert track.id is not None
    
    # Récupérer la piste depuis la BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track is not None
    assert db_track.title == "Test Track"
    assert db_track.path == "/path/to/test.mp3"
    assert db_track.track_artist_id == artist.id
    assert db_track.album_id == album.id

def test_track_unique_path_constraint(db_session):
    """Test de la contrainte d'unicité sur le chemin de la piste."""
    # Créer un artiste
    artist = Artist(name="Test Artist 2")
    db_session.add(artist)
    db_session.flush()
    
    # Créer une première piste
    track1 = Track(
        title="Track 1",
        path="/path/to/duplicate.mp3",
        track_artist_id=artist.id
    )
    db_session.add(track1)
    db_session.commit()
    
    # Tenter de créer une seconde piste avec le même chemin
    track2 = Track(
        title="Track 2",
        path="/path/to/duplicate.mp3",
        track_artist_id=artist.id
    )
    db_session.add(track2)
    
    # Vérifier que la contrainte d'unicité est respectée
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    # Rollback pour nettoyer la session
    db_session.rollback()

def test_track_relationships(db_session):
    """Test des relations entre les modèles."""
# Créer un artiste
    artist = Artist(name="Relationship Test Artist")
    db_session.add(artist)
    db_session.flush()
    
    # Créer un album
    album = Album(title="Relationship Test Album", artist_id=artist.id)
    db_session.add(album)
    db_session.flush()
    
    # Créer une piste
    track = Track(
        title="Relationship Test Track",
        path="/path/to/relationship_test.mp3",
        track_artist_id=artist.id,
        album_id=album.id
    )
    db_session.add(track)
    db_session.commit()
    
    # Vérifier les relations
    assert track.artist.id == artist.id
    assert track.artist.name == "Relationship Test Artist"
    assert track.album.id == album.id
    assert track.album.title == "Relationship Test Album"
    
    # Vérifier les relations inverses
    assert track in artist.tracks
    assert track in album.tracks
```

## 7. Fixtures et données de test

Les fixtures sont définies dans le fichier `conftest.py` et permettent de créer facilement des données de test pour les différents scénarios. Voici les principales fixtures disponibles:

1. **Fixtures de base de données**:
   - `test_db_engine`: Crée un moteur SQLAlchemy avec une base de données SQLite en mémoire
   - `db_session`: Fournit une session de base de données pour les tests

2. **Fixtures d'API**:
   - `client`: Client de test FastAPI avec une base de données de test

3. **Fixtures de création d'entités**:
   - `create_test_artist` / `create_test_artists`: Création d'artistes
   - `create_test_album` / `create_test_albums`: Création d'albums
   - `create_test_track` / `create_test_tracks`: Création de pistes
   - `create_test_album_with_artist`: Création d'un album avec son artiste
   - `create_test_track_with_relations`: Création d'une piste avec artiste et album
   - `create_test_artist_with_tracks`: Création d'un artiste avec plusieurs pistes
   - `create_test_artist_album_tracks`: Création d'un artiste, un album et des pistes associées
   - `create_test_tracks_with_metadata`: Création de pistes avec des métadonnées variées
   - `create_test_track_with_tags`: Création d'une piste avec des tags

Ces fixtures permettent de simplifier la création de données de test et d'éviter la duplication de code dans les tests.

## 8. Tests d'intégration

Les tests d'intégration vérifient que les différentes parties du système fonctionnent correctement ensemble. Voici quelques exemples de tests d'intégration:

### Test d'intégration API REST et base de données

```python
# backend/tests/test_integration/test_api_db.py

def test_create_and_retrieve_track(client, db_session, create_test_artist, create_test_album):
    """Test d'intégration: création d'une piste via API et récupération depuis la BDD."""
    # Créer un artiste et un album
    artist = create_test_artist()
    album = create_test_album(artist_id=artist.id)
    
    # Créer une piste via l'API REST
    track_data = {
        "title": "Integration Test Track",
        "path": "/path/to/integration_test.mp3",
        "track_artist_id": artist.id,
        "album_id": album.id,
        "duration": 240
    }
    response = client.post("/api/tracks/", json=track_data)
    assert response.status_code == 200
    track_id = response.json()["id"]
    
    # Récupérer la piste directement depuis la BDD
    db_track = db_session.query(Track).filter(Track.id == track_id).first()
    assert db_track is not None
    assert db_track.title == "Integration Test Track"
    assert db_track.path == "/path/to/integration_test.mp3"
    assert db_track.track_artist_id == artist.id
    assert db_track.album_id == album.id
    assert db_track.duration == 240
```

### Test d'intégration API REST et GraphQL

```python
# backend/tests/test_integration/test_rest_graphql.py

def test_create_track_rest_query_graphql(client, db_session, create_test_artist, create_test_album):
    """Test d'intégration: création d'une piste via REST et requête via GraphQL."""
    # Créer un artiste et un album via l'API REST
    artist_data = {"name": "Integration Test Artist"}
    artist_response = client.post("/api/artists/", json=artist_data)
    artist_id = artist_response.json()["id"]
    
    album_data = {"title": "Integration Test Album", "artist_id": artist_id}
    album_response = client.post("/api/albums/", json=album_data)
    album_id = album_response.json()["id"]
    
    # Créer une piste via l'API REST
    track_data = {
        "title": "Integration Test Track",
        "path": "/path/to/integration_test.mp3",
        "track_artist_id": artist_id,
        "album_id": album_id,
        "duration": 240
    }
    track_response = client.post("/api/tracks/", json=track_data)
    assert track_response.status_code == 200
    track_id = track_response.json()["id"]
    
    # Requête GraphQL pour récupérer la piste avec ses relations
    query = f"""
    query {{
        track(id: {track_id}) {{
            id
            title
            path
            duration
            artist {{
                id
                name
            }}
            album {{
                id
                title
            }}
        }}
    }}
    """
    graphql_response = client.post("/api/graphql", json={"query": query})
    assert graphql_response.status_code == 200
    data = graphql_response.json()["data"]["track"]
    
    # Vérifier les données
    assert data["id"] == str(track_id)
    assert data["title"] == "Integration Test Track"
    assert data["artist"]["id"] == str(artist_id)
    assert data["artist"]["name"] == "Integration Test Artist"
    assert data["album"]["id"] == str(album_id)
    assert data["album"]["title"] == "Integration Test Album"
```

### Test de flux de travail complet

```python
# backend/tests/test_integration/test_full_workflow.py

def test_full_music_workflow(client, db_session):
    """Test d'intégration: flux de travail complet de gestion de musique."""
    # 1. Créer un artiste
    artist_data = {"name": "Workflow Test Artist"}
    artist_response = client.post("/api/artists/", json=artist_data)
    assert artist_response.status_code == 200
    artist_id = artist_response.json()["id"]
    
    # 2. Créer un album pour cet artiste
    album_data = {
        "title": "Workflow Test Album",
        "artist_id": artist_id,
        "year": "2023"
    }
    album_response = client.post("/api/albums/", json=album_data)
    assert album_response.status_code == 200
    album_id = album_response.json()["id"]
    
    # 3. Créer plusieurs pistes pour cet album
    tracks_data = [
        {
            "title": "Workflow Track 1",
            "path": "/path/to/workflow1.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "1",
            "duration": 180
        },
        {
            "title": "Workflow Track 2",
            "path": "/path/to/workflow2.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "2",
            "duration": 210
        },
        {
            "title": "Workflow Track 3",
            "path": "/path/to/workflow3.mp3",
            "track_artist_id": artist_id,
            "album_id": album_id,
            "track_number": "3",
            "duration": 240
        }
    ]
    
    track_ids = []
    for track_data in tracks_data:
        track_response = client.post("/api/tracks/", json=track_data)
        assert track_response.status_code == 200
        track_ids.append(track_response.json()["id"])
    
    # 4. Récupérer les pistes de l'album
    album_tracks_response = client.get(f"/api/tracks/artists/{artist_id}/albums/{album_id}")
    assert album_tracks_response.status_code == 200
    album_tracks = album_tracks_response.json()
    assert len(album_tracks) == 3
    
    # 5. Mettre à jour une piste
    update_data = {
        "title": "Updated Workflow Track",
        "genre": "Rock",
        "genre_tags": ["rock", "indie"]
    }
    update_response = client.put(f"/api/tracks/{track_ids[0]}", json=update_data)
    assert update_response.status_code == 200
    updated_track = update_response.json()
    assert updated_track["title"] == "Updated Workflow Track"
    assert updated_track["genre"] == "Rock"
    assert "rock" in updated_track["genre_tags"]
    
    # 6. Rechercher des pistes par genre
    search_response = client.get("/api/tracks/search?genre=Rock")
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert len(search_results) > 0
    assert any(track["id"] == track_ids[0] for track in search_results)
    
    # 7. Supprimer une piste
    delete_response = client.delete(f"/api/tracks/{track_ids[2]}")
    assert delete_response.status_code == 204
    
    # Vérifier que la piste a bien été supprimée
    get_response = client.get(f"/api/tracks/{track_ids[2]}")
    assert get_response.status_code == 404
    
    # 8. Vérifier que l'album n'a plus que 2 pistes
    album_tracks_response = client.get(f"/api/tracks/artists/{artist_id}/albums/{album_id}")
    assert album_tracks_response.status_code == 200
    album_tracks = album_tracks_response.json()
    assert len(album_tracks) == 2
```

## 9. Stratégie d'exécution des tests

### Organisation des tests

Les tests sont organisés en plusieurs catégories:
1. **Tests unitaires**: Tests des modèles et des services individuels
2. **Tests d'API**: Tests des endpoints REST et GraphQL
3. **Tests d'intégration**: Tests des interactions entre les différentes parties du système

### Exécution des tests

Pour exécuter les tests, utilisez la commande pytest avec les options appropriées:

```bash
# Exécuter tous les tests
pytest backend/tests/

# Exécuter les tests avec rapport de couverture
pytest backend/tests/ --cov=backend --cov-report=html

# Exécuter uniquement les tests REST
pytest backend/tests/test_api/

# Exécuter uniquement les tests GraphQL
pytest backend/tests/test_graphql/

# Exécuter uniquement les tests d'intégration
pytest backend/tests/test_integration/
```

### Environnement de test

Les tests utilisent une base de données SQLite en mémoire pour garantir l'isolation et la rapidité d'exécution. Chaque test s'exécute dans un environnement propre, sans interférence avec les autres tests.

### Bonnes pratiques

1. **Isolation des tests**: Chaque test doit être indépendant des autres
2. **Utilisation des fixtures**: Utiliser les fixtures pour préparer l'environnement de test
3. **Tests de cas limites**: Tester les cas d'erreur et les cas limites
4. **Couverture de code**: Viser une couverture de code élevée (>80%)
5. **Tests d'intégration**: Tester les interactions entre les différentes parties du système

### Intégration continue

Les tests peuvent être intégrés dans un pipeline CI/CD pour garantir la qualité du code à chaque modification:

```yaml
# Exemple de configuration GitHub Actions
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r backend/requirements.txt
        pip install pytest pytest-cov
    - name: Test with pytest
      run: |
        pytest backend/tests/ --cov=backend --cov-report=xml
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

Cette stratégie d'exécution des tests garantit que le code est testé de manière complète et cohérente, ce qui permet de détecter rapidement les régressions et les bugs.
    # Créer un art