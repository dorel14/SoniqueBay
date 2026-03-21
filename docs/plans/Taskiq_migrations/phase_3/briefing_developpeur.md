# Briefing Développeur — Phase 3 : Accès DB Direct Worker

## 🎯 Objectif
Permettre l'accès DB direct pour les tâches à fort volume, avec garde-fous de sécurité.

---

## 📋 Tâches à Réaliser

### T3.1 : Créer `backend_worker/db/__init__.py`
**Fichier** : `backend_worker/db/__init__.py` (nouveau)

**Contenu** :
```python
"""Couche d'accès DB pour les workers TaskIQ.

Accès direct PostgreSQL avec garde-fous.
"""
from backend_worker.db.engine import create_worker_engine
from backend_worker.db.session import get_worker_session
from backend_worker.db.repositories import TrackRepository, ArtistRepository
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les imports sont corrects

---

### T3.2 : Créer `backend_worker/db/engine.py`
**Fichier** : `backend_worker/db/engine.py` (nouveau)

**Contenu** :
```python
"""Engine SQLAlchemy pour les workers."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
import os

def create_worker_engine() -> AsyncEngine:
    """Crée un engine async pour les workers.
    
    Optimisé pour Raspberry Pi :
    - NullPool pour éviter les fuites de connexions
    - Timeouts stricts
    - Pool size limité
    """
    database_url = os.getenv('WORKER_DATABASE_URL')
    if not database_url:
        raise ValueError("WORKER_DATABASE_URL non configuré")
    
    return create_async_engine(
        database_url,
        poolclass=NullPool,  # Pas de pool pour les workers
        connect_args={
            'timeout': 30,
            'command_timeout': 60,
        },
        echo=False,
    )
```

**Validation** :
- [ ] Le fichier existe
- [ ] L'engine s'initialise correctement
- [ ] Les timeouts sont configurés

---

### T3.3 : Créer `backend_worker/db/session.py`
**Fichier** : `backend_worker/db/session.py` (nouveau)

**Contenu** :
```python
"""Session SQLAlchemy pour les workers."""
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from backend_worker.db.engine import create_worker_engine

def get_worker_session() -> async_sessionmaker[AsyncSession]:
    """Retourne une factory de sessions pour les workers."""
    engine = create_worker_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
```

**Validation** :
- [ ] Le fichier existe
- [ ] La session s'initialise correctement

---

### T3.4 : Créer `backend_worker/db/repositories/base.py`
**Fichier** : `backend_worker/db/repositories/base.py` (nouveau)

**Contenu** :
```python
"""Repository de base avec garde-fous."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio

class BaseRepository:
    """Classe de base pour les repositories workers."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def execute_with_timeout(self, query, timeout=30):
        """Exécute une requête avec timeout."""
        try:
            return await asyncio.wait_for(
                self.session.execute(query),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Requête timeout après {timeout}s")
    
    async def commit_with_retry(self, max_retries=3):
        """Commit avec retry et backoff."""
        for attempt in range(max_retries):
            try:
                await self.session.commit()
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Backoff exponentiel
```

**Validation** :
- [ ] Le fichier existe
- [ ] Les timeouts fonctionnent
- [ ] Le retry fonctionne

---

### T3.5 : Créer `backend_worker/db/repositories/track_repository.py`
**Fichier** : `backend_worker/db/repositories/track_repository.py` (nouveau)

**Contenu** :
```python
"""Repository pour les tracks avec accès direct DB."""
from sqlalchemy import select, insert, update
from backend_worker.models.tracks_model import Track
from backend_worker.db.repositories.base import BaseRepository

class TrackRepository(BaseRepository):
    """Opérations sur les tracks."""
    
    async def bulk_insert_tracks(self, tracks_data: list[dict]) -> list[int]:
        """Insertion en masse de tracks.
        
        Args:
            tracks_data: Liste des données de tracks
            
        Returns:
            Liste des IDs insérés
        """
        if not tracks_data:
            return []
        
        # Utiliser l'insertion en masse SQLAlchemy
        stmt = insert(Track).values(tracks_data).returning(Track.id)
        result = await self.execute_with_timeout(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def get_track_by_path(self, path: str) -> dict | None:
        """Récupère une track par son chemin."""
        stmt = select(Track).where(Track.path == path)
        result = await self.execute_with_timeout(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
```

**Validation** :
- [ ] Le fichier existe
- [ ] Le bulk insert fonctionne
- [ ] Le get by path fonctionne

---

### T3.6 : Migrer `insert.direct_batch` vers TaskIQ avec DB direct
**Fichier** : `backend_worker/taskiq_tasks/insert.py` (nouveau)

**Contenu** :
```python
from backend_worker.taskiq_app import broker
from backend_worker.db.repositories.track_repository import TrackRepository
from backend_worker.db.session import get_worker_session

@broker.task
async def insert_direct_batch_task(insertion_data: dict) -> dict:
    """Insertion directe en DB via TaskIQ.
    
    Args:
        insertion_data: Données à insérer (artists, albums, tracks)
        
    Returns:
        Résultat de l'insertion
    """
    session_factory = get_worker_session()
    async with session_factory() as session:
        repo = TrackRepository(session)
        
        # Insertion des tracks
        track_ids = await repo.bulk_insert_tracks(insertion_data['tracks'])
        
        await session.commit()
        
        return {
            "tracks_inserted": len(track_ids),
            "track_ids": track_ids,
            "success": True
        }
```

**Validation** :
- [ ] Le fichier existe
- [ ] La tâche fonctionne
- [ ] L'insertion DB direct fonctionne

---

## 🧪 Tests à Exécuter

### Vérifications de Qualité de Code
```bash
# Exécuter ruff check sur les fichiers modifiés
ruff check backend_worker/db/ backend_worker/taskiq_tasks/insert.py

# Vérifier l'absence d'erreurs Pylance dans VS Code
# (Ouvrir les fichiers et vérifier la barre d'état)
```

### Tests Unitaires
```bash
# Exécuter les tests unitaires TaskIQ
python -m pytest tests/unit/worker/db/test_repositories.py -v

# Exécuter les tests unitaires Celery existants (vérifier qu'ils passent toujours)
python -m pytest tests/unit/worker -q --tb=no
```

### Tests d'Intégration
```bash
# Exécuter les tests d'intégration workers
python -m pytest tests/integration/workers -q --tb=no
```

---

## ✅ Critères d'Acceptation

- [ ] **Ruff check passe** sans erreur sur les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Le fichier `backend_worker/db/__init__.py` existe et est correct
- [ ] Le fichier `backend_worker/db/engine.py` existe et est correct
- [ ] Le fichier `backend_worker/db/session.py` existe et est correct
- [ ] Le fichier `backend_worker/db/repositories/base.py` existe et est correct
- [ ] Le fichier `backend_worker/db/repositories/track_repository.py` existe et est correct
- [ ] Le fichier `backend_worker/taskiq_tasks/insert.py` existe et est correct
- [ ] Les tests unitaires TaskIQ passent
- [ ] Les tests unitaires Celery existants passent (0 régression)
- [ ] Les tests d'intégration workers existants passent (0 régression)
- [ ] L'insertion DB direct fonctionne
- [ ] Les timeouts sont respectés
- [ ] Les retries fonctionnent

---

## 🚨 Points d'Attention

1. **Ne pas modifier** les fichiers Celery existants
2. **Utiliser des imports absolus** (backend_worker.xxx) conformément à AGENTS.md
3. **Logger avec le préfixe `[TASKIQ]`** pour différencier de Celery
4. **Tester localement** avant de committer
5. **Vérifier les timeouts** pour éviter les blocages
6. **Vérifier les retries** pour éviter les pertes de données

---

## 📞 Support

En cas de problème :
1. Consulter les logs Docker : `docker logs soniquebay-taskiq-worker`
2. Vérifier la connexion DB : `docker exec soniquebay-postgres psql -U soniquebay -d soniquebay -c "SELECT 1;"`
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 3 (Accès DB Direct Worker)*
*Statut : En cours*
