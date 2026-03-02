# Migration GraphQL → Vues Supabase

Ce document explique comment remplacer les requêtes GraphQL complexes par des vues PostgreSQL côté Supabase.

## Vue d'ensemble

Les vues PostgreSQL permettent de pré-calculer des jointures complexes et de retourner des données agrégées en une seule requête, remplaçant ainsi l'avantage principal de GraphQL.

## Vues disponibles

### 1. `artist_detail` - Détail artiste avec albums

**Remplace :**
```graphql
query {
    artist(id: 1) {
        id
        name
        bio
        imageUrl
        albums {
            id
            title
            year
            coverUrl
        }
    }
}
```

**Par :**
```python
from frontend.services import get_graphql_replacement_service

service = get_graphql_replacement_service()
artist = await service.get_artist_detail(1)
# Retourne: {id, name, bio, album_count, track_count, albums: [...]}
```

**Structure de la vue :**
```sql
CREATE VIEW artist_detail AS
SELECT 
    a.id,
    a.name,
    a.bio,
    a.image_url,
    a.date_added,
    a.date_modified,
    COALESCE(album_stats.album_count, 0) as album_count,
    COALESCE(track_stats.track_count, 0) as track_count,
    COALESCE(album_stats.albums_json, '[]'::jsonb) as albums
FROM artists a
LEFT JOIN (...) album_stats ON a.id = album_stats.artist_id
LEFT JOIN (...) track_stats ON a.id = track_stats.artist_id;
```

### 2. `album_detail` - Détail album avec pistes

**Remplace :**
```graphql
query {
    album(id: 1) {
        id
        title
        year
        coverUrl
        artist { id, name }
        tracks {
            id
            title
            trackNumber
            duration
        }
    }
}
```

**Par :**
```python
album = await service.get_album_detail(1)
# Retourne: {id, title, year, artist: {...}, tracks: [...], track_count}
```

### 3. `track_detail` - Détail piste avec artiste et album

**Remplace :**
```graphql
query {
    track(id: 1) {
        id
        title
        trackNumber
        duration
        artist { id, name }
        album { id, title, coverUrl }
    }
}
```

**Par :**
```python
track = await service.get_track_detail(1)
# Retourne: {id, title, artist: {...}, album: {...}}
```

### 4. `library_stats` - Statistiques globales

**Remplace :**
```graphql
query {
    stats {
        artistCount
        albumCount
        trackCount
        totalDuration
    }
}
```

**Par :**
```python
stats = await service.get_library_stats()
# Retourne: {artist_count, album_count, track_count, total_duration_seconds}
```

### 5. `recent_activity` - Activité récente

**Remplace :**
```graphql
query {
    recentTracks(limit: 20) {
        id
        title
        artist { id, name }
        album { id, title, coverUrl }
    }
}
```

**Par :**
```python
recent = await service.get_recent_activity(limit=20)
# Retourne: [{track_id, track_title, artist: {...}, album: {...}}]
```

### 6. `search_all` - Recherche unifiée

**Remplace :**
```graphql
query {
    search(query: "beatles") {
        artists { ... }
        albums { ... }
        tracks { ... }
    }
}
```

**Par :**
```python
results = await service.search_all("beatles", types=['artist', 'album', 'track'])
# Retourne: {artists: [...], albums: [...], tracks: [...]}
```

## Avantages des vues PostgreSQL

| Aspect | GraphQL | Vues PostgreSQL |
|--------|---------|-----------------|
| **Performance** | N+1 queries possible | Jointures optimisées côté DB |
| **Complexité** | Resolvers, schémas, types | SQL simple et maintenable |
| **Caching** | Complexe (DataLoader) | PostgreSQL gère automatiquement |
| **Type safety** | Forte (schéma) | Pydantic côté Python |
| **Flexibilité** | Très flexible | Suffisant pour la plupart des cas |

## Migration progressive

### Étape 1 : Créer les vues (fait)
```bash
alembic upgrade add_supabase_views
```

### Étape 2 : Utiliser GraphQLReplacementService
```python
from frontend.services import get_graphql_replacement_service

# Remplace l'appel GraphQL
service = get_graphql_replacement_service()
artist_detail = await service.get_artist_detail(artist_id)
```

### Étape 3 : Adapter les composants UI
```python
# Avant (GraphQL)
async def load_artist_graphql(artist_id):
    query = """
    query($id: Int!) {
        artist(id: $id) { ... }
    }
    """
    return await graphql_client.execute(query, variables={"id": artist_id})

# Après (Supabase views)
async def load_artist_supabase(artist_id):
    from frontend.services import get_graphql_replacement_service
    service = get_graphql_replacement_service()
    return await service.get_artist_detail(artist_id)
```

## Performance

Les vues sont matérialisées à l'exécution avec les index suivants :
- `idx_tracks_artist_id`
- `idx_tracks_album_id`
- `idx_albums_artist_id`

Pour des performances optimales sur de grandes bibliothèques, envisager des **vues matérialisées** (MATERIALIZED VIEW) avec rafraîchissement périodique.

## Exemple complet : Page Artiste

```python
from frontend.services import get_graphql_replacement_service
from frontend.utils.supabase_realtime import get_supabase_realtime_client

class ArtistPage:
    def __init__(self):
        self.graphql_service = get_graphql_replacement_service()
        self.realtime = get_supabase_realtime_client()
    
    async def load_artist(self, artist_id: int):
        # Récupération initiale via vue
        artist = await self.graphql_service.get_artist_detail(artist_id)
        
        # Souscription temps réel pour les mises à jour
        await self.realtime.subscribe(
            f"artist:{artist_id}",
            self.on_artist_update
        )
        
        return artist
    
    def on_artist_update(self, payload):
        # Mise à jour en temps réel
        print(f"Artiste mis à jour: {payload}")
```

## Dépannage

### Problème : Les données JSONB ne sont pas parsées
**Solution :** Le service `GraphQLReplacementService` gère automatiquement la conversion JSONB → Python.

### Problème : Performances lentes sur grandes bibliothèques
**Solution :** 
1. Ajouter des index supplémentaires si nécessaire
2. Envisager des vues matérialisées pour les stats
3. Paginer les résultats (déjà implémenté)

### Problème : Besoin de données supplémentaires
**Solution :** Étendre la vue SQL ou créer une nouvelle vue spécifique.
