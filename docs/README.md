# Documentation de SoniqueBay

Cette documentation est organisée en plusieurs catégories pour faciliter la navigation et la maintenance.

## Structure de la Documentation

### 📁 [`architecture/`](architecture/)

Documentation générale sur l'architecture du projet SoniqueBay.

**Fichiers clés :**

- [`architecture.md`](architecture/architecture.md) - Architecture générale du projet
- [`refactor.md`](architecture/refactor.md) - Plan de refactorisation globale  
- [`scan_optimization_plan.md`](architecture/scan_optimization_plan.md) - Plan d'optimisation du système de scan

### 📁 [`guides/`](guides/)

Guides pratiques pour les développeurs et contributeurs.

**Fichiers :**

- [`AGENTS.md`](guides/AGENTS.md) - Guide complet pour les agents de développement (règles de code, conventions, workflow)

### 📁 [`monitoring/`](monitoring/)

Documentation sur le monitoring, les métriques et l'optimisation des performances.

**Fichiers :**

- [`README_FLOWER_MONITORING.md`](monitoring/README_FLOWER_MONITORING.md) - Guide de monitoring avec Flower
- [`README_VECTORIZATION.md`](monitoring/README_VECTORIZATION.md) - Guide de vectorisation et monitoring
- [`celery_monitoring_guide.md`](monitoring/celery_monitoring_guide.md) - Guide de monitoring Celery
- [`celery_optimization_config.md`](monitoring/celery_optimization_config.md) - Configuration optimisée pour Celery
- [`TEST_REFACTORING_SUMMARY.md`](monitoring/TEST_REFACTORING_SUMMARY.md) - Résumé des tests et refactorisation

### 📁 [`troubleshooting/`](troubleshooting/)

Solutions aux problèmes courants et diagnostic des erreurs.

**Fichiers :**

- [`SOLUTION_422_ERRORS.md`](troubleshooting/SOLUTION_422_ERRORS.md) - Résolution des erreurs 422
- [`SOLUTION_ALBUM_MAPPING_BUG.md`](troubleshooting/SOLUTION_ALBUM_MAPPING_BUG.md) - Correction des bugs de mapping d'albums
- [`SOLUTION_TIME_SYNC_WORKERS.md`](troubleshooting/SOLUTION_TIME_SYNC_WORKERS.md) - Synchronisation temporelle des workers
- [`SOLUTION_TRACKS_API_SESSION_FIX.md`](troubleshooting/SOLUTION_TRACKS_API_SESSION_FIX.md) - Correction des sessions API
- [`genres_unique_constraint_diagnostic.md`](troubleshooting/genres_unique_constraint_diagnostic.md) - Diagnostic des contraintes uniques

### 📁 [`workers/`](workers/)

Documentation spécifique aux workers et au traitement asynchrone.

**Fichiers :**

- [`BACKEND_WORKER_REFACTOR_PLAN.md`](workers/BACKEND_WORKER_REFACTOR_PLAN.md) - Plan de refactorisation des workers backend
- [`CELERY_HEARTBEAT_FIX_REPORT.md`](workers/CELERY_HEARTBEAT_FIX_REPORT.md) - Rapport de correction du heartbeat Celery
- [`workers_architecture.md`](workers/workers_architecture.md) - Architecture détaillée des workers
- [`SSE_PROGRESSION.md`](workers/SSE_PROGRESSION.md) - Implémentation Server-Sent Events
- [`worker_cover_improvements_plan.md`](workers/worker_cover_improvements_plan.md) - Plan d'amélioration du traitement des covers
- [`feature.md`](workers/feature.md) - Documentation de fonctionnalités spécifiques

## Utilisation Rapide

### Pour les Nouveaux Contributeurs

Commencez par lire [`guides/AGENTS.md`](guides/AGENTS.md) pour comprendre les conventions et bonnes pratiques du projet.

### Pour l'Architecture

Consultez [`architecture/`](architecture/) pour comprendre la structure générale et les décisions techniques.

### Pour le Monitoring

Rendez-vous dans [`monitoring/`](monitoring/) pour tout ce qui concerne l'observabilité et les performances.

### Pour Dépanner

Les solutions aux problèmes courants sont dans [`troubleshooting/`](troubleshooting/).

### Pour les Workers

La documentation spécifique aux workers Celery est dans [`workers/`](workers/).

## Mise à jour de la Documentation

Cette documentation est maintenue par l'équipe de développement. Pour ajouter ou modifier des documents :

1. **Catégorisez** votre document selon les dossiers existants
2. **Vérifiez** qu'il n'existe pas déjà un document similaire (évitez les doublons)
3. **Supprimez** les documents obsolètes lors des refactorisations
4. **Mettez à jour** ce README si vous ajoutez de nouvelles catégories

## Contribution

Toutes les contributions à la documentation sont les bienvenues. Assurez-vous que vos documents :

- Respectent les conventions de l'équipe (voir `guides/AGENTS.md`)
- Sont clairement structurés avec des titres et sections
- Contiennent des exemples pratiques quand c'est pertinent
- Sont régulièrement mis à jour avec les évolutions du code

---

*Dernière mise à jour : Novembre 2025*
