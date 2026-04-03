# Plan Optimisé — Migration Celery → TaskIQ (SoniqueBay)

## 📋 Résumé Exécutif

Ce plan重构 le travail en **petites stories indépendantes** (1-2 jours max) pour permettre un développement incrémental sans risque de plantage systématique. Chaque story est **autonome, testable et déployable**.

---

## 🎯 Principes de重构

### 1. **Stories Atomiques**
- Chaque story = 1 fonctionnalité complète
- Durée : 1-2 jours maximum
- Livrable : Code fonctionnel + tests

### 2. **Séparation des Rôles**
- **Développeur** : Code métier, tests unitaires
- **Testeur** : Tests d'intégration, validation
- **DevOps** : Docker, CI/CD, monitoring

### 3. **Validation Continue**
- Chaque story validée avant de passer à la suivante
- Tests automatiques à chaque commit
- Feature flags pour bascule progressive

### 4. **Zéro Régression**
- Baseline des tests existants (Phase 0 ✅)
- Tests de non-régression à chaque story
- Rollback immédiat si problème

---

## 📦 Stories Organisées par Rôle

---

## 🧑‍💻 STORIES DÉVELOPPEUR

### Story DEV-1 : Dépendances TaskIQ
**Rôle** : Développeur  
**Durée** : 0.5 jour  
**Dépendances** : Aucune  

#### Objectif
Ajouter les dépendances TaskIQ sans impacter Celery.

#### Tâches
- [ ] Modifier `backend_worker/requirements.txt`
  - Ajouter : `taskiq[redis]>=0.11.0`
  - Ajouter : `taskiq-fastapi>=0.5.0`
  - **NE PAS SUPPRIMER** les dépendances Celery

#### Critères d'Acceptation
- [ ] `pip install -r requirements.txt` fonctionne
- [ ] Aucune dépendance Celery supprimée
- [ ] Tests existants passent

#### Validation
```bash
python -m pytest tests/unit/worker -q --tb=no
```

---

### Story DEV-2 : Configuration TaskIQ
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-1  

#### Objectif
Créer la configuration TaskIQ qui coexiste avec Celery.

#### Tâches
- [ ] Créer `backend_worker/taskiq_app.py`
  - Broker Redis (DB 1 pour isolation)
  - Backend de résultats
  - Handlers d'événements (logging)
- [ ] Créer `backend_worker/taskiq_worker.py`
  - Point d'entrée worker async
  - Import des tâches (vide initialement)

#### Critères d'Acceptation
- [ ] `taskiq_app.py` s'importe sans erreur
- [ ] `taskiq_worker.py` démarre (sans tâches)
- [ ] Celery fonctionne toujours
- [ ] Tests existants passent

#### Validation
```bash
python -c "from backend_worker.taskiq_app import broker; print('OK')"
python -m pytest tests/unit/worker -q --tb=no
```

---

### Story DEV-3 : Tests Unitaires TaskIQ
**Rôle** : Développeur  
**Durée** : 0.5 jour  
**Dépendances** : DEV-2  

#### Objectif
Créer les tests unitaires pour la configuration TaskIQ.

#### Tâches
- [ ] Créer `tests/unit/worker/test_taskiq_app.py`
  - Test initialisation broker
  - Test initialisation backend résultats
  - Test coexistence avec Celery

#### Critères d'Acceptation
- [ ] Tests TaskIQ passent
- [ ] Tests Celery existants passent
- [ ] Couverture de code > 80%

#### Validation
```bash
python -m pytest tests/unit/worker/test_taskiq_app.py -v
python -m pytest tests/unit/worker -q --tb=no
```

---

### Story DEV-4 : Feature Flags
**Rôle** : Développeur  
**Durée** : 0.5 jour  
**Dépendances** : DEV-2  

#### Objectif
Implémenter le système de feature flags pour bascule progressive.

#### Tâches
- [ ] Créer `backend_worker/feature_flags.py`
  - Lecture des variables d'environnement
  - Flags par tâche : `USE_TASKIQ_FOR_*`
  - Flag global : `ENABLE_CELERY_FALLBACK`
- [ ] Ajouter les variables dans `.env.example`
  - `TASKIQ_BROKER_URL=redis://redis:6379/1`
  - `TASKIQ_RESULT_BACKEND=redis://redis:6379/1`
  - `USE_TASKIQ_FOR_MAINTENANCE=false`
  - `USE_TASKIQ_FOR_COVERS=false`
  - `ENABLE_CELERY_FALLBACK=true`

#### Critères d'Acceptation
- [ ] Flags lisibles via `os.getenv()`
- [ ] Valeurs par défaut sécurisées (tout sur Celery)
- [ ] Documentation dans `.env.example`

#### Validation
```bash
python -c "from backend_worker.feature_flags import get_flag; print(get_flag('USE_TASKIQ_FOR_MAINTENANCE'))"
```

---

### Story DEV-5 : Wrapper Sync/Async
**Rôle** : Développeur  
**Durée** : 0.5 jour  
**Dépendances** : DEV-2  

#### Objectif
Créer un wrapper pour appeler des tâches TaskIQ depuis du code synchrone.

#### Tâches
- [ ] Créer `backend_worker/taskiq_utils.py`
  - Fonction `run_taskiq_sync(task_func, *args, **kwargs)`
  - Gestion de la boucle d'événements
  - Gestion des erreurs

#### Critères d'Acceptation
- [ ] Wrapper fonctionnel
- [ ] Gestion propre des erreurs
- [ ] Tests unitaires

#### Validation
```bash
python -m pytest tests/unit/worker/test_taskiq_utils.py -v
```

---

### Story DEV-6 : Tâche Maintenance (Pilote)
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-4, DEV-5  

#### Objectif
Migrer la tâche `maintenance.cleanup_old_data` vers TaskIQ (non critique).

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/__init__.py`
- [ ] Créer `backend_worker/taskiq_tasks/maintenance.py`
  - Tâche `cleanup_old_data_task`
  - Même logique que Celery
- [ ] Modifier `backend_worker/celery_tasks.py`
  - Ajouter le feature flag
  - Wrapper vers TaskIQ si flag=true

#### Critères d'Acceptation
- [ ] Tâche fonctionne en mode Celery (flag=false)
- [ ] Tâche fonctionne en mode TaskIQ (flag=true)
- [ ] Logs différenciés `[CELERY]` vs `[TASKIQ]`
- [ ] Tests existants passent

#### Validation
```bash
# Mode Celery
USE_TASKIQ_FOR_MAINTENANCE=false python -m pytest tests/unit/worker/test_cleanup.py -v

# Mode TaskIQ
USE_TASKIQ_FOR_MAINTENANCE=true python -m pytest tests/unit/worker/test_cleanup.py -v
```

---

### Story DEV-7 : Tâche Covers (Pilote 2)
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-6  

#### Objectif
Migrer la tâche `covers.extract_embedded` vers TaskIQ.

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/covers.py`
  - Tâche `extract_embedded_task`
- [ ] Modifier `backend_worker/celery_tasks.py`
  - Ajouter le feature flag `USE_TASKIQ_FOR_COVERS`

#### Critères d'Acceptation
- [ ] Tâche fonctionne en mode Celery
- [ ] Tâche fonctionne en mode TaskIQ
- [ ] Tests existants passent

---

### Story DEV-8 : Couche DB Worker (Engine)
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-2  

#### Objectif
Créer la couche d'accès DB pour les workers TaskIQ.

#### Tâches
- [ ] Créer `backend_worker/db/__init__.py`
- [ ] Créer `backend_worker/db/engine.py`
  - Engine SQLAlchemy async
  - NullPool pour éviter les fuites
  - Timeouts stricts
- [ ] Créer `backend_worker/db/session.py`
  - Factory de sessions

#### Critères d'Acceptation
- [ ] Engine s'initialise
- [ ] Sessions fonctionnelles
- [ ] Pas de fuite de connexions

#### Validation
```bash
python -m pytest tests/unit/worker/db/test_engine.py -v
```

---

### Story DEV-9 : Repository Tracks
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-8  

#### Objectif
Créer le repository pour les tracks avec accès direct DB.

#### Tâches
- [ ] Créer `backend_worker/db/repositories/base.py`
  - Classe de base avec garde-fous
  - Timeout sur les requêtes
  - Retry avec backoff
- [ ] Créer `backend_worker/db/repositories/track_repository.py`
  - `bulk_insert_tracks()`
  - `get_track_by_path()`

#### Critères d'Acceptation
- [ ] Insertion en masse fonctionnelle
- [ ] Timeout respecté
- [ ] Tests unitaires passent

---

### Story DEV-10 : Tâche Insert DB Direct
**Rôle** : Développeur  
**Durée** : 1.5 jours  
**Dépendances** : DEV-9  

#### Objectif
Migrer `insert.direct_batch` avec accès DB direct.

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/insert.py`
  - Tâche `insert_direct_batch_task`
  - Utilise TrackRepository
- [ ] Ajouter le feature flag `USE_TASKIQ_FOR_INSERT`
- [ ] Ajouter le flag `WORKER_DIRECT_DB_ENABLED`

#### Critères d'Acceptation
- [ ] Insertion via API (fallback)
- [ ] Insertion via DB direct (flag)
- [ ] Performance DB direct ≥ API
- [ ] Tests existants passent

---

### Story DEV-11 : Migration Progressive (Lot 1)
**Rôle** : Développeur  
**Durée** : 2 jours  
**Dépendances** : DEV-10  

#### Objectif
Migrer les tâches de vectorisation vers TaskIQ.

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/vectorization.py`
  - `calculate_task`
  - `batch_task`
- [ ] Ajouter le feature flag `USE_TASKIQ_FOR_VECTORIZATION`

#### Critères d'Acceptation
- [ ] Vectorisation fonctionne en mode Celery
- [ ] Vectorisation fonctionne en mode TaskIQ
- [ ] Performance comparable

---

### Story DEV-12 : Migration Progressive (Lot 2)
**Rôle** : Développeur  
**Durée** : 2 jours  
**Dépendances** : DEV-11  

#### Objectif
Migrer les tâches de métadonnées vers TaskIQ.

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/metadata.py`
  - `extract_batch_task`
  - `enrich_batch_task`
- [ ] Ajouter le feature flag `USE_TASKIQ_FOR_METADATA`

---

### Story DEV-13 : Migration Progressive (Lot 3)
**Rôle** : Développeur  
**Durée** : 2 jours  
**Dépendances** : DEV-12  

#### Objectif
Migrer les tâches de batch et scan vers TaskIQ.

#### Tâches
- [ ] Créer `backend_worker/taskiq_tasks/batch.py`
  - `process_entities_task`
- [ ] Créer `backend_worker/taskiq_tasks/scan.py`
  - `discovery_task`
- [ ] Ajouter les feature flags

---

### Story DEV-14 : Décommission Celery
**Rôle** : Développeur  
**Durée** : 1 jour  
**Dépendances** : DEV-13 + 2 semaines sans incident  

#### Objectif
Supprimer Celery après validation complète.

#### Tâches
- [ ] Supprimer `backend_worker/celery_app.py`
- [ ] Supprimer `backend_worker/celery_tasks.py`
- [ ] Supprimer `backend_worker/celery_beat_config.py`
- [ ] Nettoyer les imports

#### Critères d'Acceptation
- [ ] Aucun import Celery restant
- [ ] Toutes les tâches fonctionnent via TaskIQ
- [ ] Tests existants passent

---

## 🧪 STORIES TESTEUR

### Story TEST-1 : Tests Unitaires TaskIQ
**Rôle** : Testeur  
**Durée** : 0.5 jour  
**Dépendances** : DEV-2  

#### Objectif
Créer les tests unitaires pour la configuration TaskIQ.

#### Tâches
- [ ] Créer `tests/unit/worker/test_taskiq_app.py`
  - Test initialisation broker
  - Test initialisation backend
  - Test coexistence Celery

#### Critères d'Acceptation
- [ ] Tests passent
- [ ] Couverture > 80%

---

### Story TEST-2 : Tests Maintenance TaskIQ
**Rôle** : Testeur  
**Durée** : 0.5 jour  
**Dépendances** : DEV-6  

#### Objectif
Créer les tests pour la tâche maintenance migrée.

#### Tâches
- [ ] Créer `tests/unit/worker/test_taskiq_maintenance.py`
  - Test mode Celery
  - Test mode TaskIQ
  - Test feature flag

---

### Story TEST-3 : Tests Intégration Maintenance
**Rôle** : Testeur  
**Durée** : 1 jour  
**Dépendances** : TEST-2  

#### Objectif
Créer les tests d'intégration pour la maintenance.

#### Tâches
- [ ] Créer `tests/integration/workers/test_taskiq_maintenance_integration.py`
  - Test end-to-end
  - Test logs différenciés

---

### Story TEST-4 : Tests DB Worker
**Rôle** : Testeur  
**Durée** : 1 jour  
**Dépendances** : DEV-9  

#### Objectif
Créer les tests pour la couche DB worker.

#### Tâches
- [ ] Créer `tests/unit/worker/db/test_repositories.py`
  - Test bulk insert
  - Test timeout
  - Test retry

---

### Story TEST-5 : Tests Insert DB Direct
**Rôle** : Testeur  
**Durée** : 1 jour  
**Dépendances** : DEV-10  

#### Objectif
Créer les tests pour l'insertion DB direct.

#### Tâches
- [ ] Créer `tests/integration/workers/test_taskiq_insert_integration.py`
  - Test insertion via API
  - Test insertion via DB
  - Test comparaison performance

---

### Story TEST-6 : Tests de Non-Régression Globale
**Rôle** : Testeur  
**Durée** : 0.5 jour  
**Dépendances** : Chaque story DEV  

#### Objectif
Exécuter les tests de non-régression après chaque story.

#### Tâches
- [ ] Exécuter la baseline des tests
- [ ] Comparer avec la référence Phase 0
- [ ] Documenter les anomalies

#### Validation
```bash
python -m pytest tests/unit/worker -q --tb=no
python -m pytest tests/integration/workers -q --tb=no
```

---

## 🔧 STORIES DEVOPS

### Story DEVOPS-1 : Service Docker TaskIQ
**Rôle** : DevOps  
**Durée** : 0.5 jour  
**Dépendances** : DEV-2  

#### Objectif
Ajouter le service TaskIQ dans Docker Compose.

#### Tâches
- [ ] Modifier `docker-compose.yml`
  - Ajouter le service `taskiq-worker`
  - Même image que `celery-worker`
  - Commande : `python -m backend_worker.taskiq_worker`
  - Variables d'environnement TaskIQ
  - Dépendances : redis, api-service

#### Critères d'Acceptation
- [ ] `docker-compose up` démarre 4 conteneurs
- [ ] Logs TaskIQ visibles
- [ ] Aucune erreur

#### Validation
```bash
docker-compose build
docker-compose up -d
docker-compose ps
docker-compose logs taskiq-worker
```

---

### Story DEVOPS-2 : Variables d'Environnement
**Rôle** : DevOps  
**Durée** : 0.25 jour  
**Dépendances** : DEV-4  

#### Objectif
Configurer les variables d'environnement TaskIQ.

#### Tâches
- [ ] Modifier `.env.example`
  - Ajouter les variables TaskIQ
  - Documenter les valeurs par défaut

---

### Story DEVOPS-3 : Monitoring TaskIQ
**Rôle** : DevOps  
**Durée** : 1 jour  
**Dépendances** : DEVOPS-1  

#### Objectif
Ajouter le monitoring pour TaskIQ.

#### Tâches
- [ ] Ajouter les métriques TaskIQ
- [ ] Configurer les health checks
- [ ] Ajouter les logs structurés

---

### Story DEVOPS-4 : Mise à jour Dockerfile
**Rôle** : DevOps  
**Durée** : 0.5 jour  
**Dépendances** : DEV-14  

#### Objectif
Mettre à jour le Dockerfile après décommission Celery.

#### Tâches
- [ ] Modifier `backend_worker/Dockerfile`
  - Supprimer les dépendances Celery
  - Optimiser la taille de l'image

---

### Story DEVOPS-5 : Fusion Backend (Docker)
**Rôle** : DevOps  
**Durée** : 1 jour  
**Dépendances** : DEV-14  

#### Objectif
Fusionner les services Docker après décommission Celery.

#### Tâches
- [ ] Modifier `docker-compose.yml`
  - Supprimer les services Celery
  - Mettre à jour le service TaskIQ
- [ ] Mettre à jour les Dockerfiles

---

## 📊 Planning des Sprints

### Sprint 1 (3 jours) — Socle TaskIQ
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-1 | Dev | 0.5j | Aucune |
| DEV-2 | Dev | 1j | DEV-1 |
| DEV-3 | Dev | 0.5j | DEV-2 |
| DEVOPS-1 | DevOps | 0.5j | DEV-2 |
| TEST-1 | Test | 0.5j | DEV-2 |

**Livrable** : TaskIQ opérationnel en parallèle de Celery

---

### Sprint 2 (3 jours) — Feature Flags & Wrapper
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-4 | Dev | 0.5j | DEV-2 |
| DEV-5 | Dev | 0.5j | DEV-2 |
| DEVOPS-2 | DevOps | 0.25j | DEV-4 |

**Livrable** : Système de feature flags opérationnel

---

### Sprint 3 (3 jours) — Migration Pilote
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-6 | Dev | 1j | DEV-4, DEV-5 |
| DEV-7 | Dev | 1j | DEV-6 |
| TEST-2 | Test | 0.5j | DEV-6 |
| TEST-3 | Test | 1j | TEST-2 |

**Livrable** : 2 tâches migrées avec feature flags

---

### Sprint 4 (4 jours) — Accès DB Direct
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-8 | Dev | 1j | DEV-2 |
| DEV-9 | Dev | 1j | DEV-8 |
| DEV-10 | Dev | 1.5j | DEV-9 |
| TEST-4 | Test | 1j | DEV-9 |
| TEST-5 | Test | 1j | DEV-10 |

**Livrable** : Insertion DB direct opérationnelle

---

### Sprint 5 (6 jours) — Migration Progressive
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-11 | Dev | 2j | DEV-10 |
| DEV-12 | Dev | 2j | DEV-11 |
| DEV-13 | Dev | 2j | DEV-12 |

**Livrable** : >80% tâches sur TaskIQ

---

### Sprint 6 (2 jours) — Décommission Celery
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-14 | Dev | 1j | DEV-13 + 2 semaines |
| DEVOPS-4 | DevOps | 0.5j | DEV-14 |
| DEVOPS-5 | DevOps | 1j | DEV-14 |

**Livrable** : Runtime unique TaskIQ

---

## 🔄 Workflow de Validation

### Pour Chaque Story

1. **Développeur** :
   - Implémente la story
   - Exécute `ruff check` sur les fichiers modifiés
   - Exécute les tests unitaires
   - Commit atomique

2. **Testeur** :
   - Exécute les tests unitaires
   - Exécute les tests d'intégration
   - Compare avec la baseline
   - Documente les anomalies

3. **DevOps** (si Docker) :
   - Vérifie que `docker-compose up` fonctionne
   - Vérifie les logs
   - Vérifie les health checks

4. **Lead Développeur** :
   - Revue les résultats
   - Valide ou demande des corrections
   - Crée un tag Git

### Critères de Passage

- [ ] `ruff check` passe sans erreur
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Tests existants passent (0 régression)
- [ ] `docker-compose up` fonctionne (si applicable)
- [ ] Code revu et approuvé

---

## 📁 Structure des Fichiers

```
docs/plans/taskiq_migrations/
├── PLAN_AMELIORE_MIGRATION_TASKIQ.md  # Plan détaillé (existant)
├── PLAN_OPTIMISE_STORIES.md          # Ce fichier (plan optimisé)
├── stories/
│   ├── dev/
│   │   ├── DEV-1_dependances.md
│   │   ├── DEV-2_configuration.md
│   │   └── ...
│   ├── test/
│   │   ├── TEST-1_unitaires_taskiq.md
│   │   ├── TEST-2_maintenance.md
│   │   └── ...
│   └── devops/
│       ├── DEVOPS-1_docker.md
│       ├── DEVOPS-2_env.md
│       └── ...
└── ...
```

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
- **Développeur** : Implémentation des stories DEV
- **Testeur** : Validation des stories TEST
- **DevOps** : Configuration Docker, monitoring (stories DEVOPS)

---

*Dernière mise à jour : 2026-03-21*
*Version : 2.0 (Plan Optimisé)*
*Statut : En cours de validation*
