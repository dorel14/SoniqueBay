# Stories Organisées — Migration TaskIQ

## 📋 Résumé Exécutif

Ce document organise les **45+ stories** de la migration TaskIQ par rôle (Développeur, Testeur, DevOps) et dépendances, facilitant la délégation et le suivi.

**Phase 0 (Audit)** : ✅ Terminée  
**Phases 1-6** : Organisation détaillée ci-dessous

---

## 🎯 Vue d'ensemble — Rôles et Responsabilités

| Rôle | Nombre Stories | Responsabilités |
|------|----------------|-----------------|
| **Développeur** | 29 stories | Implémentation, tests unitaires, documentation technique |
| **Testeur** | 16 stories | Validation tests, détection régressions, rapports |
| **DevOps** | 5 stories | Configuration Docker, monitoring, CI/CD |

---

## 📦 Matrice des Stories par Rôle

### 🔧 Développeur (29 stories)

#### Phase 1 — Socle TaskIQ Minimal (5 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-1** | Ajouter dépendances TaskIQ dans `requirements.txt` | Aucune | `pip install` réussit, Celery intact |
| **DEV-2** | Créer `taskiq_app.py` et `taskiq_worker.py` | DEV-1 | Module importable, worker démarre |
| **DEV-3** | Ajouter service Docker dans `docker-compose.yml` | DEV-2 | 4 conteneurs démarrent |
| **DEV-4** | Ajouter variables d'environnement dans `.env.example` | DEV-2 | Variables documentées |
| **DEV-5** | Créer tests unitaires `test_taskiq_app.py` | DEV-2 | Tests passent, couverture >80% |

#### Phase 2 — Migration Pilote (5 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-6** | Créer package `taskiq_tasks/` | Phase 1 | Package importable |
| **DEV-7** | Migrer tâche `cleanup_old_data` | DEV-6 | Tâche fonctionne mode Celery et TaskIQ |
| **DEV-8** | Ajouter feature flag `USE_TASKIQ_FOR_MAINTENANCE` | DEV-7 | Flag opérationnel |
| **DEV-9** | Créer wrapper sync/async `taskiq_utils.py` | Phase 1 | Wrapper fonctionnel |
| **DEV-10** | Ajouter logging différencié | DEV-7 | Logs `[TASKIQ]` visibles |

#### Phase 3 — Accès DB Direct Worker (5 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-11** | Créer package `db/` (engine, session) | Phase 2 | Engine s'initialise |
| **DEV-12** | Créer `repositories/base.py` avec garde-fous | DEV-11 | Timeout et retry fonctionnent |
| **DEV-13** | Créer `repositories/track_repository.py` | DEV-12 | Bulk insert fonctionne |
| **DEV-14** | Migrer `insert.direct_batch` avec DB direct | DEV-13 | Insertion DB direct fonctionne |
| **DEV-15** | Ajouter feature flag `WORKER_DIRECT_DB_ENABLED` | DEV-14 | Flag opérationnel |

#### Phase 4 — Migration Progressive du Cœur (4 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-16** | Migrer tâches vectorisation (Lot 1) | Phase 3 | Vectorisation fonctionne |
| **DEV-17** | Migrer tâches métadonnées (Lot 2) | DEV-16 | Métadonnées fonctionnent |
| **DEV-18** | Migrer tâches batch et scan (Lot 3) | DEV-17 | Batch et scan fonctionnent |
| **DEV-19** | Ajouter feature flags par tâche | DEV-16,17,18 | Flags opérationnels |

#### Phase 5 — Décommission Celery (5 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-20** | Supprimer imports Celery dans `backend/api/utils/` | Phase 4 + 2 semaines | Aucun import Celery restant |
| **DEV-21** | Supprimer `celery_app.py` | DEV-20 | Fichier supprimé |
| **DEV-22** | Supprimer `celery_tasks.py` | DEV-21 | Fichier supprimé |
| **DEV-23** | Supprimer `celery_beat_config.py` | DEV-22 | Fichier supprimé |
| **DEV-24** | Nettoyer imports et documentation | DEV-23 | Documentation à jour |

#### Phase 6 — Fusion Backend / Backend Worker (5 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEV-25** | Auditer duplications `backend/` vs `backend_worker/` | Phase 5 | Audit documenté |
| **DEV-26** | Créer structure cible `backend/tasks/` et `backend/workers/` | DEV-25 | Structure créée |
| **DEV-27** | Fusionner services dupliqués | DEV-26 | Services unifiés |
| **DEV-28** | Mettre à jour imports TaskIQ | DEV-27 | Imports fonctionnels |
| **DEV-29** | Supprimer `backend_worker/` après validation | DEV-28 | Répertoire supprimé |

---

### 🧪 Testeur (16 stories)

#### Phase 1 — Socle TaskIQ Minimal (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-1** | Créer tests unitaires `test_taskiq_app.py` | DEV-2 | Tests passent, couverture >80% |
| **TEST-2** | Exécuter tests non-régression | TEST-1 | 0 régression vs baseline |

#### Phase 2 — Migration Pilote (3 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-3** | Créer tests unitaires maintenance | DEV-7 | Tests passent |
| **TEST-4** | Créer tests intégration maintenance | TEST-3 | Tests E2E passent |
| **TEST-5** | Exécuter tests comparatifs Celery vs TaskIQ | TEST-4 | Résultats comparables |

#### Phase 3 — Accès DB Direct Worker (3 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-6** | Créer tests unitaires repositories | DEV-13 | Tests passent |
| **TEST-7** | Créer tests intégration insert DB direct | DEV-14 | Tests E2E passent |
| **TEST-8** | Exécuter tests performance | TEST-7 | Performance DB ≥ API |

#### Phase 4 — Migration Progressive du Cœur (3 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-9** | Créer tests unitaires par lot | DEV-16,17,18 | Tests passent |
| **TEST-10** | Créer tests intégration par lot | TEST-9 | Tests E2E passent |
| **TEST-11** | Exécuter tests non-régression globale | TEST-10 | 0 régression |

#### Phase 5 — Décommission Celery (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-12** | Exécuter suite complète de tests | DEV-24 | Tous les tests passent |
| **TEST-13** | Vérifier absence imports Celery | DEV-24 | `grep` ne trouve rien |

#### Phase 6 — Fusion Backend / Backend Worker (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **TEST-14** | Exécuter suite complète de tests | DEV-29 | Tous les tests passent |
| **TEST-15** | Vérifier absence imports `backend_worker` | DEV-29 | `grep` ne trouve rien |

---

### ⚙️ DevOps (5 stories)

#### Phase 1 — Socle TaskIQ Minimal (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-1** | Configurer service Docker TaskIQ | DEV-2 | `docker-compose up` fonctionne |
| **DEVOPS-2** | Configurer variables d'environnement | DEV-4 | Variables disponibles |

#### Phase 2 — Migration Pilote (1 story)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-3** | Configurer monitoring TaskIQ | DEV-7 | Logs structurés |

#### Phase 3 — Accès DB Direct Worker (1 story)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-4** | Configurer `WORKER_DATABASE_URL` | DEV-11 | Variable disponible |

#### Phase 4 — Migration Progressive du Cœur (1 story)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-5** | Optimiser Docker pour RPi4 | DEV-18 | Mémoire maîtrisée |

#### Phase 5 — Décommission Celery (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-6** | Nettoyer `docker-compose.yml` | DEV-24 | Services Celery supprimés |
| **DEVOPS-7** | Mettre à jour Dockerfile | DEV-24 | Image optimisée |

#### Phase 6 — Fusion Backend / Backend Worker (2 stories)

| Story | Tâches | Dépendances | Critères d'Acceptation |
|-------|--------|-------------|------------------------|
| **DEVOPS-8** | Mettre à jour Docker Compose | DEV-28 | Services unifiés |
| **DEVOPS-9** | Mettre à jour Dockerfiles | DEV-28 | Images optimisées |

---

## 🔗 Graphe des Dépendances

### Diagramme des Dépendances (Mermaid)

```mermaid
graph TD
    subgraph Phase 1
        DEV-1 --> DEV-2
        DEV-2 --> DEV-3
        DEV-2 --> DEV-4
        DEV-2 --> DEV-5
        DEV-2 --> DEVOPS-1
        DEV-4 --> DEVOPS-2
        DEV-2 --> TEST-1
        TEST-1 --> TEST-2
    end

    subgraph Phase 2
        DEV-6 --> DEV-7
        DEV-7 --> DEV-8
        DEV-7 --> DEV-10
        DEV-7 --> DEVOPS-3
        DEV-7 --> TEST-3
        TEST-3 --> TEST-4
        TEST-4 --> TEST-5
    end

    subgraph Phase 3
        DEV-11 --> DEV-12
        DEV-12 --> DEV-13
        DEV-13 --> DEV-14
        DEV-14 --> DEV-15
        DEV-11 --> DEVOPS-4
        DEV-13 --> TEST-6
        DEV-14 --> TEST-7
        TEST-7 --> TEST-8
    end

    subgraph Phase 4
        DEV-16 --> DEV-17
        DEV-17 --> DEV-18
        DEV-18 --> DEV-19
        DEV-18 --> DEVOPS-5
        DEV-16 --> TEST-9
        DEV-17 --> TEST-9
        DEV-18 --> TEST-9
        TEST-9 --> TEST-10
        TEST-10 --> TEST-11
    end

    subgraph Phase 5
        DEV-20 --> DEV-21
        DEV-21 --> DEV-22
        DEV-22 --> DEV-23
        DEV-23 --> DEV-24
        DEV-24 --> DEVOPS-6
        DEV-24 --> DEVOPS-7
        DEV-24 --> TEST-12
        DEV-24 --> TEST-13
    end

    subgraph Phase 6
        DEV-25 --> DEV-26
        DEV-26 --> DEV-27
        DEV-27 --> DEV-28
        DEV-28 --> DEV-29
        DEV-28 --> DEVOPS-8
        DEV-28 --> DEVOPS-9
        DEV-29 --> TEST-14
        DEV-29 --> TEST-15
    end

    Phase 1 --> Phase 2
    Phase 2 --> Phase 3
    Phase 3 --> Phase 4
    Phase 4 --> Phase 5
    Phase 5 --> Phase 6
```

### Criticité des Dépendances

| Dépendance | Criticité | Impact si Bloquée |
|------------|-----------|-------------------|
| DEV-1 → DEV-2 | 🔴 Critique | Aucune configuration TaskIQ possible |
| DEV-2 → DEV-3 | 🔴 Critique | Pas de service Docker TaskIQ |
| DEV-6 → DEV-7 | 🔴 Critique | Aucune tâche migrée |
| DEV-11 → DEV-12 | 🔴 Critique | Pas d'accès DB direct |
| DEV-13 → DEV-14 | 🔴 Critique | Insertion DB impossible |
| DEV-20 → DEV-21 | 🟡 Haute | Imports Celery restants |
| DEV-25 → DEV-26 | 🟡 Haute | Structure cible non créée |
| TEST-1 → TEST-2 | 🟡 Haute | Non-régression non validée |
| TEST-3 → TEST-4 | 🟡 Haute | Intégration non validée |
| TEST-9 → TEST-10 | 🟡 Haute | Intégration non validée |

### Points de Blocage

| Point de Blocage | Phase | Stories Affectées | Mitigation |
|------------------|-------|-------------------|------------|
| Configuration Redis DB 1 | 1 | DEV-2, DEVOPS-1 | Vérifier Redis avant démarrage |
| Feature flags non fonctionnels | 2 | DEV-8, DEV-7 | Tests unitaires flags |
| Timeouts DB non respectés | 3 | DEV-12, DEV-14 | Tests de timeout |
| Régression tests existants | 4 | TEST-11, TEST-12 | Baseline tests stricte |
| Imports Celery restants | 5 | DEV-20, TEST-13 | Grep automatisé |
| Services dupliqués non fusionnés | 6 | DEV-27, DEV-28 | Audit préalable |

---

## 📅 Planning des Sprints

### Sprint 1 (3 jours) — Phase 1 : Socle TaskIQ

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-1 | Dev | 0.5j | Aucune | ⬜ |
| DEV-2 | Dev | 1j | DEV-1 | ⬜ |
| DEV-3 | Dev | 0.5j | DEV-2 | ⬜ |
| DEVOPS-1 | DevOps | 0.5j | DEV-2 | ⬜ |
| TEST-1 | Test | 0.5j | DEV-2 | ⬜ |
| DEV-4 | Dev | 0.25j | DEV-2 | ⬜ |
| DEVOPS-2 | DevOps | 0.25j | DEV-4 | ⬜ |
| TEST-2 | Test | 0.5j | TEST-1 | ⬜ |

**Livrable** : TaskIQ opérationnel en parallèle de Celery

---

### Sprint 2 (3 jours) — Phase 2 : Migration Pilote

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-6 | Dev | 0.5j | Phase 1 | ⬜ |
| DEV-7 | Dev | 1j | DEV-6 | ⬜ |
| DEV-8 | Dev | 0.5j | DEV-7 | ⬜ |
| DEV-9 | Dev | 0.5j | Phase 1 | ⬜ |
| DEV-10 | Dev | 0.25j | DEV-7 | ⬜ |
| DEVOPS-3 | DevOps | 0.5j | DEV-7 | ⬜ |
| TEST-3 | Test | 0.5j | DEV-7 | ⬜ |
| TEST-4 | Test | 1j | TEST-3 | ⬜ |
| TEST-5 | Test | 0.5j | TEST-4 | ⬜ |

**Livrable** : Tâche maintenance migrée avec feature flag

---

### Sprint 3 (4 jours) — Phase 3 : Accès DB Direct

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-11 | Dev | 1j | Phase 2 | ⬜ |
| DEV-12 | Dev | 1j | DEV-11 | ⬜ |
| DEV-13 | Dev | 1j | DEV-12 | ⬜ |
| DEV-14 | Dev | 1j | DEV-13 | ⬜ |
| DEV-15 | Dev | 0.5j | DEV-14 | ⬜ |
| DEVOPS-4 | DevOps | 0.5j | DEV-11 | ⬜ |
| TEST-6 | Test | 0.5j | DEV-13 | ⬜ |
| TEST-7 | Test | 1j | DEV-14 | ⬜ |
| TEST-8 | Test | 1j | TEST-7 | ⬜ |

**Livrable** : Insertion DB direct opérationnelle

---

### Sprint 4 (6 jours) — Phase 4 : Migration Progressive

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-16 | Dev | 2j | Phase 3 | ⬜ |
| DEV-17 | Dev | 2j | DEV-16 | ⬜ |
| DEV-18 | Dev | 2j | DEV-17 | ⬜ |
| DEV-19 | Dev | 1j | DEV-16,17,18 | ⬜ |
| DEVOPS-5 | DevOps | 1j | DEV-18 | ⬜ |
| TEST-9 | Test | 1j | DEV-16,17,18 | ⬜ |
| TEST-10 | Test | 1j | TEST-9 | ⬜ |
| TEST-11 | Test | 1j | TEST-10 | ⬜ |

**Livrable** : >80% tâches sur TaskIQ

---

### Sprint 5 (3 jours) — Phase 5 : Décommission Celery

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-20 | Dev | 0.5j | Phase 4 + 2 semaines | ⬜ |
| DEV-21 | Dev | 0.5j | DEV-20 | ⬜ |
| DEV-22 | Dev | 0.5j | DEV-21 | ⬜ |
| DEV-23 | Dev | 0.5j | DEV-22 | ⬜ |
| DEV-24 | Dev | 0.5j | DEV-23 | ⬜ |
| DEVOPS-6 | DevOps | 0.5j | DEV-24 | ⬜ |
| DEVOPS-7 | DevOps | 0.5j | DEV-24 | ⬜ |
| TEST-12 | Test | 1j | DEV-24 | ⬜ |
| TEST-13 | Test | 0.5j | DEV-24 | ⬜ |

**Livrable** : Runtime unique TaskIQ

---

### Sprint 6 (5 jours) — Phase 6 : Fusion Backend

| Story | Rôle | Durée | Dépendances | Statut |
|-------|------|-------|-------------|--------|
| DEV-25 | Dev | 1j | Phase 5 | ⬜ |
| DEV-26 | Dev | 1j | DEV-25 | ⬜ |
| DEV-27 | Dev | 2j | DEV-26 | ⬜ |
| DEV-28 | Dev | 1j | DEV-27 | ⬜ |
| DEV-29 | Dev | 0.5j | DEV-28 | ⬜ |
| DEVOPS-8 | DevOps | 0.5j | DEV-28 | ⬜ |
| DEVOPS-9 | DevOps | 0.5j | DEV-28 | ⬜ |
| TEST-14 | Test | 1j | DEV-29 | ⬜ |
| TEST-15 | Test | 0.5j | DEV-29 | ⬜ |

**Livrable** : Répertoire `backend/` unifié

---

## ✅ Checklists de Préparation par Phase

### Phase 1 — Socle TaskIQ Minimal

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 1
- [ ] Vérifier que Redis est accessible (DB 0 et DB 1)
- [ ] Préparer l'environnement de développement
- [ ] Vérifier les imports Celery existants
- [ ] Créer une branche `feat/phase-1-socle-taskiq`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 1
- [ ] Exécuter la baseline des tests (31 unitaires + 6 intégration)
- [ ] Sauvegarder les résultats dans `docs/plans/taskiq_migrations/audit/`
- [ ] Préparer les tests unitaires TaskIQ
- [ ] Vérifier que pytest est fonctionnel

#### Préparation DevOps
- [ ] Vérifier que Docker est fonctionnel
- [ ] Vérifier que `docker-compose.yml` est valide
- [ ] Préparer les variables d'environnement
- [ ] Vérifier les limites de ressources RPi4

#### Critères de Démarrage
- [ ] Phase 0 (Audit) terminée et validée
- [ ] Baseline des tests établie
- [ ] Configuration Redis documentée
- [ ] Briefings distribués à tous les rôles

---

### Phase 2 — Migration Pilote

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 2
- [ ] Vérifier que Phase 1 est validée (tag `phase-1-complete`)
- [ ] Analyser les tâches Celery existantes (`celery_tasks.py`)
- [ ] Identifier la tâche `cleanup_old_data` à migrer
- [ ] Créer une branche `feat/phase-2-migration-pilote`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 2
- [ ] Exécuter les tests Phase 1 (non-régression)
- [ ] Préparer les tests unitaires maintenance
- [ ] Préparer les tests d'intégration maintenance
- [ ] Vérifier que les feature flags sont testables

#### Préparation DevOps
- [ ] Vérifier que le service TaskIQ fonctionne
- [ ] Préparer le monitoring TaskIQ
- [ ] Vérifier les logs structurés
- [ ] Préparer les variables d'environnement feature flags

#### Critères de Démarrage
- [ ] Phase 1 validée (tag `phase-1-complete`)
- [ ] Tests Phase 1 passent (0 régression)
- [ ] Service TaskIQ opérationnel
- [ ] Briefings distribués

---

### Phase 3 — Accès DB Direct Worker

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 3
- [ ] Vérifier que Phase 2 est validée (tag `phase-2-complete`)
- [ ] Analyser les besoins d'accès DB direct
- [ ] Préparer la couche de repositories
- [ ] Créer une branche `feat/phase-3-db-direct`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 3
- [ ] Exécuter les tests Phase 2 (non-régression)
- [ ] Préparer les tests unitaires repositories
- [ ] Préparer les tests d'intégration insert DB direct
- [ ] Préparer les tests de performance

#### Préparation DevOps
- [ ] Vérifier la connexion PostgreSQL
- [ ] Préparer la variable `WORKER_DATABASE_URL`
- [ ] Vérifier les timeouts de connexion
- [ ] Préparer le monitoring DB

#### Critères de Démarrage
- [ ] Phase 2 validée (tag `phase-2-complete`)
- [ ] Tests Phase 2 passent (0 régression)
- [ ] Tâche maintenance migrée et fonctionnelle
- [ ] Briefings distribués

---

### Phase 4 — Migration Progressive du Cœur

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 4
- [ ] Vérifier que Phase 3 est validée (tag `phase-3-complete`)
- [ ] Analyser les tâches par lot (criticité croissante)
- [ ] Préparer les modules TaskIQ par lot
- [ ] Créer une branche `feat/phase-4-migration-progressive`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 4
- [ ] Exécuter les tests Phase 3 (non-régression)
- [ ] Préparer les tests unitaires par lot
- [ ] Préparer les tests d'intégration par lot
- [ ] Préparer les tests de feature flags

#### Préparation DevOps
- [ ] Vérifier que Docker est optimisé pour RPi4
- [ ] Préparer le monitoring des tâches migrées
- [ ] Vérifier les limites de mémoire
- [ ] Préparer les variables d'environnement par lot

#### Critères de Démarrage
- [ ] Phase 3 validée (tag `phase-3-complete`)
- [ ] Tests Phase 3 passent (0 régression)
- [ ] Insertion DB direct opérationnelle
- [ ] Briefings distribués

---

### Phase 5 — Décommission Celery

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 5
- [ ] Vérifier que Phase 4 est validée (tag `phase-4-complete`)
- [ ] Vérifier que 2 semaines sans incident se sont écoulées
- [ ] Analyser les imports Celery restants
- [ ] Créer une branche `feat/phase-5-decommission-celery`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 5
- [ ] Exécuter la suite complète de tests
- [ ] Préparer la vérification des imports Celery
- [ ] Préparer les tests Docker
- [ ] Préparer les tests de toutes les tâches TaskIQ

#### Préparation DevOps
- [ ] Vérifier que toutes les tâches fonctionnent via TaskIQ
- [ ] Préparer la suppression des services Celery
- [ ] Préparer la mise à jour des Dockerfiles
- [ ] Préparer le nettoyage Docker

#### Critères de Démarrage
- [ ] Phase 4 validée (tag `phase-4-complete`)
- [ ] 2 semaines sans incident majeur
- [ ] Tous les tests passent
- [ ] Performance validée
- [ ] Briefings distribués

---

### Phase 6 — Fusion Backend / Backend Worker

#### Préparation Développeur
- [ ] Lire le briefing développeur Phase 6
- [ ] Vérifier que Phase 5 est validée (tag `phase-5-complete`)
- [ ] Auditer les duplications entre `backend/` et `backend_worker/`
- [ ] Préparer la structure cible
- [ ] Créer une branche `feat/phase-6-fusion-backend`

#### Préparation Testeur
- [ ] Lire le briefing testeur Phase 6
- [ ] Exécuter la suite complète de tests
- [ ] Préparer la vérification des imports `backend_worker`
- [ ] Préparer les tests Docker
- [ ] Préparer les tests de toutes les tâches TaskIQ

#### Préparation DevOps
- [ ] Vérifier que toutes les tâches fonctionnent via TaskIQ
- [ ] Préparer la mise à jour Docker Compose
- [ ] Préparer la mise à jour des Dockerfiles
- [ ] Préparer la suppression de `backend_worker/`

#### Critères de Démarrage
- [ ] Phase 5 validée (tag `phase-5-complete`)
- [ ] Tous les tests passent
- [ ] Aucun import Celery ne reste
- [ ] Documentation à jour
- [ ] Briefings distribués

---

## 📊 Métriques de Suivi

### Métriques par Phase

| Phase | Stories Dev | Stories Test | Stories DevOps | Total | Durée Estimée |
|-------|-------------|--------------|----------------|-------|---------------|
| 1 (Socle) | 5 | 2 | 2 | 9 | 2-3 jours |
| 2 (Pilote) | 5 | 3 | 1 | 9 | 2-4 jours |
| 3 (DB Direct) | 5 | 3 | 1 | 9 | 3-5 jours |
| 4 (Migration) | 4 | 3 | 1 | 8 | 5-10 jours |
| 5 (Décommission) | 5 | 2 | 2 | 9 | 2-3 jours |
| 6 (Fusion) | 5 | 2 | 2 | 9 | 5-8 jours |
| **Total** | **29** | **16** | **9** | **54** | **19-33 jours** |

### Métriques de Qualité

| Métrique | Objectif | Mesure |
|----------|----------|--------|
| **Taux de réussite tests** | ≥ 100% | Tests passants / Tests totaux |
| **Régressions introduites** | 0 | Tests échoués vs baseline |
| **Anomalies bloquantes** | 0 | Anomalies critiques |
| **Performance** | ≤ 110% de Celery | Latence TaskIQ / Latence Celery |
| **Mémoire** | ≤ 100% de Celery | Mémoire TaskIQ / Mémoire Celery |
| **Fiabilité** | ≥ 99% | Tâches succès / Tâches totales |

---

## 🔄 Workflow de Validation

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

---

## 🚨 Procédure de Rollback

### Rollback Immédiat (Feature Flag)

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

## 📁 Structure des Fichiers de Délégation

```
docs/plans/taskiq_migrations/
├── STORY_ORGANIZATION.md           # Ce fichier
├── PLAN_DELEGATION.md              # Plan de délégation détaillé
├── PLAN_AMELIORE_MIGRATION_TASKIQ.md  # Plan détaillé (existant)
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

## 🎯 Objectifs de Qualité

- **Zéro régression** sur les tests existants
- **Performance** : latence ≤ 110% de Celery
- **Mémoire** : consommation ≤ 100% de Celery
- **Fiabilité** : taux de succès ≥ 99%
- **Observabilité** : logs structurés et différenciés

---

*Dernière mise à jour : 2026-03-21*
*Version : 1.0*
*Statut : En cours de validation*
