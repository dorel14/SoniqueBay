# 📘 Guide des Agents – SoniqueBay

## ✅ Checklist rapide

Avant de committer ou pousser du code, vérifie :

* [ ] Le projet **démarre correctement dans Docker** avec `docker-compose up`.
* [ ] Les **4 conteneurs** (FastAPI+GraphQL, Celery worker, NiceGUI frontend) tournent sans erreur.
* [ ] Le code respecte **PEP8** et les règles définies ci-dessous.
* [ ] Le code ne contient pas de vulnérabilités ou failles de sécurité potentielles, un contrôle temps réel est effectué via Snyk
* [ ] Les **tests passent** et aucune régression n’est introduite,  les tests sont lancés en masse via la commande "python -m pytest .\tests\ -x --tb=no -q --snapshot-update".
* [ ] Tu fais un revoew à chaque implémentation de nouveau code ou corrections de bugs
* [ ] Les commits suivent le format standard (`feat`, `fix`, etc.).
* [ ] Aucun fichier sensible ou généré n’est committé (`.env`, cache, DB locale, etc.).
* [ ] Nous développons en environnement windows ,  les commandes doivent donc se faire en powershell

---

## 1. 🎯 Objectifs

* Assurer un code clair, lisible et cohérent.
* Garantir un projet **dockerisé stable**, avec des conteneurs isolés et interconnectés.
* Maintenir des commits propres et explicites.
* Respecter l’architecture globale du dépôt.

---

## 2. 📦 Architecture Docker

Le projet fonctionne sous **Docker Compose** avec **3 conteneurs** principaux :

* **library_api** : API FastAPI + endpoints GraphQL pour la gestion de la librairie.
* **backend_worker** : worker Celery (tâches asynchrones).
* **frontend** : interface utilisateur NiceGUI.

**Règles spécifiques Docker** :

* Ne pas modifier les `Dockerfile` et `docker-compose.yml` sans justification claire.
* Ajouter toute nouvelle dépendance au **bon service** (fichier `requirements.txt` ou équivalent).
* Toujours tester avec :

```bash
docker-compose build && docker-compose up
```

---

## 3. 📂 Structure et organisation

* Respecter la hiérarchie existante du projet.
* Ajouter de nouveaux modules uniquement si justifié.
* Éviter les duplications de code (favoriser la modularité).
* Documenter chaque nouveau fichier avec : rôle, dépendances, auteur.

---

## 4. 💻 Règles de codage

### Python (FastAPI, Celery)

* Respecter **PEP8** et utiliser un formateur (ex. `black` + `isort` + `ruff`) .
* Utiliser des **annotations de type** (`typing`) systématiquement.
* Ajouter des **docstrings** claires (module, classes, fonctions).
* Préférer les **imports absolus** dans les modules internes.
* Travailler dans une architecture MVC afin de séparer logique métier et api par exemple 
* Bien séparer :

  * API (FastAPI/GraphQL),
  * Workers Celery,
  * Logique métier.
* Gestion d’erreurs : lever des exceptions explicites, logs utiles, pas de `except: pass`.
* Gestion des logs: dans chacun des dossiers principaux , il existe un sous dossier utils et une lib logging.py , elle doit être utilisée pour la gestion des logs ,  pas de print autorisé

### Frontend (NiceGUI)

* Favoriser les **composants réutilisables**.
* Maintenir une cohérence graphique (clair/sombre).
* Commenter les parties complexes (animations, transitions, WebSocket).
* Soigner les performances (latence, taille des listes, throttling des events).
* On interroge le backend via l'api REST ou GraphQL ou websocket selon le niveau de performance et de mise àjour temps réel à  obtenir

### Base de données

* Respecter le schéma SQLAlchemy existant.
* Toute nouvelle table doit avoir :

  * un identifiant unique (`id`),
  * des index si nécessaire,
  * une migration associée (si Alembic est utilisé).

* Seule l'API accède à la base de donnée , le worker et le frontend accès via l'api,  graphql ou les websockets à l'exception du cadre du projet de migration vers taskiq

---

## 5. ✅ Tests & Validation

* Tester le projet en mode local avec pytest,  on indiquera en fin de commande -n auto pour la lib pytest-xdist
* Tester le projet **dans Docker** (pas seulement en local “nu”).
* Tous les tests doivent être écrits dans les sous répertoires 'tests' des dossiers principaux 
* Si il y a besoin d'accéder à une bdd ,  il est possible de créer une bdd temporaire à base d'aiosqlite ,  pas de wrapper dans le code actuel pour passer en  mode sync 
* Ajouter des **tests unitaires** pour la logique non triviale.
* Vérifier avant commit :

  * `docker-compose up` démarre sans erreur,
  * les endpoints FastAPI/GraphQL répondent,
  * l’UI NiceGUI fonctionne.
* '
---

## 6. 📜 Règles de commits

### Format

`<type>(scope): message court`

### Types autorisés

* **feat** : ajout de fonctionnalité
* **fix** : correction de bug
* **refactor** : modification interne sans changement de comportement
* **style** : formatage, lint, renommages non fonctionnels
* **docs** : documentation uniquement
* **test** : ajout/modification de tests
* **chore** : tâches diverses (dépendances, scripts, CI, etc.)

### Exemples

```text
feat(playqueue): ajout de la gestion des webradios
fix(db): correction des doublons dans la table Artist
docs(agents): ajout des règles de contribution
```

**Bonnes pratiques de commit** :

* Commits **atomiques** et messages **impératifs** (“add”, “fix”, “update”).
* Inclure le **contexte** si utile (raison du changement, impact).
* Éviter les commits géants mêlant refactor, feature et fix.

---

## 7. 🔄 Workflow Git

1. Créer une branche à partir de `main` :

```bash
git checkout -b feat/nom-fonctionnalite
```

1. Commits atomiques et clairs.
2. Push et création d’une **Pull Request** vers `main`.
3. Revue par un autre agent/mainteneur (si applicable).
4. **Squash & merge** recommandé si les commits sont nombreux et granulaires.

---

## 8. 🤝 Bonnes pratiques

* Expliquer les choix dans le message de commit ou la PR.
* Tenir compte de la cible **Raspberry Pi 4** (performance & mémoire).
* Favoriser des solutions simples, lisibles et robustes.
* Documenter toute dépendance externe ajoutée (raison, version).
* Optionnel mais recommandé : **pre-commit** avec `black`, `isort`, `flake8`/`ruff`, `mypy`.

---

## 9. 📌 Notes pour les agents automatiques

* Ne **jamais** modifier ou committer `.env`, secrets, clés API.
* Ne pas committer de fichiers générés (`__pycache__`, `.mypy_cache`, `*.db`, `dist/`, etc.).
* Respecter `.gitignore`.
* Avant commit, vérifier :

  * le projet démarre dans Docker,
  * le code est formaté (`ruff`, `isort`),
  * pas d’imports morts, pas de TODO “temporaires” laissés au milieu d’une feature.

---

👉 Ce fichier évolue via **Pull Request** avec justification.
