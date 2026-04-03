# Plan de Délégation — Migration Celery → TaskIQ (SoniqueBay)

## 📋 Résumé Exécutif

Ce plan de délégation structure l'attribution des tâches pour toutes les phases (1 à 6) de la migration TaskIQ, avec attribution par rôle, workflow de validation et procédure de rollback.

**Phase 0 (Audit)** : ✅ Terminée  
**Phases 1-6** : Plan de délégation détaillé ci-dessous

---

## 🎯 Vue d'ensemble — Rôles et Responsabilités

### Rôles Définis

| Rôle | Responsabilités | Livrables |
|------|-----------------|-----------|
| **Lead Développeur** | Validation globale, revue de code, décision de passage de phase | Tags Git, validation phases |
| **Développeur** | Implémentation des tâches, tests unitaires, documentation technique | Code fonctionnel, tests unitaires |
| **Testeur** | Validation des tests, détection des régressions, rapports de tests | Rapports de tests, anomalies |
| **DevOps** | Configuration Docker, monitoring, CI/CD | Services Docker, variables d'environnement |

### Matrice de Responsabilités par Phase

| Phase | Lead Dev | Développeur | Testeur | DevOps |
|-------|----------|-------------|---------|--------|
| 0 (Audit) | ✅ Validation | ✅ Documentation | ✅ Baseline tests | ✅ Config Redis |
| 1 (Socle) | ✅ Validation | ✅ Implémentation | ✅ Tests | ✅ Docker |
| 2 (Pilote) | ✅ Validation | ✅ Implémentation | ✅ Tests | ✅ Monitoring |
| 3 (DB Direct) | ✅ Validation | ✅ Implémentation | ✅ Tests | ✅ Config DB |
| 4 (Migration) | ✅ Validation | ✅ Implémentation | ✅ Tests | ✅ Optimisation |
| 5 (Décommission) | ✅ Validation | ✅ Suppression | ✅ Vérification | ✅ Nettoyage Docker |
| 6 (Fusion) | ✅ Validation | ✅ Fusion | ✅ Tests | ✅ Docker unifié |

---

## 📦 Matrice des Stories par Phase et Rôle

### Phase 1 — Socle TaskIQ Minimal (2-3 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-1** | Développeur | Ajouter dépendances TaskIQ dans `requirements.txt` | Aucune | `pip install` réussit, Celery intact |
| **DEV-2** | Développeur | Créer `taskiq_app.py` et `taskiq_worker.py` | DEV-1 | Module importable, worker démarre |
| **DEV-3** | Développeur | Ajouter service Docker dans `docker-compose.yml` | DEV-2 | 4 conteneurs démarrent |
| **DEV-4** | Développeur | Ajouter variables d'environnement dans `.env.example` | DEV-2 | Variables documentées |
| **TEST-1** | Testeur | Créer tests unitaires `test_taskiq_app.py` | DEV-2 | Tests passent, couverture >80% |
| **TEST-2** | Testeur | Exécuter tests non-régression | TEST-1 | 0 régression vs baseline |
| **DEVOPS-1** | DevOps | Configurer service Docker TaskIQ | DEV-2 | `docker-compose up` fonctionne |
| **DEVOPS-2** | DevOps | Configurer variables d'environnement | DEV-4 | Variables disponibles |

**Livrables Phase 1** :
- Worker TaskIQ opérationnel en parallèle de Celery
- Tests unitaires TaskIQ passent
- Tests existants Celery toujours verts (0 régression)
- Docker démarre les 4 conteneurs

---

### Phase 2 — Migration Pilote (2-4 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-5** | Développeur | Créer package `taskiq_tasks/` | Phase 1 | Package importable |
| **DEV-6** | Développeur | Migrer tâche `cleanup_old_data` | DEV-5 | Tâche fonctionne mode Celery et TaskIQ |
| **DEV-7** | Développeur | Ajouter feature flag `USE_TASKIQ_FOR_MAINTENANCE` | DEV-6 | Flag opérationnel |
| **DEV-8** | Développeur | Créer wrapper sync/async `taskiq_utils.py` | Phase 1 | Wrapper fonctionnel |
| **DEV-9** | Développeur | Ajouter logging différencié | DEV-6 | Logs `[TASKIQ]` visibles |
| **TEST-3** | Testeur | Créer tests unitaires maintenance | DEV-6 | Tests passent |
| **TEST-4** | Testeur | Créer tests intégration maintenance | TEST-3 | Tests E2E passent |
| **TEST-5** | Testeur | Exécuter tests comparatifs Celery vs TaskIQ | TEST-4 | Résultats comparables |
| **DEVOPS-3** | DevOps | Configurer monitoring TaskIQ | DEV-6 | Logs structurés |

**Livrables Phase 2** :
- Tâche maintenance migrée et fonctionnelle
- Feature flag opérationnel
- Tests unitaires et intégration passent
- Rapport comparatif Celery vs TaskIQ

---

### Phase 3 — Accès DB Direct Worker (3-5 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-10** | Développeur | Créer package `db/` (engine, session) | Phase 2 | Engine s'initialise |
| **DEV-11** | Développeur | Créer `repositories/base.py` avec garde-fous | DEV-10 | Timeout et retry fonctionnent |
| **DEV-12** | Développeur | Créer `repositories/track_repository.py` | DEV-11 | Bulk insert fonctionne |
| **DEV-13** | Développeur | Migrer `insert.direct_batch` avec DB direct | DEV-12 | Insertion DB direct fonctionne |
| **DEV-14** | Développeur | Ajouter feature flag `WORKER_DIRECT_DB_ENABLED` | DEV-13 | Flag opérationnel |
| **TEST-6** | Testeur | Créer tests unitaires repositories | DEV-12 | Tests passent |
| **TEST-7** | Testeur | Créer tests intégration insert DB direct | DEV-13 | Tests E2E passent |
| **TEST-8** | Testeur | Exécuter tests performance | TEST-7 | Performance DB ≥ API |
| **DEVOPS-4** | DevOps | Configurer `WORKER_DATABASE_URL` | DEV-10 | Variable disponible |

**Livrables Phase 3** :
- Couche DB worker opérationnelle
- Tâche insert migrée avec DB direct
- Tests unitaires et intégration passent
- Rapport de performance

---

### Phase 4 — Migration Progressive du Cœur (5-10 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-15** | Développeur | Migrer tâches vectorisation (Lot 1) | Phase 3 | Vectorisation fonctionne |
| **DEV-16** | Développeur | Migrer tâches métadonnées (Lot 2) | DEV-15 | Métadonnées fonctionnent |
| **DEV-17** | Développeur | Migrer tâches batch et scan (Lot 3) | DEV-16 | Batch et scan fonctionnent |
| **DEV-18** | Développeur | Ajouter feature flags par tâche | DEV-15,16,17 | Flags opérationnels |
| **TEST-9** | Testeur | Créer tests unitaires par lot | DEV-15,16,17 | Tests passent |
| **TEST-10** | Testeur | Créer tests intégration par lot | TEST-9 | Tests E2E passent |
| **TEST-11** | Testeur | Exécuter tests non-régression globale | TEST-10 | 0 régression |
| **DEVOPS-5** | DevOps | Optimiser Docker pour RPi4 | DEV-17 | Mémoire maîtrisée |

**Livrables Phase 4** :
- >80% tâches sur TaskIQ
- Tous les tests existants passent
- Performance stable ou meilleure
- Mémoire maîtrisée (profil RPi)

---

### Phase 5 — Décommission Celery (2-3 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-19** | Développeur | Supprimer imports Celery dans `backend/api/utils/` | Phase 4 + 2 semaines | Aucun import Celery restant |
| **DEV-20** | Développeur | Supprimer `celery_app.py` | DEV-19 | Fichier supprimé |
| **DEV-21** | Développeur | Supprimer `celery_tasks.py` | DEV-20 | Fichier supprimé |
| **DEV-22** | Développeur | Supprimer `celery_beat_config.py` | DEV-21 | Fichier supprimé |
| **DEV-23** | Développeur | Nettoyer imports et documentation | DEV-22 | Documentation à jour |
| **TEST-12** | Testeur | Exécuter suite complète de tests | DEV-23 | Tous les tests passent |
| **TEST-13** | Testeur | Vérifier absence imports Celery | DEV-23 | `grep` ne trouve rien |
| **DEVOPS-6** | DevOps | Nettoyer `docker-compose.yml` | DEV-23 | Services Celery supprimés |
| **DEVOPS-7** | DevOps | Mettre à jour Dockerfile | DEV-23 | Image optimisée |

**Livrables Phase 5** :
- Runtime unique TaskIQ
- Documentation à jour
- Tests mis à jour et passent
- Docker optimisé

---

### Phase 6 — Fusion Backend / Backend Worker (5-8 jours)

| Story | Rôle | Tâches | Dépendances | Critères d'Acceptation |
|-------|------|--------|-------------|------------------------|
| **DEV-24** | Développeur | Auditer duplications `backend/` vs `backend_worker/` | Phase 5 | Audit documenté |
| **DEV-25** | Développeur | Créer structure cible `backend/tasks/` et `backend/workers/` | DEV-24 | Structure créée |
| **DEV-26** | Développeur | Fusionner services dupliqués | DEV-25 | Services unifiés |
| **DEV-27** | Développeur | Mettre à jour imports TaskIQ | DEV-26 | Imports fonctionnels |
| **DEV-28** | Développeur | Mettre à jour `taskiq_app.py` et `taskiq_worker.py` | DEV-27 | Configuration fonctionnelle |
| **DEV-29** | Développeur | Supprimer `backend_worker/` après validation | DEV-28 | Répertoire supprimé |
| **TEST-14** | Testeur | Exécuter suite complète de tests | DEV-29 | Tous les tests passent |
| **TEST-15** | Testeur | Vérifier absence imports `backend_worker` | DEV-29 | `grep` ne trouve rien |
| **DEVOPS-8** | DevOps | Mettre à jour Docker Compose | DEV-28 | Services unifiés |
| **DEVOPS-9** | DevOps | Mettre à jour Dockerfiles | DEV-28 | Images optimisées |

**Livrables Phase 6** :
- Répertoire `backend/` unifié avec toute la logique métier
- Répertoire `backend_worker/` supprimé
- Tous les imports mis à jour
- Docker fonctionnel avec la nouvelle structure
- Tests passent sans régression

---

## 🔄 Workflow de Validation par Phase

### Cycle de Validation Standard

```
┌─────────────────────────────────────────────────────────────┐
│                    PRÉPARATION                               │
│  Lead Dev → Briefings + Baseline tests                      │
│  Dev → Lecture briefings + Préparation environnement        │
│  Testeur → Lecture briefings + Préparation environnement    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    DÉVELOPPEMENT                             │
│  Dev → Implémentation tâche par tâche                       │
│  Dev → Ruff check + Pylance + Tests unitaires               │
│  Dev → Commit atomique après chaque sous-tâche              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION TESTEUR                        │
│  Testeur → Ruff check + Pylance                             │
│  Testeur → Tests unitaires TaskIQ + Celery (non-régression) │
│  Testeur → Tests intégration workers                        │
│  Testeur → Vérification Docker                              │
│  Testeur → Rapport de tests                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    VALIDATION LEAD DEV                       │
│  Lead Dev → Ruff check + Pylance                            │
│  Lead Dev → Revue code + Rapport tests                      │
│  Lead Dev → Validation critères d'acceptation               │
│  Lead Dev → Tag Git (phase-X-complete)                      │
│  Lead Dev → Décision passage phase suivante                 │
└─────────────────────────────────────────────────────────────┘
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

### Stratégie de Commits par Phase

Format de commit : `<type>(scope): message`

Exemples :
```bash
# Phase 1
git commit -m "chore(taskiq): ajout dépendances TaskIQ (core + redis + fastapi)"
git commit -m "feat(taskiq): création configuration TaskIQ avec broker Redis"
git commit -m "test(taskiq): ajout tests unitaires configuration TaskIQ"

# Phase 2
git commit -m "feat(taskiq): migration tâche cleanup_old_data vers TaskIQ"
git commit -m "feat(taskiq): ajout feature flag USE_TASKIQ_FOR_MAINTENANCE"

# Tag de fin de phase
git tag phase-1-complete
```

---

## 📊 Plan de Suivi et Reporting

### Tableau de Bord de Suivi par Phase

| Phase | Stories Dev | Stories Test | Stories DevOps | Statut Global |
|-------|-------------|--------------|----------------|---------------|
| 0 (Audit) | 4 | 2 | 1 | ✅ Terminée |
| 1 (Socle) | 4 | 2 | 2 | ⏳ En attente |
| 2 (Pilote) | 5 | 3 | 1 | ⏳ En attente |
| 3 (DB Direct) | 5 | 3 | 1 | ⏳ En attente |
| 4 (Migration) | 4 | 3 | 1 | ⏳ En attente |
| 5 (Décommission) | 5 | 2 | 2 | ⏳ En attente |
| 6 (Fusion) | 6 | 2 | 2 | ⏳ En attente |

### Métriques de Suivi

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| **Taux de réussite tests** | ≥ 100% | Tests passants / Tests totaux |
| **Régressions introduites** | 0 | Tests échoués vs baseline |
| **Anomalies bloquantes** | 0 | Anomalies critiques |
| **Performance** | ≤ 110% de Celery | Latence TaskIQ / Latence Celery |
| **Mémoire** | ≤ 100% de Celery | Mémoire TaskIQ / Mémoire Celery |
| **Fiabilité** | ≥ 99% | Tâches succès / Tâches totales |

### Rapports Hebdomadaires

**Contenu du rapport** :
1. **Avancement** : Stories terminées / Stories prévues
2. **Tests** : Taux de réussite, régressions détectées
3. **Anomalies** : Liste des anomalies ouvertes/fermées
4. **Performance** : Comparaison Celery vs TaskIQ
5. **Risques** : Risques identifiés et mitigations
6. **Prochaines étapes** : Stories planifiées pour la semaine

**Template de rapport** :
```markdown
# Rapport Hebdomadaire — Migration TaskIQ
## Semaine du [DATE]

### Avancement
- Stories terminées : [NOMBRE]
- Stories en cours : [NOMBRE]
- Stories prévues : [NOMBRE]

### Tests
- Taux de réussite : [POURCENTAGE]%
- Régressions détectées : [NOMBRE]
- Anomalies ouvertes : [NOMBRE]

### Performance
- Latence TaskIQ : [VALEUR]ms
- Latence Celery : [VALEUR]ms
- Ratio : [POURCENTAGE]%

### Risques
- [RISQUE 1] : [MITIGATION]
- [RISQUE 2] : [MITIGATION]

### Prochaines étapes
- [STORY 1]
- [STORY 2]
```

---

## 🚨 Procédure de Rollback

### Rollback par Phase

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

### Procédure de Rollback Immédiat (Feature Flag)

Si régression détectée en production :

```bash
# 1. Immédiatement désactiver le feature flag
export USE_TASKIQ_FOR_<TACHE>=false

# 2. Redémarrer les services
docker-compose restart celery-worker taskiq-worker

# 3. Vérifier que Celery reprend le relais
docker logs soniquebay-celery-worker --tail 100

# 4. Documenter l'incident
# Créer : docs/plans/taskiq_migrations/incidents/[DATE]_[TACHE].md
```

### Checklist de Rollback

- [ ] Identifier la phase concernée
- [ ] Identifier la tâche problématique
- [ ] Désactiver le feature flag si applicable
- [ ] Redémarrer les services Docker
- [ ] Vérifier que Celery reprend le relais
- [ ] Documenter l'incident
- [ ] Analyser la cause racine
- [ ] Corriger le code
- [ ] Ajouter un test pour éviter la régression
- [ ] Re-valider avant de réactiver le feature flag

---

## 📅 Planning des Sprints

### Sprint 1 (3 jours) — Socle TaskIQ
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-1 | Dev | 0.5j | Aucune |
| DEV-2 | Dev | 1j | DEV-1 |
| DEV-3 | Dev | 0.5j | DEV-2 |
| DEVOPS-1 | DevOps | 0.5j | DEV-2 |
| TEST-1 | Test | 0.5j | DEV-2 |

**Livrable** : TaskIQ opérationnel en parallèle de Celery

### Sprint 2 (3 jours) — Feature Flags & Wrapper
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-4 | Dev | 0.5j | DEV-2 |
| DEV-5 | Dev | 0.5j | DEV-2 |
| DEVOPS-2 | DevOps | 0.25j | DEV-4 |

**Livrable** : Système de feature flags opérationnel

### Sprint 3 (3 jours) — Migration Pilote
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-6 | Dev | 1j | DEV-4, DEV-5 |
| DEV-7 | Dev | 1j | DEV-6 |
| TEST-2 | Test | 0.5j | DEV-6 |
| TEST-3 | Test | 1j | TEST-2 |

**Livrable** : 2 tâches migrées avec feature flags

### Sprint 4 (4 jours) — Accès DB Direct
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-8 | Dev | 1j | DEV-2 |
| DEV-9 | Dev | 1j | DEV-8 |
| DEV-10 | Dev | 1.5j | DEV-9 |
| TEST-4 | Test | 1j | DEV-9 |
| TEST-5 | Test | 1j | DEV-10 |

**Livrable** : Insertion DB direct opérationnelle

### Sprint 5 (6 jours) — Migration Progressive
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-11 | Dev | 2j | DEV-10 |
| DEV-12 | Dev | 2j | DEV-11 |
| DEV-13 | Dev | 2j | DEV-12 |

**Livrable** : >80% tâches sur TaskIQ

### Sprint 6 (2 jours) — Décommission Celery
| Story | Rôle | Durée | Dépendances |
|-------|------|-------|-------------|
| DEV-14 | Dev | 1j | DEV-13 + 2 semaines |
| DEVOPS-4 | DevOps | 0.5j | DEV-14 |
| DEVOPS-5 | DevOps | 1j | DEV-14 |

**Livrable** : Runtime unique TaskIQ

---

## 📁 Structure des Fichiers de Délégation

```
docs/plans/taskiq_migrations/
├── PLAN_DELEGATION.md              # Ce fichier
├── PLAN_AMELIORE_MIGRATION_TASKIQ.md  # Plan détaillé (existant)
├── PLAN_OPTIMISE_STORIES.md        # Plan optimisé stories (existant)
├── WORKFLOW_VALIDATION.md          # Workflow validation (existant)
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
├── phase_1/
│   ├── briefing_developpeur.md     # Existant
│   ├── briefing_testeur.md         # Existant
│   └── resultats_tests.md
├── phase_2/
│   ├── briefing_developpeur.md     # Existant
│   ├── briefing_testeur.md         # Existant
│   └── resultats_tests.md
├── phase_3/
│   ├── briefing_developpeur.md     # Existant
│   ├── briefing_testeur.md         # Existant
│   └── resultats_tests.md
├── phase_4/
│   ├── briefing_developpeur.md     # Existant
│   ├── briefing_testeur.md         # Existant
│   └── resultats_tests.md
├── phase_5/
│   ├── briefing_developpeur.md     # Existant
│   ├── briefing_testeur.md         # Existant
│   └── resultats_tests.md
└── phase_6/
    ├── briefing_developpeur.md     # Existant
    ├── briefing_testeur.md         # Existant
    └── resultats_tests.md
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

### Lead Développeur
- **Responsabilités** :
  - Validation globale
  - Revue de code
  - Décision de passage à la phase suivante
  - Communication avec l'équipe
  - Création des tags Git

### Développeur
- **Responsabilités** :
  - Implémentation des stories DEV
  - Tests unitaires locaux
  - Documentation technique
  - Correction des anomalies
  - Commits atomiques

### Testeur
- **Responsabilités** :
  - Validation des stories TEST
  - Détection des régressions
  - Documentation des anomalies
  - Rapports de tests
  - Vérification Docker

### DevOps
- **Responsabilités** :
  - Configuration Docker
  - Monitoring
  - CI/CD
  - Variables d'environnement
  - Optimisation RPi4

---

## ✅ Checklist de Validation Finale

### Avant Chaque Phase
- [ ] Baseline des tests exécutée
- [ ] Feature flags configurés
- [ ] Documentation à jour
- [ ] Briefings distribués

### Après Chaque Phase
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Tests existants passent (0 régression)
- [ ] Performance stable ou meilleure
- [ ] Logs différenciés visibles
- [ ] Documentation à jour
- [ ] Tag Git créé
- [ ] Rollback testé

### Avant Phase 5 (Décommission)
- [ ] 2 semaines sans incident
- [ ] Tous les tests passent
- [ ] Performance validée
- [ ] Documentation complète
- [ ] Rollback testé et documenté

---

*Dernière mise à jour : 2026-03-21*
*Version : 1.0*
*Statut : En cours de validation*
