# refactor.md — Refactorisation Backend & Backend Workers

**Objectif** : découpler proprement l'API (backend) des traitements lourds (backend workers), introduire une file de tâches robuste, rendre le système testable et observable, et préparer l'évolutivité (DB scalable, moteur vecteurs, services IA). Ce document formalise les étapes, modules à isoler, contrats techniques, risques, outils et checklist par sprint.

---

## Principes directeurs

* **Séparation claire des responsabilités** : l'API doit traiter les requêtes clients et orchester les opérations, les workers effectuent le travail long et idempotent.
* **Communication asynchrone** via une file (Redis + Celery recommandé) pour la robustesse et la scalabilité.
* **Contrats explicites** entre services (payloads JSON, événements WS) pour permettre tests et évolutions indépendantes.
* **Observabilité** : logs structurés, métriques et traces pour diagnostiquer performances et erreurs.
* **Testabilité** : couverture unitaires et d'intégration, mocks pour services externes.

---

## Structure de code proposée

```
/backend-api/                 # FastAPI (service API)
  app/
    main.py
    api/
      v1/
        routes/
        schemas/             # Pydantic schemas (public contract)
        services/            # App-level orchestration, appelle tasks via broker
    db/
      models.py
      crud.py
      session.py
    auth/
    tasks_client.py          # fonctions utilitaires pour envoyer des tâches (celery.apply_async wrapper)
    tests/
  Dockerfile
  requirements.txt

/backend-workers/             # Workers Celery (ou équivalent)
  worker/
    tasks/
      indexer.py
      audio_analysis.py
      downloaders.py
      vectorize.py
    apps/
      indexer_app.py         # bootstrap worker
    utils/
    tests/
  Dockerfile
  celeryconfig.py
  requirements.txt

/common/                      # Code partagé (pydantic schemas, constantes, utils)
  schemas.py
  events.py                    # noms d'événements, versions
  logging.py

/docker-compose.yml
/infra/                        # configs: redis, pg, monitoring
/ops/                          # scripts deploy / migrations / backup
```

> **Remarque** : `common/` est un package Python importable par `backend-api` et `backend-workers` (via volume mount en dev / pip package interne en prod).

---

## Contrats et payloads (exemples)

### 1) Tâche d'indexation (API → queue)

```json
{
  "task": "index_file",
  "version": 1,
  "payload": {
    "file_path": "/media/music/Artist/Album/01 - Track.mp3",
    "scan_id": "uuid-v4",
    "priority": "normal"
  }
}
```

### 2) Événement de fin d'indexation (worker → backend via DB/WS)

```json
{
  "event": "index_complete",
  "scan_id": "uuid-v4",
  "status": "ok",
  "metadata": {"artist": "...", "album": "...", "track": "..."}
}
```

### 3) Task vectorize

```json
{
  "task": "vectorize_track",
  "payload": {"track_id": 1234, "embedding_model": "ollama-v1"}
}
```

Documenter tous les schemas Pydantic dans `common/schemas.py` pour validation côté API et côté worker.

---

## Choix technologiques recommandés

* **Broker** : Redis (pub/sub + broker pour Celery)
* **Task queue** : Celery (mature, supports retries, ETA, task chaining) ou RQ si simplicité souhaitée.
* **Worker runtime** : Python asyncio-compatible (pour IO heavy) + processus multiples.
* **DB** : SQLite pour dev/local, PostgreSQL pour production (pgvector si besoin d'index vecteurs). FAISS pour gros corpus si besoin hors-DB.
* **Embeddings / LLM** : Ollama local ou API interne. Mettre un cache des embeddings pour éviter recalculs.
* **Search** : Whoosh (léger) ou Elasticsearch / Postgres fulltext pour montée en charge.
* **CI/CD** : GitHub Actions (tests, lint, build images, run migrations), optional: Dependabot.
* **Monitoring** : Prometheus + Grafana ou simplement statsd Prometheus exporter + logs JSON via stdout.
* **Tracing** : OpenTelemetry (optionnel mais recommandé).

---

## Sprints de refactorisation (objectifs & checklist)

### Sprint R1 — Isolation de l'API (Backend as API-only)

**Objectif** : faire en sorte que le backend n'exécute plus de traitements lourds en-process.

Checklist :

* [ ] Extraire tout code d'indexation/processing hors du backend.
* [ ] Créer `tasks_client.py` pour soumettre les tâches à la queue (interface simple `submit_task(name, payload, retry=...)`).
* [ ] Remplacer les appels directs à la logique lourde par des `submit_task(...)`.
* [ ] Ajouter endpoints qui déclenchent des tâches asynchrones et renvoient un `task_id`.
* [ ] Ajouter tests unitaires sur les endpoints (mock du client de tâches).
* [ ] Mettre en place une healthcheck pour broker (Redis) et DB.

Résultat attendu : backend ne doit plus lancer d'opérations bloquantes — uniquement orchestration.

### Sprint R2 — File de tâches & Worker Basique

**Objectif** : déployer des workers qui consomment les tâches et effectuer indexation/analysis simple.

Checklist :

* [ ] Installer & configurer Redis + Celery.
* [ ] Implémenter tâches de base dans `backend-workers/tasks/` : `index_file`, `analyze_audio`, `download_artwork`.
* [ ] Gérer retries, timeouts et idempotence (keyed by `file_path` + hash).
* [ ] Intégrer logging structuré dans les tâches.
* [ ] Mettre en place un petit dashboard (Flower) pour surveiller la queue en dev.
* [ ] Tests d'intégration: soumettre une tâche via API, vérifier DB après exécution worker.

Résultat attendu : pipeline asynchrone fonctionnel, tâches traitées et DB mise à jour.

### Sprint R3 — Découpage des Workers & Vectorisation

**Objectif** : séparer les responsabilités entre workers spécialisés et ajouter génération d'embeddings.

Checklist :

* [ ] Créer workers spécialisés : `indexer_worker`, `audio_worker`, `vector_worker`, `downloader_worker`.
* [ ] Implémenter chaîne de tâches : `index_file` → `analyze_audio` → `vectorize_track`.
* [ ] Mettre en place un cache pour embeddings (Redis/DB) pour éviter recalculs.
* [ ] Ajouter monitoring des tasks (durée, erreurs) et métriques Prometheus.
* [ ] Tests d'intégration couvrant la chaîne complète.

Résultat attendu : workers modulaires, vecteurs générés et stockés, systèmes de retries robustes.

### Sprint R4 — Intégrations externes et robustesse

**Objectif** : intégrer Last.fm / ListenBrainz, Napster OAuth, et Soulseek ; ajouter résilience.

Checklist :

* [ ] Implémenter adaptateurs (adapters) pour Last.fm, ListenBrainz, Napster, Soulseek avec interfaces unifiées.
* [ ] Gérer quotas & erreurs externes (backoff, circuit breaker).
* [ ] Implémenter file d'attente priorisée (ex: priorité haute pour tasks utilisateur).
* [ ] Ajouter tests end-to-end simulant erreurs d'API externes.

Résultat attendu : intégrations stables et résilientes.

### Sprint R5 — Tests, CI, Monitoring & Documentation

**Objectif** : rendre la plateforme maintenable et observable.

Checklist :

* [ ] Couverture tests unitaires > X% (à décider), tests d'intégration pour endpoints principaux.
* [ ] CI pipeline (GitHub Actions): lint, unit tests, build images, run migration scripts.
* [ ] Setup monitoring (Prometheus/Grafana) et alerting minimal (erreurs de queue, erreurs DB).
* [ ] Documenter les contrats tasks/events (`common/schemas.py`).
* [ ] Plan de rollback pour déploiements (DB backups, tags images).

Résultat attendu : plateforme conforme aux bonnes pratiques devops.

---

## Idempotence, retrys et erreurs

* **Idempotence** : chaque tâche doit être idempotente (ex: marquer `file_path` avec hash, utiliser `upsert`).
* **Retries** : configurer policy exponential backoff ; différencier erreurs transitoires et fatales.
* **Dead Letter Queue** : stocker tâches échouées après N retries pour analyse.

---

## Tests & Qualité

* **Unit tests** : pydantic schemas, CRUD, services orchestration.
* **Integration tests** : endpoints + worker (pytest + docker-compose to spin Redis/Postgres/Workers).
* **E2E tests** : simulate user flows (scan directory → index → playqueue → play).
* **Static analysis** : flake8 / black / mypy (optionnel mais recommandé).

---

## Monitoring & Observabilité

* Logs JSON (stdout) pour ingestion par Grafana Loki ou autre.
* Exposer métriques Prometheus depuis API & Workers (`celery-exporter` ou endpoint /metrics).
* Alerting minimal : queue depth, failed tasks rate, DB connection errors.

---

## Risques & Mitigations

* **Problème de concurrence DB (SQLite)** : SQLite mal adapté à forte concurrence. Mitigation : utiliser SQLite en local/dev, PostgreSQL pour production. Utiliser transactions courtes, verrous prudents.
* **Ressources sur Raspberry Pi** : tasks lourdes (vectorisation, transcodage) consomment CPU/RAM. Mitigation : limiter concurrents, offload sur machine plus puissante ou planifier hors-peak.
* **Dépendances externes instables** : Napster/Soulseek peuvent rate limiter. Mitigation : circuit breaker, retries, file d'attente priorisée.

---

## Checklist de livraison (DoD) pour chaque sprint

* [ ] Code review passées
* [ ] Tests unitaires et d'intégration exécutés et réussis
* [ ] Documentation (README des modules) mise à jour
* [ ] Scripts de déploiement/migration mis à jour
* [ ] Monitoring de base en place
* [ ] Rollback documenté


