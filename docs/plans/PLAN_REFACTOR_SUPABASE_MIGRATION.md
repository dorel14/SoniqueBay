"""
Plan de refactorisation pour la migration Supabase - SoniqueBay.

Ce document détaille la stratégie de migration progressive de PostgreSQL/SQLAlchemy
vers Supabase tout en maintenant la compatibilité et en évitant les régressions.

Auteur: SoniqueBay Team
Version: 1.0.0
Date: 2025-01-20
"""

# Plan de Migration Supabase - SoniqueBay

## Vue d'ensemble

**Objectif** : Migrer progressivement de l'architecture PostgreSQL/SQLAlchemy vers Supabase
sans interruption de service et sans régression fonctionnelle.

**Stratégie** : Approche hybride avec feature flags permettant un basculement progressif
et un rollback immédiat si nécessaire.

---

## Architecture Actuelle

```
┌─────────────┐     HTTP      ┌──────────────┐     SQLAlchemy    ┌─────────────┐
│   NiceGUI   │ ◄────────────► │   FastAPI    │ ◄───────────────► │  PostgreSQL │
│  (Frontend) │                │   (Backend)  │                   │   (Local)   │
└─────────────┘                └──────────────┘                   └─────────────┘
                                      │
                                      │ HTTP API
                                      ▼
                               ┌──────────────┐
                               │Celery Workers│
                               │  (No DB)     │
                               └──────────────┘
```

## Architecture Cible

```
┌─────────────┐     Supabase   ┌─────────────┐
│   NiceGUI   │ ◄─────────────► │  Supabase   │
│  (Frontend) │   Client SDK   │  (DB/Auth/  │
└─────────────┘                │  Realtime)  │
                               └──────┬──────┘
                                      │
                                      │ HTTP API
                                      ▼
                               ┌──────────────┐
                               │   FastAPI    │
                               │ (Business    │
                               │  Logic + AI)  │
                               └──────┬──────┘
                                      │
                                      │ HTTP API
                                      ▼
                               ┌──────────────┐
                               │Celery Workers│
                               │  (API only)  │
                               └──────────────┘
```

---

## Phase 1 : Préparation et Configuration (Semaine 1)

### 1.1 Gestion des branches Git

**Actions requises :**
- Fermer la branche `blackboxai/fix-orchestrator-async-init` (si elle existe encore)
- Créer une nouvelle branche dédiée : `blackboxai/feature/supabase-migration-v2`

```powershell
# Commandes PowerShell
git checkout master
git branch -D blackboxai/fix-orchestrator-async-init 2>$null
git checkout -b blackboxai/feature/supabase-migration-v2
git push -u origin blackboxai/feature/supabase-migration-v2
```

### 1.2 Configuration environnement

**Fichiers à créer/modifier :**

1. **`.env.supabase`** (nouveau) :
```bash
# Supabase Configuration
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Feature Flags (permettent basculement progressif)
USE_SUPABASE_DB=false
USE_SUPABASE_AUTH=false
USE_SUPABASE_REALTIME=false
USE_SUPABASE_STORAGE=false

# Database URLs (compatibilité progressive)
# Phase 1-2 : Utiliser PostgreSQL local
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/musicdb
# Phase 3+ : Migrer vers Supabase
# DATABASE_URL=postgresql+asyncpg://supabase:supabase@localhost:54322/postgres
```

2. **Mise à jour `docker-compose.yml`** :
   - Services Supabase déjà partiellement configurés
   - Ajouter healthchecks pour supabase-db
   - Configurer les dépendances de démarrage

### 1.3 Infrastructure Supabase

**État actuel :** Le dossier `supabase/` existe avec :
- `Dockerfile` : PostgreSQL 15 avec extensions
- `db_init/init_supabase.sql` : Extensions uuid-ossp, pg_trgm, pgcrypto, vector
- `scripts/start.sh`, `stop.sh`, `logs.sh` : Gestion des services

**Actions :**
- Vérifier que les scripts sont compatibles PowerShell
- Tester le démarrage : `.\supabase\scripts\start.sh`

---

## Phase 2 : Couche d'Abstraction Base de Données (Semaine 1-2)

### 2.1 DatabaseAdapter Pattern

**Nouveau fichier :** `backend/api/utils/db_adapter.py`

```python
"""
Couche d'abstraction pour la base de données.
Permet la transition progressive de SQLAlchemy vers Supabase.
"""

import os
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

class DatabaseAdapter:
    """
    Adaptateur unifié pour SQLAlchemy et Supabase.
    
    Usage:
        adapter = DatabaseAdapter(use_supabase=FeatureFlags.USE_SUPABASE_DB)
        result = await adapter.query('tracks', {'id': 123})
    """
    
    def __init__(self, use_supabase: Optional[bool] = None):
        self.use_supabase = use_supabase or os.getenv('USE_SUPABASE_DB', 'false').lower() == 'true'
        self._supabase_client = None
        self._sqlalchemy_session = None
    
    async def _get_supabase(self):
        """Lazy loading du client Supabase."""
        if self._supabase_client is None:
            from backend.api.utils.supabase_client import get_supabase_client
            self._supabase_client = get_supabase_client()
        return self._supabase_client
    
    async def query(self, table: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Requête SELECT avec filtres.
        
        Args:
            table: Nom de la table
            filters: Dict de filtres {colonne: valeur}
            
        Returns:
            Liste de dictionnaires
        """
        if self.use_supabase:
            return await self._supabase_query(table, filters)
        return await self._sqlalchemy_query(table, filters)
    
    async def _supabase_query(self, table: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """Requête via Supabase."""
        client = await self._get_supabase()
        query = client.table(table).select('*')
        
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)
        
        response = await query.execute()
        return response.data
    
    async def _sqlalchemy_query(self, table: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """Requête via SQLAlchemy (fallback)."""
        from sqlalchemy import select
        from backend.api.utils.database import get_async_session
        
        # Mapping table -> modèle
        model = self._get_model_for_table(table)
        
        async with get_async_session() as session:
            stmt = select(model)
            if filters:
                for col, val in filters.items():
                    stmt = stmt.where(getattr(model, col) == val)
            
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [row.to_dict() for row in rows]
    
    def _get_model_for_table(self, table: str):
        """Mapping table name -> SQLAlchemy model."""
        from backend.api.models import Track, Artist, Album
        
        mapping = {
            'tracks': Track,
            'artists': Artist,
            'albums': Album,
            # ... autres mappings
        }
        return mapping.get(table)
    
    # TODO: Implémenter insert(), update(), delete() avec même pattern
    
    async def close(self):
        """Nettoyage des ressources."""
        if self._supabase_client:
            await self._supabase_client.aclose()
```

### 2.2 Feature Flags

**Fichier à modifier :** `frontend/utils/feature_flags.py`

```python
"""
Feature flags pour la migration Supabase.
Permettent d'activer/désactiver les fonctionnalités progressivement.
"""

import os

class FeatureFlags:
    """Flags de fonctionnalités pour migration progressive."""
    
    # Database
    USE_SUPABASE_DB = os.getenv('USE_SUPABASE_DB', 'false').lower() == 'true'
    
    # Auth
    USE_SUPABASE_AUTH = os.getenv('USE_SUPABASE_AUTH', 'false').lower() == 'true'
    
    # Realtime (WebSocket replacement)
    USE_SUPABASE_REALTIME = os.getenv('USE_SUPABASE_REALTIME', 'false').lower() == 'true'
    
    # Storage (covers, avatars)
    USE_SUPABASE_STORAGE = os.getenv('USE_SUPABASE_STORAGE', 'false').lower() == 'true'
    
    # GraphQL (désactiver quand Supabase views prêtes)
    USE_GRAPHQL = os.getenv('USE_GRAPHQL', 'true').lower() == 'true'
    
    @classmethod
    def status(cls) -> dict:
        """Retourne l'état de tous les flags (pour monitoring)."""
        return {
            'supabase_db': cls.USE_SUPABASE_DB,
            'supabase_auth': cls.USE_SUPABASE_AUTH,
            'supabase_realtime': cls.USE_SUPABASE_REALTIME,
            'supabase_storage': cls.USE_SUPABASE_STORAGE,
            'graphql': cls.USE_GRAPHQL,
        }
```

---

## Phase 3 : Migration des Modèles et Vues (Semaine 2-3)

### 3.1 Stratégie : Conserver SQLAlchemy

**Principe :** Les modèles SQLAlchemy dans `backend/api/models/` restent la source de vérité
pour la structure des tables. Les migrations Alembic continuent de fonctionner.

**Raisons :**
- Évite de réécrire 30+ migrations
- Garde la validation Pydantic/SQLAlchemy
- Permet rollback facile

### 3.2 Vues Supabase pour remplacer GraphQL

**Nouveau fichier :** `supabase/db_init/02_views.sql`

```sql
-- Vues pour remplacer les requêtes GraphQL complexes
-- Ces vues permettent au frontend de faire des requêtes simples
-- tout en obtenant des données enrichies

-- Vue tracks avec artistes et albums
CREATE OR REPLACE VIEW public.tracks_with_relations AS
SELECT 
    t.id,
    t.title,
    t.duration,
    t.path,
    a.id as artist_id,
    a.name as artist_name,
    al.id as album_id,
    al.title as album_title,
    al.year as album_year
FROM tracks t
LEFT JOIN artists a ON t.artist_id = a.id
LEFT JOIN albums al ON t.album_id = al.id;

-- Vue artists avec statistiques
CREATE OR REPLACE VIEW public.artists_with_stats AS
SELECT 
    a.id,
    a.name,
    COUNT(DISTINCT t.id) as track_count,
    COUNT(DISTINCT al.id) as album_count
FROM artists a
LEFT JOIN tracks t ON t.artist_id = a.id
LEFT JOIN albums al ON al.artist_id = a.id
GROUP BY a.id, a.name;

-- Vue albums avec tracks
CREATE OR REPLACE VIEW public.albums_with_tracks AS
SELECT 
    al.id,
    al.title,
    al.year,
    a.name as artist_name,
    json_agg(
        json_build_object(
            'id', t.id,
            'title', t.title,
            'duration', t.duration,
            'track_number', t.track_number
        ) ORDER BY t.track_number
    ) as tracks
FROM albums al
LEFT JOIN artists a ON al.artist_id = a.id
LEFT JOIN tracks t ON t.album_id = al.id
GROUP BY al.id, al.title, al.year, a.name;

-- Politiques RLS (Row Level Security)
-- Permettre lecture publique pour le catalogue
ALTER TABLE tracks ENABLE ROW LEVEL SECURITY;
ALTER TABLE artists ENABLE ROW LEVEL SECURITY;
ALTER TABLE albums ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read tracks" ON tracks FOR SELECT USING (true);
CREATE POLICY "Allow public read artists" ON artists FOR SELECT USING (true);
CREATE POLICY "Allow public read albums" ON albums FOR SELECT USING (true);

-- TODO: Ajouter politiques pour écriture (authentifié uniquement)
```

### 3.3 Mapping Modèles → Tables

**Nouveau fichier :** `backend/api/utils/model_mapper.py`

```python
"""
Mapping entre modèles SQLAlchemy et tables Supabase.
Utilisé par DatabaseAdapter pour les conversions.
"""

from typing import Dict, Type, Any
from backend.api.models import Track, Artist, Album, User

# Mapping table Supabase -> Modèle SQLAlchemy
TABLE_TO_MODEL: Dict[str, Type] = {
    'tracks': Track,
    'artists': Artist,
    'albums': Album,
    'users': User,
    # TODO: Ajouter autres tables
}

# Mapping Modèle SQLAlchemy -> table Supabase
MODEL_TO_TABLE: Dict[Type, str] = {
    Track: 'tracks',
    Artist: 'artists',
    Album: 'albums',
    User: 'users',
    # TODO: Ajouter autres modèles
}

# Champs à exclure lors de la sérialisation (internes SQLAlchemy)
EXCLUDED_FIELDS = {'_sa_instance_state', 'metadata', 'registry'}

def model_to_dict(instance: Any) -> Dict[str, Any]:
    """
    Convertit une instance SQLAlchemy en dict pour Supabase.
    
    Args:
        instance: Instance de modèle SQLAlchemy
        
    Returns:
        Dictionnaire sérialisable
    """
    if instance is None:
        return None
    
    result = {}
    for key in dir(instance):
        if key.startswith('_') or key in EXCLUDED_FIELDS:
            continue
        
        value = getattr(instance, key)
        # Ignorer méthodes et relations complexes
        if callable(value) or hasattr(value, '_sa_class_manager'):
            continue
        
        result[key] = value
    
    return result

def dict_to_model(data: Dict[str, Any], model_class: Type) -> Any:
    """
    Convertit un dict Supabase en instance SQLAlchemy.
    
    Args:
        data: Données de Supabase
        model_class: Classe du modèle SQLAlchemy
        
    Returns:
        Instance du modèle
    """
    if data is None:
        return None
    
    # Filtrer les champs qui n'existent pas dans le modèle
    valid_fields = {
        k: v for k, v in data.items() 
        if hasattr(model_class, k)
    }
    
    return model_class(**valid_fields)
```

---

## Phase 4 : Migration des Services Backend (Semaine 3-4)

### 4.1 Approche par étapes

**Ordre de migration :**
1. **Lecture (SELECT)** : Migrer en premier (lecture seule, sans risque)
2. **Écriture (INSERT/UPDATE/DELETE)** : Garder SQLAlchemy temporairement
3. **Transactions complexes** : Dernière étape (nécessite tests approfondis)

### 4.2 Exemple : TrackService

**Fichier à modifier :** `backend/api/services/track_service.py`

```python
"""
Service de gestion des tracks - Version hybride SQLAlchemy/Supabase.
"""

from typing import Optional, List, Dict, Any
from backend.api.utils.feature_flags import FeatureFlags
from backend.api.utils.db_adapter import DatabaseAdapter
from backend.api.utils.database import get_async_session
from backend.api.models.tracks_model import Track
from sqlalchemy import select

class TrackService:
    """
    Service de gestion des tracks.
    
    En phase de migration, utilise DatabaseAdapter pour basculer
    entre SQLAlchemy et Supabase selon les feature flags.
    """
    
    def __init__(self):
        self.db = DatabaseAdapter(use_supabase=FeatureFlags.USE_SUPABASE_DB)
    
    async def get_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère une track par ID.
        
        Phase 1 : Lecture via Supabase si activé
        """
        if FeatureFlags.USE_SUPABASE_DB:
            # Via Supabase (lecture seule, sans risque)
            result = await self.db.query('tracks', {'id': track_id})
            return result[0] if result else None
        else:
            # Via SQLAlchemy (fallback)
            async with get_async_session() as session:
                track = await session.get(Track, track_id)
                return track.to_dict() if track else None
    
    async def get_tracks_by_artist(self, artist_id: int) -> List[Dict[str, Any]]:
        """
        Récupère les tracks d'un artiste.
        """
        if FeatureFlags.USE_SUPABASE_DB:
            result = await self.db.query('tracks', {'artist_id': artist_id})
            return result
        else:
            async with get_async_session() as session:
                stmt = select(Track).where(Track.artist_id == artist_id)
                result = await session.execute(stmt)
                tracks = result.scalars().all()
                return [t.to_dict() for t in tracks]
    
    async def create_track(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une nouvelle track.
        
        Phase 1 : Toujours via SQLAlchemy pour garantir cohérence
        Phase 2 : Migrer vers Supabase avec validation
        """
        # Écriture toujours via SQLAlchemy pour l'instant
        # (garantit la cohérence avec les migrations existantes)
        async with get_async_session() as session:
            track = Track(**track_data)
            session.add(track)
            await session.commit()
            await session.refresh(track)
            
            # TODO: Phase 2 - Synchroniser avec Supabase via trigger PostgreSQL
            # ou utiliser supabase.table('tracks').insert()
            
            return track.to_dict()
    
    async def update_track(self, track_id: int, track_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour une track.
        
        Phase 1 : Via SQLAlchemy
        """
        async with get_async_session() as session:
            track = await session.get(Track, track_id)
            if not track:
                return None
            
            for key, value in track_data.items():
                if hasattr(track, key):
                    setattr(track, key, value)
            
            await session.commit()
            await session.refresh(track)
            return track.to_dict()
    
    async def delete_track(self, track_id: int) -> bool:
        """
        Supprime une track.
        
        Phase 1 : Via SQLAlchemy
        """
        async with get_async_session() as session:
            track = await session.get(Track, track_id)
            if not track:
                return False
            
            await session.delete(track)
            await session.commit()
            return True
```

### 4.3 Services à migrer (ordre de priorité)

| Service | Priorité | Complexité | Stratégie |
|---------|----------|------------|-----------|
| `track_service.py` | Haute | Moyenne | Lecture d'abord |
| `artist_service.py` | Haute | Faible | Lecture d'abord |
| `album_service.py` | Haute | Faible | Lecture d'abord |
| `search_service.py` | Moyenne | Haute | Garder SQLAlchemy (TSVECTOR) |
| `chat_service.py` | Moyenne | Moyenne | Hybride |
| `vector_search_service.py` | Basse | Haute | Garder SQLAlchemy (pgvector) |

---

## Phase 5 : Migration Frontend (Semaine 4-5)

### 5.1 Remplacement des services v2

Les fichiers `_v2.py` existants deviennent la norme :

**Action :** Renommer et remplacer
- `frontend/services/track_service_v2.py` → `frontend/services/track_service.py`
- `frontend/services/artist_service_v2.py` → `frontend/services/artist_service.py`
- `frontend/services/album_service_v2.py` → `frontend/services/album_service.py`

### 5.2 Exemple : TrackService Frontend

**Fichier :** `frontend/services/track_service.py` (nouvelle version)

```python
"""
Service de gestion des tracks - Frontend avec Supabase.
"""

import os
from typing import Optional, List, Dict, Any
from frontend.utils.supabase_client import get_supabase_client
from frontend.utils.feature_flags import FeatureFlags
from frontend.utils.logging import logger

class TrackService:
    """
    Service de gestion des tracks côté frontend.
    
    Communique directement avec Supabase pour les opérations CRUD,
    évitant le passage par l'API FastAPI pour les opérations simples.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.api_url = os.getenv("API_URL", "http://localhost:8001")
    
    async def get_tracks(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère la liste des tracks.
        
        Via Supabase si activé, sinon via API legacy.
        """
        if FeatureFlags.USE_SUPABASE_DB:
            # Via Supabase directement
            response = await self.supabase.table('tracks')\
                .select('*')\
                .range(skip, skip + limit - 1)\
                .execute()
            return response.data
        else:
            # Fallback via API
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/api/tracks",
                    params={"skip": skip, "limit": limit}
                )
                return response.json()
    
    async def get_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une track par ID."""
        if FeatureFlags.USE_SUPABASE_DB:
            response = await self.supabase.table('tracks')\
                .select('*')\
                .eq('id', track_id)\
                .single()\
                .execute()
            return response.data
        else:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/api/tracks/{track_id}")
                if response.status_code == 200:
                    return response.json()
                return None
    
    async def search_tracks(self, query: str) -> List[Dict[str, Any]]:
        """
        Recherche de tracks.
        
        Note : En phase 1, la recherche full-text reste via API
        (car utilise PostgreSQL TSVECTOR).
        """
        # TODO: Phase 2 - Migrer vers Supabase quand views prêtes
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/search",
                params={"q": query}
            )
            return response.json().get('results', [])
    
    # TODO: Implémenter create_track, update_track, delete_track
```

---

## Phase 6 : Migration Realtime (Semaine 5)

### 6.1 Remplacer WebSocket par Supabase Realtime

**Fichier existant :** `frontend/utils/supabase_realtime.py` (déjà créé)

**Utilisation :**

```python
# frontend/pages/playlist_page.py

from frontend.utils.supabase_realtime import supabase_realtime
from frontend.utils.feature_flags import FeatureFlags

class PlaylistPage:
    def __init__(self):
        if FeatureFlags.USE_SUPABASE_REALTIME:
            # Utiliser Supabase Realtime
            self.channel = supabase_realtime.subscribe_to_playlist(
                playlist_id=123,
                callback=self.on_playlist_update
            )
        else:
            # Fallback WebSocket legacy
            self.ws = WebSocketClient()
    
    def on_playlist_update(self, payload):
        """Callback appelé quand la playlist change."""
        # payload contient le changement (INSERT, UPDATE, DELETE)
        self.refresh_playlist()
```

### 6.2 Cas à conserver en WebSocket

Certains cas nécessitent de garder WebSocket :
- **Streaming audio** : Flux binaires, latence critique
- **Chat IA temps réel** : Intégration avec LLM service
- **Notifications push** : Événements système

---

## Phase 7 : Workers Celery (Semaine 5-6)

### 7.1 Principe : Pas de changement majeur

Les workers dans `backend_worker/` continuent d'utiliser l'API :
- Pas de connexion directe à Supabase (respect de l'architecture)
- Appels HTTP vers `api-service` pour toute opération DB

### 7.2 Optimisation Bulk Operations

**Fichier existant :** `backend_worker/services/bulk_operations_service.py`

Utiliser l'API batch de Supabase pour les opérations massives :
```python
# Insertion batch optimisée
await supabase.table('tracks').insert(tracks_data).execute()
```

---

## Phase 8 : Tests et Validation (Semaine 6-7)

### 8.1 Stratégie de test

| Type | Outil | Couverture |
|------|-------|------------|
| Unit tests | pytest | Services avec mocks Supabase |
| Integration | pytest + Docker | API avec Supabase local |
| E2E | Playwright/Selenium | Parcours complets UI |

### 8.2 Checklist de non-régression

- [ ] **Scan bibliothèque** : Découverte et indexation des fichiers
- [ ] **Lecture audio** : Streaming sans interruption
- [ ] **Recherche texte** : Résultats pertinents, performance < 200ms
- [ ] **Recherche vectorielle** : Similarités cohérentes
- [ ] **CRUD tracks** : Création, lecture, mise à jour, suppression
- [ ] **CRUD artists/albums** : Mêmes opérations
- [ ] **Auth utilisateurs** : Login, logout, sessions
- [ ] **Realtime playlists** : Synchronisation temps réel
- [ ] **Workers Celery** : Traitement des tâches en arrière-plan
- [ ] **MIR (Music Info Retrieval)** : Analyse audio, embeddings

### 8.3 Tests parallèles

Comparatif SQLAlchemy vs Supabase :
```python
# Test comparatif
async def test_read_consistency():
    """Vérifie que Supabase et SQLAlchemy retournent les mêmes résultats."""
    track_id = 123
    
    # Via SQLAlchemy
    track_sqlalchemy = await track_service_sqlalchemy.get_track(track_id)
    
    # Via Supabase
    track_supabase = await track_service_supabase.get_track(track_id)
    
    # Doivent être identiques
    assert track_sqlalchemy['title'] == track_supabase['title']
    assert track_sqlalchemy['duration'] == track_supabase['duration']
```

---

## Phase 9 : Nettoyage et Documentation (Semaine 7-8)

### 9.1 Suppression code legacy (après validation)

Une fois tous les tests passés et la migration validée :

- [ ] Supprimer `backend/api/utils/database.py` (ou garder pour fallback)
- [ ] Supprimer services sans suffixe (remplacés par v2)
- [ ] Supprimer routes GraphQL obsolètes
- [ ] Nettoyer migrations Alembic (optionnel)

### 9.2 Documentation

**Fichiers à mettre à jour :**
- `README.md` : Nouvelle architecture
- `docs/plans/supabase-checklist.md` : État de la migration
- `.env.example` : Variables Supabase
- `docs/architecture/` : Diagrammes à jour

---

## Fichiers à Modifier (Récapitulatif)

### Nouveaux fichiers
1. `backend/api/utils/db_adapter.py` - Couche d'abstraction
2. `backend/api/utils/model_mapper.py` - Mapping modèles
3. `supabase/db_init/02_views.sql` - Vues Supabase
4. `.env.supabase` - Configuration

### Fichiers à modifier
1. `frontend/utils/feature_flags.py` - Ajouter flags Supabase
2. `backend/api/services/track_service.py` - Migration hybride
3. `backend/api/services/artist_service.py` - Migration hybride
4. `backend/api/services/album_service.py` - Migration hybride
5. `frontend/services/track_service.py` - Remplacer par v2
6. `frontend/services/artist_service.py` - Remplacer par v2
7. `frontend/services/album_service.py` - Remplacer par v2
8. `docker-compose.yml` - Healthchecks Supabase

### Fichiers à supprimer (Phase 9)
1. Services legacy sans suffixe
2. Routes GraphQL obsolètes
3. (Optionnel) `backend/api/utils/database.py`

---

## Risques et Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Régression fonctionnelle | Moyenne | Haute | Feature flags, tests parallèles |
| Perte de données | Faible | Critique | Backup avant migration, transactions |
| Performance dégradée | Moyenne | Moyenne | Tests de charge, cache Redis |
| Incompatibilité extensions | Faible | Haute | Vérifier pgvector, pg_trgm |
| Complexité rollback | Moyenne | Moyenne | Feature flags, documentation |

---

## Planning et Jalons

| Semaine | Phase | Livrable | Validation |
|---------|-------|----------|------------|
| 1 | 1 | Branche créée, env configuré | Démarrage Supabase local |
| 1-2 | 2 | DatabaseAdapter, FeatureFlags | Tests unitaires passent |
| 2-3 | 3 | Vues SQL, ModelMapper | Vues créées, mapping testé |
| 3-4 | 4 | Services backend hybrides | Lecture via Supabase OK |
| 4-5 | 5 | Frontend services v2 | CRUD frontend fonctionne |
| 5 | 6 | Realtime Supabase | Playlists temps réel OK |
| 5-6 | 7 | Workers optimisés | Bulk operations OK |
| 6-7 | 8 | Tests E2E complets | Checklist non-régression |
| 7-8 | 9 | Documentation, nettoyage | Merge vers master |

---

## Prochaines Actions Immédiates

1. **Validation du plan** : En attente de votre approbation
2. **Création branche** : `blackboxai/feature/supabase-migration-v2`
3. **Démarrage Phase 1** : Configuration et variables d'environnement

---

**En attente de votre validation pour commencer la Phase 1.**
