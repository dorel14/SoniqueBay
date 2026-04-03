# Tickets Phase 2 — Suppression Fichiers Celery

## [TICKET-P2-001] Créer TaskIQ retry config (remplacement celery_retry_config)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `celery_retry_config.py` contient des patterns de retry utilisés par plusieurs workers. Créer un équivalent TaskIQ :
- Retry automatique avec backoff exponentiel
- Dead Letter Queue pour tâches en échec définitif
- Décorateurs utilitaires pour faciliter l'implémentation
- Adapter les constantes `DEFAULT_RETRY_CONFIG` pour TaskIQ
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.5 jour
**Notes**: Voir `backend_worker/utils/celery_retry_config.py` pour le contenu à migrer

---

## [TICKET-P2-002] Créer TaskIQ admin API (remplacement celery_admin_api)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Renommer `celery_admin_api.py` en `taskiq_admin_api.py` et adapter les endpoints :
- Lister les tâches en échec depuis Redis TaskIQ
- Relancer les tâches
- Statistiques des queues
- Mettre à jour le prefix de l'API (`/api/admin/taskiq` au lieu de `/api/admin/celery`)
- Mettre à jour la clé d'authentification (`TASKIQ_ADMIN_API_KEY` au lieu de `CELERY_ADMIN_API_KEY`)
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.5 jour
**Notes**: Voir `backend/api/routers/celery_admin_api.py` pour le contenu à migrer

---

## [TICKET-P2-003] Adapter celery_config_loader pour TaskIQ ou supprimer
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le module `celery_config_loader.py` lit la configuration Celery depuis Redis. Décider :
- Option A : Supprimer si la config TaskIQ est gérée autrement (recommandé)
- Option B : Adapter pour lire la config TaskIQ depuis Redis
- Option C : Déplacer la config dans un fichier YAML/JSON standard
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour
**Notes**: Voir `backend/api/utils/celery_config_loader.py`

---

## [TICKET-P2-004] Supprimer celery_config_source.py (worker)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `celery_config_source.py` contient la configuration des queues et routes Celery. Décider :
- Supprimer si les queues TaskIQ sont gérées différemment
- Adapter si les queues Redis sont encore nécessaires
- Vérifier qu'aucun import ne pointe vers ce fichier
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour
**Notes**: Contient `get_unified_queues()`, `get_unified_task_routes()`, `get_unified_celery_config()`

---

## [TICKET-P2-005] Supprimer celery_config_publisher.py (worker)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `celery_config_publisher.py` publie la config Celery dans Redis au démarrage du worker. Supprimer ce fichier :
- Vérifier qu'aucun import ne pointe vers ce fichier
- Supprimer les appels de publication au démarrage du worker
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.1 jour

---

## [TICKET-P2-006] Supprimer celery_monitor.py (worker)
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Le fichier `celery_monitor.py` contient le monitoring des arguments Celery. Décider :
- Supprimer si le monitoring TaskIQ est géré différemment
- Adapter pour TaskIQ si le monitoring des tailles de payload est encore nécessaire
- Vérifier qu'aucun import ne pointe vers ce fichier
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour
**Notes**: Contient `CELERY_SIZE_METRICS` et des fonctions de monitoring

---

## [TICKET-P2-007] Renommer celery_app.py (API) en taskiq_broker.py
**Statut**: OUVERT
**Auteur**: Système (audit automatique)
**Description**: Renommer `backend/api/utils/celery_app.py` en `backend/api/utils/taskiq_broker.py` :
- Renommer la classe `CeleryAppCompatibility` en `TaskIQBrokerCompatibility`
- Renommer la variable `celery_app` en `taskiq_broker`
- Mettre à jour tous les imports qui pointent vers ce fichier
- Vérifier les imports dans `backend/api/routers/`, `backend/api/services/`, etc.
**Dépendances**: CLEAN-1 (imports nettoyés)
**Durée estimée**: 0.25 jour
**Notes**: Ce fichier est le point d'entrée principal pour l'envoi de tâches depuis l'API
