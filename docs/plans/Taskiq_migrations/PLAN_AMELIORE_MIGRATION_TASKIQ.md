# Plan Amélioré de Migration Celery → TaskIQ (SoniqueBay)

## 📋 Résumé Exécutif

Ce plan amélioré intègre des **garde-fous anti-régression** basés sur l'audit du code existant. Il garantit une migration incrémentale sans interruption de service.

---

## 🔍 Analyse des Risques Identifiés

### Points d'Attention Critiques
1. **Configuration Celery unifiée** : `celery_config_source.py` et `celery_config_publisher.py` synchronisent la config via Redis
2. **Queues et priorités** : 13 queues configurées avec priorités strictes (scan=0, deferred=9)
3. **Tâches bind=True** : Utilisation de `self.request.id` pour le tracking
4. **Monitoring** : Signaux Celery (worker_init, task_prerun, task_postrun, worker_shutdown)
5. **Tests existants** : 15+ tests unitaires worker, 6 tests intégration workers

### Fichiers Sensibles à Ne Pas Casser
- [`backend_worker/celery_app.py`](backend_worker/celery_app.py) - Configuration principale
- [`backend_worker/celery_tasks.py`](backend_worker/celery_tasks.py) - Tâches centralisées
- [`backend_worker/celery_config_source.py`](backend_worker/celery_config_source.py) - Config unifiée
- [`backend/api/utils/celery_app.py`](backend/api/utils/celery_app.py) - Config API
- [`docker-compose.yml`](docker-compose.yml) - Services Docker

---

## 🛡️ Stratégie Anti-Régression

### 1. Mode Coexistence (Phase 1-2)
```
Celery Worker (existant) ←→ Redis ←→ TaskIQ Worker (nouveau)
         ↓                           ↓
    Tâches legacy              Tâches migrées
```

### 2. Feature Flags par Tâche
```python
# .env
USE_TASKIQ_FOR_SCAN=false
USE_TASKIQ_FOR_METADATA=false
USE_TASKIQ_FOR_BATCH=false
USE_TASKIQ_FOR_INSERT=false
USE_TASKIQ_FOR_VECTORIZATION=false
ENABLE_CELERY_FALLBACK=true
```

### 3. Shadow Mode (Phase 2)
- Exécution simultanée Celery + TaskIQ
- Comparaison des résultats
- Logs différenciés `[CELERY]` vs `[TASKIQ]`

### 4. Tests de Non-Régression
- Avant chaque phase : baseline des tests existants
- Après chaque phase : comparaison des résultats
- Critère : 0 régression sur les tests existants

---

## 📦 Plan de Migration par Phases

## Phase 0 — Audit et Préparation (1-2 jours) ✅ TERMINÉE

### Objectif
Cartographier l'existant sans modifier le code.

### Tâches
- [x] **T0.1** : Lister toutes les tâches Celery avec leurs signatures
  - Fichier : [`docs/plans/taskiq_migrations/audit/taches_celery.md`](docs/plans/taskiq_migrations/audit/taches_celery.md)
  - Format : nom, queue, priorité, payload, idempotence, criticité
  - **Résultat** : 26 tâches identifiées (4 haute, 7 moyenne, 15 basse criticité)

- [x] **T0.2** : Documenter les dépendances entre tâches
  - Fichier : [`docs/plans/taskiq_migrations/audit/dependances_taches.md`](docs/plans/taskiq_migrations/audit/dependances_taches.md)
  - Exemple : `scan.discovery` → `metadata.extract_batch` → `batch.process_entities` → `insert.direct_batch`
  - **Résultat** : Flux principaux documentés avec diagrammes

- [x] **T0.3** : Exécuter la baseline des tests
  - Fichier : [`docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt`](docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt)
  - Fichier : [`docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt`](docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt)
  - **Résultat** : 31 tests unitaires + 6 tests intégration documentés

- [x] **T0.4** : Documenter la configuration Redis actuelle
  - Fichier : [`docs/plans/taskiq_migrations/audit/configuration_redis.md`](docs/plans/taskiq_migrations/audit/configuration_redis.md)
  - **Résultat** : Configuration complète (URLs, clés, queues, optimisations)

### Livrables
- [x] Matrice des tâches avec priorité de migration
- [x] Baseline des tests (référence pour non-régression)
- [x] Documentation des flux inter-tâches
- [x] Configuration Redis documentée

### Validation
- [x] Tous les tests existants passent (référence établie)
- [x] Documentation complète et revue

### Résultats Détaillés
- Voir : [`docs/plans/taskiq_migrations/phase_0/resultats_audit.md`](docs/plans/taskiq_migrations/phase_0/resultats_audit.md)

---

## Phase 1 — Socle TaskIQ Minimal (2-3 jours)

### Objectif
Ajouter TaskIQ sans impacter Celery existant.

### Tâches Développeur

- [ ] **T1.1** : Ajouter les dépendances TaskIQ
  - Fichier : `backend_worker/requirements.txt`
  - Ajouter : `taskiq[redis]`, `taskiq-fastapi`
  - **NE PAS SUPPRIMER** les dépendances Celery

- [ ] **T1.2** : Créer `backend_worker/taskiq_app.py`
  ```python
  """Configuration TaskIQ pour SoniqueBay.
  
  Coexiste avec celery_app.py pendant la migration.
  """
  from taskiq import TaskiqState
  from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
  from backend_worker.utils.logging import logger
  import os
  
  # Broker Redis (même instance que Celery)
  broker = ListQueueBroker(
      url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')  # DB différente
  )
  
  # Backend pour les résultats
  result_backend = RedisAsyncResultBackend(
      redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
  )
  
  @broker.on_event(TaskiqState.EVENT_PRE_SEND)
  async def pre_send_handler(task_name: str, **kwargs):
      logger.info(f"[TASKIQ] Envoi tâche: {task_name}")
  
  @broker.on_event(TaskiqState.EVENT_POST_EXECUTE)
  async def post_execute_handler(task_name: str, result, **kwargs):
      logger.info(f"[TASKIQ] Tâche terminée: {task_name}")
  ```

- [ ] **T1.3** : Créer `backend_worker/taskiq_worker.py`
  ```python
  """Worker TaskIQ pour SoniqueBay.
  
  Démarre en parallèle du worker Celery.
  """
  from backend_worker.taskiq_app import broker
  import asyncio
  
  # Import des tâches TaskIQ (à migrer progressivement)
  # from backend_worker.taskiq_tasks import *
  
  async def main():
      await broker.startup()
      # Le worker écoute les tâches
      await broker.run()
  
  if __name__ == "__main__":
      asyncio.run(main())
  ```

- [ ] **T1.4** : Ajouter le service TaskIQ dans `docker-compose.yml`
  ```yaml
  taskiq-worker:
      build:
          context: .
          dockerfile: backend_worker/Dockerfile
      container_name: soniquebay-taskiq-worker
      restart: unless-stopped
      command: ["python", "-m", "backend_worker.taskiq_worker"]
      volumes:
          - ./backend_worker:/app/backend_worker
          - music-share:/music:ro
          - ./logs:/app/logs
      environment:
          - TASKIQ_BROKER_URL=redis://redis:6379/1
          - TASKIQ_RESULT_BACKEND=redis://redis:6379/1
          - API_URL=http://library:8001
          - MUSIC_PATH=/music
      depends_on:
          redis:
              condition: service_healthy
          api-service:
              condition: service_healthy
      networks:
          default:
              aliases:
                  - taskiq-worker
      deploy:
          resources:
              limits:
                  cpus: '0.5'
                  memory: 512M
  ```

- [ ] **T1.5** : Ajouter les variables d'environnement
  - Fichier : `.env.example`
  - Variables : `TASKIQ_BROKER_URL`, `TASKIQ_RESULT_BACKEND`

### Tâches Testeur

- [ ] **T1.6** : Créer `tests/unit/worker/test_taskiq_app.py`
  ```python
  """Tests unitaires pour la configuration TaskIQ.
  
  Vérifie que TaskIQ s'initialise correctement sans impacter Celery.
  """
  import pytest
  from backend_worker.taskiq_app import broker, result_backend
  
  def test_taskiq_broker_initialization():
      """Test que le broker TaskIQ s'initialise."""
      assert broker is not None
      assert broker.url is not None
  
  def test_taskiq_result_backend_initialization():
      """Test que le backend de résultats s'initialise."""
      assert result_backend is not None
  
  def test_celery_still_works():
      """Test que Celery fonctionne toujours après ajout TaskIQ."""
      from backend_worker.celery_app import celery
      assert celery is not None
      assert celery.conf.broker_url is not None
  ```

- [ ] **T1.7** : Exécuter les tests de non-régression
  ```bash
  python -m pytest tests/unit/worker/test_taskiq_app.py -v
  python -m pytest tests/unit/worker -q --tb=no
  # Comparer avec baseline Phase 0
  ```

### Livrables
- Worker TaskIQ démarre en parallèle de Celery
- Aucune tâche métier migrée
- Tests unitaires TaskIQ passent
- Tests existants Celery toujours verts

### Validation
- [ ] `docker-compose up` démarre les 4 conteneurs (api, celery-worker, taskiq-worker, frontend)
- [ ] Logs TaskIQ visibles sans erreurs
- [ ] Tests unitaires TaskIQ passent
- [ ] Tests unitaires Celery existants passent (0 régression)

---

## Phase 2 — Migration Pilote (2-4 jours)

### Objectif
Migrer 1-2 tâches non critiques avec shadow mode.

### Sélection Tâche Pilote
**Recommandation** : `maintenance.cleanup_old_data` (non critique, idempotente)

### Tâches Développeur

- [ ] **T2.1** : Créer `backend_worker/taskiq_tasks/maintenance.py`
  ```python
  """Tâches TaskIQ de maintenance.
  
  Migration de celery_tasks.py vers TaskIQ.
  """
  from backend_worker.taskiq_app import broker
  from backend_worker.utils.logging import logger
  import os
  
  @broker.task
  async def cleanup_old_data_task(days_old: int = 30) -> dict:
      """Nettoie les anciennes données.
      
      Args:
          days_old: Nombre de jours pour considérer les données comme anciennes
          
      Returns:
          Résultat du nettoyage
      """
      logger.info(f"[TASKIQ] Nettoyage données > {days_old} jours")
      # Implémentation existante
      return {"cleaned": True, "days_old": days_old}
  ```

- [ ] **T2.2** : Ajouter le feature flag dans `backend_worker/celery_tasks.py`
  ```python
  # En haut du fichier
  import os
  
  USE_TASKIQ_FOR_MAINTENANCE = os.getenv('USE_TASKIQ_FOR_MAINTENANCE', 'false').lower() == 'true'
  
  @celery.task(name="maintenance.cleanup_old_data", queue="maintenance", bind=True)
  def cleanup_old_data(self, days_old: int = 30):
      """Nettoie les anciennes données."""
      if USE_TASKIQ_FOR_MAINTENANCE:
          # Déléguer à TaskIQ
          from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
          # Note: TaskIQ est async, on utilise un wrapper sync
          import asyncio
          try:
              loop = asyncio.get_event_loop()
          except RuntimeError:
              loop = asyncio.new_event_loop()
              asyncio.set_event_loop(loop)
          return loop.run_until_complete(cleanup_old_data_task.kiq(days_old=days_old))
      
      # Code Celery existant (ne pas modifier)
      # ... existing implementation ...
  ```

- [ ] **T2.3** : Créer le wrapper sync/async pour TaskIQ
  - Fichier : `backend_worker/taskiq_utils.py`
  - Fonction : `run_taskiq_sync(task_func, *args, **kwargs)`

- [ ] **T2.4** : Ajouter le logging différencié
  ```python
  # Dans les tâches migrées
  logger.info(f"[TASKIQ|CELERY] Tâche {task_name} exécutée via {engine}")
  ```

### Tâches Testeur

- [ ] **T2.5** : Créer `tests/unit/worker/test_taskiq_maintenance.py`
  ```python
  """Tests pour la tâche maintenance migrée vers TaskIQ."""
  import pytest
  from unittest.mock import patch, MagicMock
  
  def test_cleanup_old_data_taskiq():
      """Test que la tâche fonctionne via TaskIQ."""
      from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
      # Mock de la logique métier
      with patch('backend_worker.taskiq_tasks.maintenance.cleanup_logic') as mock_cleanup:
          mock_cleanup.return_value = {"cleaned": 10}
          # Test async
          import asyncio
          result = asyncio.run(cleanup_old_data_task(days_old=30))
          assert result["cleaned"] == 10
  
  def test_cleanup_old_data_celery_fallback():
      """Test que le fallback Celery fonctionne."""
      import os
      os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
      from backend_worker.celery_tasks import cleanup_old_data
      # Test que la tâche Celery est appelée
      # ... test implementation ...
  ```

- [ ] **T2.6** : Créer `tests/integration/workers/test_taskiq_maintenance_integration.py`
  ```python
  """Tests d'intégration pour la maintenance TaskIQ."""
  import pytest
  
  @pytest.mark.asyncio
  async def test_maintenance_taskiq_end_to_end():
      """Test complet de la tâche maintenance via TaskIQ."""
      # 1. Démarrer le worker TaskIQ
      # 2. Envoyer la tâche
      # 3. Vérifier le résultat
      # 4. Vérifier les logs
      pass
  ```

- [ ] **T2.7** : Exécuter les tests de comparaison
  ```bash
  # Mode Celery
  USE_TASKIQ_FOR_MAINTENANCE=false python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v
  
  # Mode TaskIQ
  USE_TASKIQ_FOR_MAINTENANCE=true python -m pytest tests/unit/worker/test_taskiq_maintenance.py -v
  
  # Comparer les résultats
  ```

### Livrables
- Tâche maintenance migrée et fonctionnelle
- Feature flag opérationnel
- Tests unitaires et intégration passent
- Rapport comparatif Celery vs TaskIQ

### Validation
- [ ] Tâche fonctionne en mode Celery (flag=false)
- [ ] Tâche fonctionne en mode TaskIQ (flag=true)
- [ ] Logs différenciés visibles
- [ ] Performance comparable (latence, mémoire)
- [ ] Tests existants toujours verts (0 régression)

---

## Phase 3 — Accès DB Direct Worker (Option B) (3-5 jours)

### Objectif
Permettre l'accès DB direct pour les tâches à fort volume.

### Prérequis
- Phase 2 validée
- Feature flag `WORKER_DIRECT_DB_ENABLED` opérationnel

### Tâches Développeur

- [ ] **T3.1** : Créer `backend_worker/db/__init__.py`
  ```python
  """Couche d'accès DB pour les workers TaskIQ.
  
  Accès direct PostgreSQL avec garde-fous.
  """
  from backend_worker.db.engine import create_worker_engine
  from backend_worker.db.session import get_worker_session
  from backend_worker.db.repositories import TrackRepository, ArtistRepository
  ```

- [ ] **T3.2** : Créer `backend_worker/db/engine.py`
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

- [ ] **T3.3** : Créer `backend_worker/db/session.py`
  ```python
  """Session SQLAlchemy pour les workers."""
  from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
  from backend_worker.db.engine import create_worker_engine
  
  def get_worker_session() -> async_sessionmaker[AsyncSession]:
      """Retourne une factory de sessions pour les workers."""
      engine = create_worker_engine()
      return async_sessionmaker(engine, expire_on_commit=False)
  ```

- [ ] **T3.4** : Créer `backend_worker/db/repositories/base.py`
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

- [ ] **T3.5** : Créer `backend_worker/db/repositories/track_repository.py`
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

- [ ] **T3.6** : Migrer `insert.direct_batch` vers TaskIQ avec DB direct
  ```python
  # backend_worker/taskiq_tasks/insert.py
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

### Tâches Testeur

- [ ] **T3.7** : Créer `tests/unit/worker/db/test_repositories.py`
  ```python
  """Tests unitaires pour les repositories workers."""
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  
  @pytest.mark.asyncio
  async def test_track_repository_bulk_insert():
      """Test l'insertion en masse de tracks."""
      from backend_worker.db.repositories.track_repository import TrackRepository
      
      # Mock de la session
      mock_session = AsyncMock()
      mock_result = MagicMock()
      mock_result.fetchall.return_value = [(1,), (2,)]
      mock_session.execute.return_value = mock_result
      
      repo = TrackRepository(mock_session)
      tracks_data = [
          {"title": "Track 1", "path": "/path/1.mp3"},
          {"title": "Track 2", "path": "/path/2.mp3"}
      ]
      
      ids = await repo.bulk_insert_tracks(tracks_data)
      
      assert len(ids) == 2
      mock_session.execute.assert_called_once()
  ```

- [ ] **T3.8** : Créer `tests/integration/workers/test_taskiq_insert_integration.py`
  ```python
  """Tests d'intégration pour l'insertion TaskIQ avec DB direct."""
  import pytest
  
  @pytest.mark.asyncio
  async def test_insert_direct_batch_taskiq():
      """Test complet de l'insertion via TaskIQ."""
      # 1. Préparer les données de test
      # 2. Appeler la tâche TaskIQ
      # 3. Vérifier l'insertion en DB
      # 4. Vérifier les logs
      pass
  ```

- [ ] **T3.9** : Exécuter les tests de performance
  ```bash
  # Comparer les performances Celery vs TaskIQ vs DB direct
  python -m pytest tests/performance/benchmarks/test_insert_performance.py -v
  ```

### Livrables
- Couche DB worker opérationnelle
- Tâche insert migrée avec DB direct
- Tests unitaires et intégration passent
- Rapport de performance

### Validation
- [ ] Insertion fonctionne via API (fallback)
- [ ] Insertion fonctionne via DB direct (feature flag)
- [ ] Performance DB direct ≥ Performance API
- [ ] Pas de fuites de connexions DB
- [ ] Tests existants toujours verts (0 régression)

---

## Phase 4 — Migration Progressive du Cœur (5-10 jours)

### Objectif
Migrer les tâches critiques par lots.

### Ordre de Migration (par criticité croissante)
1. **Lot 1** : `maintenance.*` (non critique)
2. **Lot 2** : `covers.*` (faible criticité)
3. **Lot 3** : `metadata.*` (critique moyenne)
4. **Lot 4** : `batch.*` + `insert.*` (critique)
5. **Lot 5** : `scan.*` (très critique)
6. **Lot 6** : `vectorization.*` (critique)

### Pour Chaque Lot

#### Tâches Développeur
- [ ] Créer le module TaskIQ correspondant
- [ ] Ajouter le feature flag
- [ ] Implémenter le wrapper sync/async si nécessaire
- [ ] Ajouter les logs différenciés

#### Tâches Testeur
- [ ] Créer les tests unitaires
- [ ] Créer les tests d'intégration
- [ ] Exécuter les tests de non-régression
- [ ] Comparer les performances

### Livrables par Lot
- Tâche migrée et fonctionnelle
- Feature flag opérationnel
- Tests passent
- Rapport de validation

### Validation Globale Phase 4
- [ ] >80% tâches sur TaskIQ
- [ ] Tous les tests existants passent
- [ ] Performance stable ou meilleure
- [ ] Mémoire maîtrisée (profil RPi)

---

## Phase 5 — Décommission Celery (2-3 jours)

### Objectif
Supprimer Celery après validation complète.

### Prérequis
- Phase 4 validée
- 2 semaines sans incident majeur
- Tous les tests passent

### Tâches Développeur

- [ ] **T5.1** : Supprimer les imports Celery dans `backend/api/utils/`
  - Vérifier que plus aucun import Celery n'est utilisé
  - Remplacer par les appels TaskIQ

- [ ] **T5.2** : Supprimer `backend_worker/celery_app.py`
  - **UNIQUEMENT** après confirmation que plus aucune tâche ne l'utilise

- [ ] **T5.3** : Supprimer `backend_worker/celery_tasks.py`
  - **UNIQUEMENT** après migration complète

- [ ] **T5.4** : Supprimer `backend_worker/celery_beat_config.py`
  - Remplacer par le scheduler TaskIQ

- [ ] **T5.5** : Nettoyer `docker-compose.yml`
  - Supprimer les services `celery-worker` et `celery_beat`
  - Garder uniquement `taskiq-worker`

- [ ] **T5.6** : Mettre à jour la documentation
  - `README.md`
  - `docs/` (runbooks, architecture)

### Tâches Testeur

- [ ] **T5.7** : Exécuter la suite complète de tests
  ```bash
  python -m pytest tests/ -q --tb=no
  ```

- [ ] **T5.8** : Vérifier qu'aucun import Celery ne reste
  ```bash
  grep -r "from celery" backend/ backend_worker/ || echo "Aucun import Celery trouvé"
  ```

- [ ] **T5.9** : Vérifier que Docker démarre correctement
  ```bash
  docker-compose build
  docker-compose up -d
  docker-compose ps  # Vérifier que tous les services sont UP
  ```

### Livrables
- Runtime unique TaskIQ
- Documentation à jour
- Tests mis à jour et passent

### Validation
- [ ] `docker-compose up` démarre sans Celery
- [ ] Toutes les tâches fonctionnent via TaskIQ
- [ ] Tests existants passent (0 régression)
- [ ] Documentation à jour

---

## Phase 6 — Fusion Backend / Backend Worker (5-8 jours)

### Objectif
Fusionner les répertoires `backend/` et `backend_worker/` pour réunir toute la logique métier en un seul lieu, éliminant la duplication de code.

### Prérequis
- Phase 5 validée (Celery décommissionné)
- Runtime TaskIQ stable depuis 2 semaines
- Tous les tests passent

### Problématique Actuelle
- Duplication de logique entre `backend/services/` et `backend_worker/services/`
- Contrats de données implicites entre les deux modules
- Maintenance complexe avec code réparti

### Architecture Cible
```
backend/
├── api/                    # API FastAPI + GraphQL (inchangé)
├── services/               # Logique métier unifiée (fusionné)
│   ├── album_service.py
│   ├── artist_service.py
│   ├── track_service.py
│   ├── scan_service.py
│   ├── vectorization_service.py
│   ├── covers_service.py
│   ├── mir_service.py
│   └── ...
├── tasks/                  # Tâches TaskIQ (depuis backend_worker/tasks/)
│   ├── __init__.py
│   ├── maintenance_tasks.py
│   ├── audio_analysis_tasks.py
│   ├── covers_tasks.py
│   └── ...
├── workers/                # Workers spécialisés (depuis backend_worker/workers/)
│   ├── __init__.py
│   ├── scan/
│   ├── metadata/
│   ├── vectorization/
│   └── ...
├── models/                 # Modèles SQLAlchemy (depuis backend_worker/models/)
│   ├── __init__.py
│   └── ...
├── utils/                  # Utilitaires partagés
│   ├── logging.py
│   ├── redis_utils.py
│   └── ...
├── taskiq_app.py           # Configuration TaskIQ
├── taskiq_worker.py        # Point d'entrée worker
└── api_app.py              # Point d'entrée API
```

### Tâches Développeur

- [ ] **T6.1** : Auditer les duplications entre `backend/services/` et `backend_worker/services/`
  - Identifier les services dupliqués
  - Documenter les différences de signature
  - Prioriser les services à fusionner

- [ ] **T6.2** : Créer la structure cible dans `backend/`
  - Créer `backend/tasks/` (depuis `backend_worker/tasks/`)
  - Créer `backend/workers/` (depuis `backend_worker/workers/`)
  - Déplacer `backend_worker/models/` vers `backend/models/`

- [ ] **T6.3** : Fusionner les services dupliqués
  - Fusionner `backend/services/album_service.py` et `backend_worker/services/`
  - Fusionner `backend/services/artist_service.py` et `backend_worker/services/`
  - Fusionner les autres services dupliqués

- [ ] **T6.4** : Mettre à jour les imports dans toutes les tâches TaskIQ
  - Remplacer `backend_worker.tasks.*` par `backend.tasks.*`
  - Remplacer `backend_worker.workers.*` par `backend.workers.*`
  - Remplacer `backend_worker.models.*` par `backend.models.*`
  - Remplacer `backend_worker.services.*` par `backend.services.*`

- [ ] **T6.5** : Mettre à jour `backend/taskiq_app.py`
  - Inclure les nouvelles tâches depuis `backend.tasks.*`
  - Mettre à jour les imports

- [ ] **T6.6** : Mettre à jour `docker-compose.yml`
  - Supprimer le service `celery-worker` (déjà fait en Phase 5)
  - Mettre à jour le service `taskiq-worker` pour pointer vers `backend/`
  - Mettre à jour les volumes montés

- [ ] **T6.7** : Mettre à jour les Dockerfiles
  - `backend/Dockerfile` : inclure les tâches et workers
  - Supprimer `backend_worker/Dockerfile` (si encore présent)

- [ ] **T6.8** : Supprimer `backend_worker/` après validation
  - Vérifier qu'aucun import ne pointe vers `backend_worker/`
  - Supprimer le répertoire `backend_worker/`
  - Mettre à jour `.gitignore` si nécessaire

### Tâches Testeur

- [ ] **T6.9** : Exécuter la suite complète de tests
  ```bash
  python -m pytest tests/ -q --tb=no
  ```

- [ ] **T6.10** : Vérifier qu'aucun import `backend_worker` ne reste
  ```bash
  grep -r "from backend_worker" backend/ tests/ || echo "Aucun import backend_worker trouvé"
  grep -r "import backend_worker" backend/ tests/ || echo "Aucun import backend_worker trouvé"
  ```

- [ ] **T6.11** : Vérifier que Docker démarre correctement
  ```bash
  docker-compose build
  docker-compose up -d
  docker-compose ps
  ```

- [ ] **T6.12** : Vérifier que toutes les tâches TaskIQ fonctionnent
  - Tester chaque tâche migrée
  - Vérifier les logs
  - Valider les résultats

### Livrables
- Répertoire `backend/` unifié avec toute la logique métier
- Répertoire `backend_worker/` supprimé
- Tous les imports mis à jour
- Docker fonctionnel avec la nouvelle structure
- Tests passent sans régression

### Validation
- [ ] `docker-compose up` démarre avec la nouvelle structure
- [ ] Toutes les tâches TaskIQ fonctionnent
- [ ] Aucun import `backend_worker` ne reste
- [ ] Tests existants passent (0 régression)
- [ ] Documentation à jour

---

## 📊 Matrice de Suivi des Tests

| Phase | Tests Unitaires | Tests Intégration | Tests E2E | Régression |
|-------|----------------|-------------------|-----------|------------|
| 0 (Baseline) | ✅ 15+ | ✅ 6 | ✅ 3 | N/A |
| 1 (Socle) | ✅ +1 | ✅ 0 | ✅ 0 | ✅ 0 |
| 2 (Pilote) | ✅ +2 | ✅ +1 | ✅ 0 | ✅ 0 |
| 3 (DB Direct) | ✅ +3 | ✅ +2 | ✅ 0 | ✅ 0 |
| 4 (Migration) | ✅ +10 | ✅ +6 | ✅ +3 | ✅ 0 |
| 5 (Décommission) | ✅ 0 | ✅ 0 | ✅ 0 | ✅ 0 |
| 6 (Fusion) | ✅ 0 | ✅ 0 | ✅ 0 | ✅ 0 |

**Légende** : ✅ = Tests passent, +N = Nouveaux tests ajoutés

---

## 🔄 Workflow de Validation par Phase

### Pour Chaque Phase

1. **Développeur** :
   - Implémente les tâches de la phase
   - **Exécute ruff check** sur les fichiers modifiés
   - **Vérifie l'absence d'erreurs Pylance** dans VS Code
   - Exécute les tests unitaires localement
   - **Commit atomique** à la fin de chaque sous-tâche validée
   - Format de commit : `feat(taskiq): [description de la tâche]`

2. **Testeur** :
   - **Exécute ruff check** sur tous les fichiers modifiés
   - **Vérifie l'absence d'erreurs Pylance** dans VS Code
   - Exécute les tests unitaires
   - Exécute les tests d'intégration
   - Compare avec la baseline
   - Documente les anomalies

3. **Lead Développeur** :
   - **Exécute ruff check** sur tous les fichiers modifiés
   - **Vérifie l'absence d'erreurs Pylance** dans VS Code
   - Revue les résultats
   - Valide ou demande des corrections
   - **Crée un tag Git** à la fin de chaque phase validée
   - Format de tag : `phase-X-complete` (ex: `phase-1-complete`)

### Stratégie de Commits par Phase

#### Phase 0 — Audit
```bash
git add docs/plans/taskiq_migrations/audit/
git commit -m "docs(taskiq): audit complet des tâches Celery et baseline tests"
git tag phase-0-complete
```

#### Phase 1 — Socle TaskIQ
```bash
# Sous-tâche T1.1 : Dépendances
git add backend_worker/requirements.txt
git commit -m "chore(taskiq): ajout dépendances TaskIQ (core + redis + fastapi)"

# Sous-tâche T1.2 : Configuration TaskIQ
git add backend_worker/taskiq_app.py
git commit -m "feat(taskiq): création configuration TaskIQ avec broker Redis"

# Sous-tâche T1.3 : Worker TaskIQ
git add backend_worker/taskiq_worker.py
git commit -m "feat(taskiq): création worker TaskIQ async"

# Sous-tâche T1.4 : Docker Compose
git add docker-compose.yml
git commit -m "feat(taskiq): ajout service taskiq-worker dans Docker Compose"

# Sous-tâche T1.5 : Variables d'environnement
git add .env.example
git commit -m "chore(taskiq): ajout variables d'environnement TaskIQ"

# Sous-tâche T1.6 : Tests unitaires
git add tests/unit/worker/test_taskiq_app.py
git commit -m "test(taskiq): ajout tests unitaires configuration TaskIQ"

# Tag de fin de phase
git tag phase-1-complete
```

#### Phase 2 — Migration Pilote
```bash
# Sous-tâche T2.1 : Package tâches TaskIQ
git add backend_worker/taskiq_tasks/__init__.py
git commit -m "feat(taskiq): création package tâches TaskIQ"

# Sous-tâche T2.2 : Tâche maintenance
git add backend_worker/taskiq_tasks/maintenance.py
git commit -m "feat(taskiq): migration tâche cleanup_old_data vers TaskIQ"

# Sous-tâche T2.3 : Feature flag
git add backend_worker/celery_tasks.py
git commit -m "feat(taskiq): ajout feature flag USE_TASKIQ_FOR_MAINTENANCE"

# Sous-tâche T2.4 : Wrapper sync/async
git add backend_worker/taskiq_utils.py
git commit -m "feat(taskiq): ajout wrapper sync/async pour TaskIQ"

# Sous-tâche T2.5 : Tests unitaires maintenance
git add tests/unit/worker/test_taskiq_maintenance.py
git commit -m "test(taskiq): ajout tests unitaires tâche maintenance TaskIQ"

# Sous-tâche T2.6 : Tests intégration
git add tests/integration/workers/test_taskiq_maintenance_integration.py
git commit -m "test(taskiq): ajout tests intégration maintenance TaskIQ"

# Tag de fin de phase
git tag phase-2-complete
```

#### Phase 3 — Accès DB Direct
```bash
# Sous-tâche T3.1 : Package DB
git add backend_worker/db/__init__.py
git commit -m "feat(taskiq): création package couche DB worker"

# Sous-tâche T3.2 : Engine DB
git add backend_worker/db/engine.py
git commit -m "feat(taskiq): ajout engine SQLAlchemy async pour workers"

# Sous-tâche T3.3 : Session DB
git add backend_worker/db/session.py
git commit -m "feat(taskiq): ajout factory sessions SQLAlchemy workers"

# Sous-tâche T3.4 : Repository base
git add backend_worker/db/repositories/base.py
git commit -m "feat(taskiq): ajout repository base avec garde-fous"

# Sous-tâche T3.5 : Repository tracks
git add backend_worker/db/repositories/track_repository.py
git commit -m "feat(taskiq): ajout repository tracks avec bulk insert"

# Sous-tâche T3.6 : Tâche insert DB direct
git add backend_worker/taskiq_tasks/insert.py
git commit -m "feat(taskiq): migration insert.direct_batch avec accès DB direct"

# Sous-tâche T3.7 : Tests repositories
git add tests/unit/worker/db/test_repositories.py
git commit -m "test(taskiq): ajout tests unitaires repositories workers"

# Sous-tâche T3.8 : Tests intégration insert
git add tests/integration/workers/test_taskiq_insert_integration.py
git commit -m "test(taskiq): ajout tests intégration insertion DB direct"

# Tag de fin de phase
git tag phase-3-complete
```

#### Phase 4 — Migration Progressive
```bash
# Pour chaque lot de migration
git add backend_worker/taskiq_tasks/<module>.py
git commit -m "feat(taskiq): migration tâches <module> vers TaskIQ"

git add tests/unit/worker/test_taskiq_<module>.py
git commit -m "test(taskiq): ajout tests unitaires tâches <module>"

git add tests/integration/workers/test_taskiq_<module>_integration.py
git commit -m "test(taskiq): ajout tests intégration tâches <module>"

# Tag de fin de phase
git tag phase-4-complete
```

#### Phase 5 — Décommission Celery
```bash
# Suppression progressive
git rm backend_worker/celery_app.py
git commit -m "refactor(taskiq): suppression celery_app.py (remplacé par taskiq_app.py)"

git rm backend_worker/celery_tasks.py
git commit -m "refactor(taskiq): suppression celery_tasks.py (tâches migrées vers TaskIQ)"

git rm backend_worker/celery_beat_config.py
git commit -m "refactor(taskiq): suppression celery_beat_config.py (scheduler TaskIQ)"

# Nettoyage Docker Compose
git add docker-compose.yml
git commit -m "refactor(taskiq): suppression services Celery dans Docker Compose"

# Documentation
git add README.md docs/
git commit -m "docs(taskiq): mise à jour documentation post-migration TaskIQ"

# Tag de fin de phase
git tag phase-5-complete
```

#### Phase 6 — Fusion Backend / Backend Worker
```bash
# Sous-tâche T6.1 : Audit des duplications
git add docs/plans/taskiq_migrations/audit/duplications_services.md
git commit -m "docs(taskiq): audit des duplications backend/backend_worker"

# Sous-tâche T6.2 : Création structure cible
git add backend/tasks/ backend/workers/
git commit -m "refactor(taskiq): création structure tasks/ et workers/ dans backend/"

# Sous-tâche T6.3 : Fusion services
git add backend/services/
git commit -m "refactor(taskiq): fusion services backend et backend_worker"

# Sous-tâche T6.4 : Mise à jour imports
git add backend/ tests/
git commit -m "refactor(taskiq): mise à jour imports backend_worker vers backend"

# Sous-tâche T6.5 : Configuration TaskIQ
git add backend/taskiq_app.py backend/taskiq_worker.py
git commit -m "refactor(taskiq): déplacement configuration TaskIQ vers backend/"

# Sous-tâche T6.6 : Docker Compose
git add docker-compose.yml
git commit -m "refactor(taskiq): mise à jour Docker Compose pour backend unifié"

# Sous-tâche T6.7 : Dockerfiles
git add backend/Dockerfile
git commit -m "refactor(taskiq): mise à jour Dockerfile backend unifié"

# Sous-tâche T6.8 : Suppression backend_worker/
git rm -r backend_worker/
git commit -m "refactor(taskiq): suppression répertoire backend_worker/ (fusionné dans backend/)"

# Documentation
git add README.md docs/
git commit -m "docs(taskiq): mise à jour documentation post-fusion backend"

# Tag de fin de migration complète
git tag taskiq-migration-complete
```

### Procédure de Rollback par Phase

#### Rollback Phase 1
```bash
# Revenir à l'état avant Phase 1
git checkout phase-0-complete
git checkout -b rollback/phase-1

# Ou revenir à un commit spécifique
git revert <commit-hash>  # Annuler un commit spécifique
git tag phase-1-rollback
```

#### Rollback Phase 2
```bash
# Revenir à l'état avant Phase 2
git checkout phase-1-complete
git checkout -b rollback/phase-2

# Désactiver le feature flag
export USE_TASKIQ_FOR_MAINTENANCE=false
docker-compose restart celery-worker taskiq-worker

git tag phase-2-rollback
```

#### Rollback Phase 3
```bash
# Revenir à l'état avant Phase 3
git checkout phase-2-complete
git checkout -b rollback/phase-3

# Désactiver le feature flag DB
export WORKER_DIRECT_DB_ENABLED=false
docker-compose restart taskiq-worker

git tag phase-3-rollback
```

#### Rollback Phase 4
```bash
# Revenir à l'état avant Phase 4
git checkout phase-3-complete
git checkout -b rollback/phase-4

# Désactiver tous les feature flags TaskIQ
export USE_TASKIQ_FOR_SCAN=false
export USE_TASKIQ_FOR_METADATA=false
export USE_TASKIQ_FOR_BATCH=false
export USE_TASKIQ_FOR_INSERT=false
export USE_TASKIQ_FOR_VECTORIZATION=false
docker-compose restart celery-worker taskiq-worker

git tag phase-4-rollback
```

#### Rollback Phase 5
```bash
# Revenir à l'état avant Phase 5
git checkout phase-4-complete
git checkout -b rollback/phase-5

# Restaurer les fichiers Celery supprimés
git checkout phase-4-complete -- backend_worker/celery_app.py
git checkout phase-4-complete -- backend_worker/celery_tasks.py
git checkout phase-4-complete -- backend_worker/celery_beat_config.py
git checkout phase-4-complete -- docker-compose.yml

git add .
git commit -m "rollback(taskiq): restauration complète Celery après Phase 5"
git tag phase-5-rollback
```

#### Rollback Phase 6
```bash
# Revenir à l'état avant Phase 6
git checkout phase-5-complete
git checkout -b rollback/phase-6

# Restaurer le répertoire backend_worker/
git checkout phase-5-complete -- backend_worker/

# Restaurer les imports originaux
git checkout phase-5-complete -- backend/
git checkout phase-5-complete -- tests/
git checkout phase-5-complete -- docker-compose.yml

git add .
git commit -m "rollback(taskiq): restauration backend_worker/ après Phase 6"
git tag phase-6-rollback
```

### Critères de Passage à la Phase Suivante

- [ ] **Ruff check passe** sans erreur sur tous les fichiers modifiés
- [ ] **Pylance ne signale aucune erreur** dans VS Code
- [ ] Tous les tests de la phase passent
- [ ] Aucune régression sur les tests existants
- [ ] Performance stable ou meilleure
- [ ] Documentation à jour
- [ ] Code revu et approuvé
- [ ] **Commit atomique pour chaque sous-tâche**
- [ ] **Tag Git créé pour la phase**
- [ ] **Rollback testé et documenté**

---

## 📁 Structure des Fichiers

```
docs/plans/taskiq_migrations/
├── PLAN_AMELIORE_MIGRATION_TASKIQ.md  # Ce fichier
├── audit/
│   ├── taches_celery.md
│   ├── dependances_taches.md
│   ├── baseline_tests_unitaires.txt
│   └── baseline_tests_integration.txt
├── phase_1/
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── resultats_tests.md
├── phase_2/
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── resultats_tests.md
├── phase_3/
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── resultats_tests.md
├── phase_4/
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── resultats_tests.md
├── phase_5/
│   ├── briefing_developpeur.md
│   ├── briefing_testeur.md
│   └── resultats_tests.md
└── phase_6/
    ├── briefing_developpeur.md
    ├── briefing_testeur.md
    └── resultats_tests.md
```

---

## 🚨 Procédure de Rollback

### Si Régression Détectée

1. **Immédiatement** :
   ```bash
   # Désactiver le feature flag
   export USE_TASKIQ_FOR_<TACHE>=false
   
   # Redémarrer les services
   docker-compose restart celery-worker taskiq-worker
   ```

2. **Investigation** :
   - Analyser les logs `[TASKIQ]` vs `[CELERY]`
   - Identifier la cause de la régression
   - Documenter dans `docs/plans/taskiq_migrations/incidents/`

3. **Correction** :
   - Corriger le code
   - Ajouter un test pour éviter la régression
   - Re-valider avant de réactiver le feature flag

---

## 📝 Checklist de Validation Finale

### Avant Chaque Phase
- [ ] Baseline des tests exécutée
- [ ] Feature flags configurés
- [ ] Documentation à jour

### Après Chaque Phase
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Tests existants passent (0 régression)
- [ ] Performance stable ou meilleure
- [ ] Logs différenciés visibles
- [ ] Documentation à jour

### Avant Phase 5 (Décommission)
- [ ] 2 semaines sans incident
- [ ] Tous les tests passent
- [ ] Performance validée
- [ ] Documentation complète
- [ ] Rollback testé et documenté

---

## 🎯 Objectifs de Qualité

- **Zéro régression** sur les tests existants
- **Performance** : latence ≤ 110% de Celery
- **Mémoire** : consommation ≤ 100% de Celery
- **Fiabilité** : taux de succès ≥ 99%
- **Observabilité** : logs structurés et différenciés

---

## 📞 Contacts et Responsabilités

- **Lead Développeur** : Validation globale, revue de code
- **Développeur** : Implémentation des tâches
- **Testeur** : Validation des tests, détection des régressions
- **DevOps** : Configuration Docker, monitoring

---

*Dernière mise à jour : 2026-03-20*
*Version : 1.0*
*Statut : En cours de validation*
