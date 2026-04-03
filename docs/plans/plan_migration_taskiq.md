# Plan détaillé de migration Celery → TaskIQ (SoniqueBay)

## 1) Objectifs et contraintes

### Objectifs
- Remplacer progressivement Celery par TaskIQ pour les traitements asynchrones.
- Réduire la complexité opérationnelle et améliorer l’observabilité.
- Préserver la continuité de service (zéro interruption fonctionnelle).
- Mettre à jour les tests existants et exécuter la suite de validation.

### Contraintes architecture/projet
- Stack actuelle : FastAPI (`backend/`), workers (`backend_worker/`), PostgreSQL + Redis, Docker Compose.
- Exécution cible : CPU-only / Raspberry Pi (mémoire limitée).
- Maintien de la séparation claire API / Worker / Frontend.
- Toute migration doit être incrémentale avec rollback simple.

---

## 2) État actuel (à confirmer par audit technique)

- Orchestration asynchrone via Celery (`backend_worker/celery_app.py`, `celery_tasks.py`, workers spécialisés).
- Broker/result backend déjà adossés à Redis.
- API FastAPI expose des endpoints internes consommés par les workers.
- Une partie de la logique métier est dupliquée ou répartie entre `backend/services` et `backend_worker/services`.

---

## 3) Cible d’architecture TaskIQ

## 3.1 Schéma cible (progressif)
1. **TaskIQ Broker** adossé à Redis (première phase).
2. **TaskIQ workers** démarrés dans `backend_worker`.
3. **TaskIQ scheduler** (si besoin) remplaçant Celery Beat.
4. **Intégration FastAPI** pour injection de dépendances et cycle de vie (réf. `taskiq-with-fastapi`).
5. **Tracing + métriques** unifiés (logs structurés + timings + erreurs).

## 3.2 Positionnement DB pour les workers (demande projet)
Demande: permettre `SELECT/INSERT/UPDATE` directs depuis workers pour éviter le hop API.

### Proposition sécurisée en 2 options
- **Option A (recommandée court terme):** conserver l’accès DB via API interne pendant migration moteur (risque minimal).
- **Option B (évolutive, sous feature flag):** accès DB direct worker encadré :
  - Session SQLAlchemy dédiée workers.
  - Timeouts DB stricts + retry/backoff.
  - Opérations autorisées par whitelist (tables/opérations ciblées).
  - Transactions courtes, idempotence, journal d’audit.
  - Coupure rapide via variable d’env (`WORKER_DIRECT_DB_ENABLED=false`).

Recommandation: implémenter Option B progressivement sur tâches à fort volume (vectorisation / batch insert), avec fallback API.

---

## 4) Plan de migration par phases

## Phase 0 — Audit et préparation (1-2 jours)
- Cartographier toutes les tâches Celery : triggers, payloads, SLA, criticité, idempotence.
- Identifier les dépendances circulaires entre `backend` et `backend_worker`.
- Définir les interfaces de tâches standard (input/output/errors/retry policy).
- Inventorier les tests impactés (unit, intégration, e2e).

**Livrables**
- Matrice des tâches (priorité migration).
- Stratégie de rollback validée.
- Liste des variables d’environnement à ajouter.

## Phase 1 — Socle TaskIQ minimal (2-3 jours)
- Ajouter dépendances TaskIQ (core + redis broker + fastapi integration).
- Créer `backend_worker/taskiq_app.py` (broker, middlewares, retry defaults).
- Créer bootstrap worker TaskIQ et commande Docker dédiée.
- Ajouter healthcheck worker (liveness/readiness).

**Livrables**
- Worker TaskIQ démarre en parallèle de Celery.
- Aucune tâche métier migrée à ce stade.

## Phase 2 — Migration pilote (2-4 jours)
- Migrer 1 à 2 tâches non critiques (ex: maintenance/diagnostic).
- Conserver double exécution désactivable par flags:
  - `USE_TASKIQ_FOR_X=true/false`
  - `ENABLE_CELERY_FALLBACK=true/false`
- Mettre en place instrumentation comparative (latence, erreurs, mémoire).

**Livrables**
- Tâches pilotes en production interne/staging.
- Rapport comparatif Celery vs TaskIQ.

## Phase 3 — Accès DB direct worker (Option B) sur périmètre restreint (3-5 jours)
- Introduire `backend_worker/db/` :
  - `engine.py` (create_async_engine),
  - `session.py` (async_sessionmaker),
  - `repositories/` spécialisés.
- Migrer une tâche à forte charge avec DB direct (ex: insert batch).
- Ajouter garde-fous:
  - transactions atomiques,
  - verrou logique/idempotency key,
  - timeout/retry bornés.

**Livrables**
- Premier flux DB direct validé.
- Fallback API interne toujours disponible.

## Phase 4 — Migration progressive du cœur des tâches (5-10 jours)
- Migrer lot par lot:
  1. tâches batch insert/update,
  2. enrichissement metadata,
  3. vectorisation/embeddings,
  4. tâches planifiées.
- Retirer dépendances Celery au fur et à mesure (sans big bang).
- Adapter scripts d’exploitation/monitoring.

**Livrables**
- >80% tâches sur TaskIQ.
- Celery conservé en secours transitoire.

## Phase 5 — Décommission Celery (2-3 jours)
- Supprimer `celery_app.py`, `celery_tasks.py`, conf beat associée (après gel de stabilité).
- Nettoyer Docker Compose + docs ops.
- Finaliser runbooks TaskIQ.

**Livrables**
- Runtime unique TaskIQ.
- Documentation à jour.
- Plans de test dans  `/tests` mis à jour pour la prise en charge de cette nouvelle architecture 

---

## 5) Refonte partielle backend / backend_worker (optimisation demandée)

## 5.1 Problème actuel
- Risque de duplication logique (services API vs services worker).
- Contrats de données parfois implicites.
- Coût de maintenance élevé.

## 5.2 Proposition de refonte modulaire
Créer un package partagé interne (ex: `backend_common/`) contenant:
- schémas Pydantic communs (payload tâches, DTO),
- logique métier pure (sans dépendance web/queue),
- utilitaires techniques (retries, pagination, validation),
- couche repository abstraite.

Ensuite:
- `backend/` garde l’orchestration HTTP/WebSocket + auth + transaction boundary API.
- `backend_worker/` garde orchestration asynchrone TaskIQ + scheduling.
- Les deux appellent `backend_common` pour éviter divergences.

Bénéfices:
- réduction duplication,
- tests unitaires plus rapides,
- contrats explicites et versionnables.

---

## 6) Stratégie de tests et validation

## 6.1 Mise à jour tests
- Adapter mocks Celery vers TaskIQ:
  - publication de tâche,
  - retry policy,
  - résultats/aspects async.
- Ajouter tests unitaires:
  - config broker TaskIQ,
  - sérialisation payloads,
  - idempotence et retries.
- Ajouter tests intégration:
  - enchaînement API → queue → worker → DB,
  - mode fallback API vs DB direct.

## 6.2 Exécution (Windows/Powershell)
Ordre recommandé:
1. tests unitaires worker migrés,
2. tests intégration workers,
3. tests API impactés,
4. suite globale ciblée puis complète.

Exemple:
- `python -m pytest tests/unit/worker -q`
- `python -m pytest tests/integration/workers -q`
- `python -m pytest tests/integration/api -q`
- `python -m pytest tests -q`

## 6.3 Critères d’acceptation
- Parité fonctionnelle Celery/TaskIQ sur périmètre migré.
- Taux d’échec non régressif.
- Temps moyen de traitement stable ou meilleur.
- Consommation mémoire maîtrisée (profil RPi).

---

## 7) Observabilité, performance, robustesse

- Logs structurés corrélés (request_id / task_id / entity_id).
- Métriques:
  - queue depth,
  - task latency p50/p95,
  - retries, failures, timeout rate.
- Backpressure:
  - concurrence faible par défaut (1-2),
  - limitation taille batch,
  - protection OOM.
- Retry policy:
  - exponential backoff + jitter,
  - plafond strict des tentatives.
- Dead-letter strategy pour tâches poison.

---

## 8) Plan d’optimisation global (au-delà migration)

1. **Unification des contrats de données**
   - DTO partagés + versionnage payloads.
2. **Réduction des allers-retours DB**
   - bulk insert/update, pagination stricte, projections ciblées.
3. **Optimisation vectorisation**
   - batching calibré mémoire,
   - reprise sur incident par checkpoints.
4. **Optimisation tests**
   - fixtures DB plus rapides,
   - partition unit/integration/e2e stricte,
   - exécution parallèle prudente selon ressources.
5. **Fiabilité opérationnelle**
   - runbooks incidents,
   - commandes diagnostics standardisées,
   - healthchecks renforcés.

---

## 9) Analyse risques & mitigation

- **Risque**: rupture compatibilité payloads  
  **Mitigation**: adaptateurs de schéma + tests de contrat.
- **Risque**: contention DB en accès direct worker  
  **Mitigation**: limites concurrence + transactions courtes + index.
- **Risque**: dette de migration longue  
  **Mitigation**: phases courtes, KPI hebdo, kill-switch par feature flags.
- **Risque**: régression silencieuse  
  **Mitigation**: shadow mode, comparaison outputs Celery/TaskIQ.

---

## 10) Roadmap opérationnelle (proposée)

- Semaine 1: Phase 0 + Phase 1
- Semaine 2: Phase 2 (pilote) + début Phase 3
- Semaine 3: fin Phase 3 + Phase 4 (lot 1)
- Semaine 4: Phase 4 (lots 2/3) + préparation décommission
- Semaine 5: Phase 5 + stabilisation finale

---

## 11) TODO technique initial (exécutable)

- [ ] Créer `backend_worker/taskiq_app.py`
- [ ] Ajouter config env TaskIQ (`TASKIQ_BROKER_URL`, retries, timeouts)
- [ ] Ajouter service bootstrap TaskIQ dans `docker-compose.yml`
- [ ] Migrer une tâche pilote non critique
- [ ] Ajouter feature flags de bascule Celery/TaskIQ
- [ ] Implémenter couche DB worker (feature flag) pour 1 flux pilote
- [ ] Adapter tests unitaires worker
- [ ] Adapter tests intégration worker/API
- [ ] Exécuter suites pytest ciblées puis complètes
- [ ] Documenter rollback et runbook exploitation

---

## 12) Décisions à valider

1. Activer l’accès DB direct worker dès la Phase 3 (piloté par feature flag) : **Oui/Non**
2. Créer `backend_common/` maintenant ou après migration pilote : **Maintenant recommandé**
3. Décommission Celery seulement après 2 semaines sans incident majeur : **Recommandé**
