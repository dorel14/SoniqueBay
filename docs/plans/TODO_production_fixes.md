# TODO - Correctifs Production

> Branche : `blackboxai/production-fixes`
> Créée le : 2025-03-05
> Base : `master` (commit 4ba4834)

## Objectif
Cette branche est dédiée aux correctifs suite aux tests en production.

## Liste des correctifs

| # | Problème | Statut | Commit |
|---|----------|--------|--------|
| 1 | **DNS Error "Name or service not known"** - Variable d'environnement API_URL incorrecte | ✅ Corrigé | ef280de |
| 2 | **Système de retry Celery avec DLQ** - Les tâches échouées ne sont pas retentées | ✅ Implémenté | 3a9d4db, 179dc93 |
| 3 | **Cache HuggingFace non persistant** - Modèle re-téléchargé à chaque fois | ✅ Corrigé | 00ca9b3 |

### Fix #1 : DNS Error "Name or service not known" ✅

**Problème** : Les workers Celery ne pouvaient pas résoudre `http://api:8001`

**Solution** : Correction de la variable d'environnement dans `docker-compose.yml` :
```yaml
# Avant
- API_URL=http://api:8001

# Après  
- API_URL=http://library:8001
```

**Services corrigés** :
- `celery-worker`
- `frontend`

### Fix #2 : Système de retry Celery avec Dead Letter Queue ✅

**Problème** : Les tâches Celery qui échouent (ex: erreur DNS, timeout API) ne sont pas automatiquement retentées.

**Solution** : Mise en place d'un système de retry robuste avec :

#### 1. Configuration des retries (backend_worker/celery_app.py)
```python
task_default_retry_delay=60,      # 1 minute avant première retry
task_max_retries=5,               # 5 tentatives maximum
task_retry_backoff=True,          # Backoff exponentiel
task_retry_backoff_max=3600,      # Maximum 1 heure
task_retry_jitter=True,           # Jitter pour éviter thundering herds
task_autoretry_for=(              # Exceptions qui déclenchent le retry
    ConnectionError,
    TimeoutError,
    OSError,  # DNS errors
),
```

#### 2. Dead Letter Queue (DLQ)
- Queue `failed` ajoutée au worker
- Les tâches en échec après 5 retries sont stockées dans Redis
- Retention de 7 jours pour analyse

#### 3. API d'administration (backend/api/routers/celery_admin_api.py)
Endpoints disponibles :
- `GET /api/admin/celery/failed-tasks` - Liste les tâches en échec
- `POST /api/admin/celery/retry-task` - Relance une tâche manuellement
- `DELETE /api/admin/celery/failed-tasks/{task_id}` - Supprime une tâche de la DLQ
- `GET /api/admin/celery/retry-stats` - Statistiques de retry

#### Fichiers créés/modifiés :
1. `backend_worker/utils/celery_retry_config.py` - Configuration des retries
2. `backend_worker/celery_app.py` - Intégration des retries
3. `backend/api/routers/celery_admin_api.py` - API d'administration
4. `backend/api/__init__.py` - Enregistrement du router
5. `docker-compose.yml` - Ajout de la queue `failed`

#### Exemple de comportement :
```
Tâche lancée → Échec (DNS Error) → Retry 1 (après 1 min) → Échec → Retry 2 (après 2 min) 
→ Échec → Retry 3 (après 4 min) → Échec → Retry 4 (après 8 min) → Échec → Retry 5 (après 16 min) 
→ Échec → DLQ (stockée pour analyse)
```

### Fix #3 : Cache HuggingFace non persistant ✅

**Problème** : Le modèle sentence-transformers est re-téléchargé à chaque exécution car le cache HuggingFace n'est pas persistant entre les redémarrages du conteneur.

**Solution** : Ajout d'un volume persistant dans `docker-compose.yml` :
```yaml
volumes:
  - huggingface-cache:/root/.cache/huggingface

environment:
  - HF_HOME=/root/.cache/huggingface
```

**Commit** : `00ca9b3`

## Procédure de travail

1. **Réception du problème** : L'utilisateur décrit le bug rencontré en production
2. **Analyse** : Investigation des logs et du code concerné
3. **Correction** : Implémentation du fix avec tests
4. **Commit** : Format `type(scope): description` (Conventional Commits)
5. **Test** : Vérification en production
6. **Itération** : Si nouveau problème, retour à l'étape 1

## Notes

- Chaque correction fait l'objet d'un commit séparé
- Les tests unitaires sont obligatoires pour chaque fix
- La branche reste ouverte tant que des correctifs sont nécessaires
- **Principe important** : Toujours privilégier la configuration via variables d'environnement plutôt que de modifier le code source

---

### Fix #2b : Import SQLAlchemy optionnel ✅

**Problème** : Le worker Celery n'a pas SQLAlchemy installé, causant une erreur `ModuleNotFoundError` au démarrage.

**Solution** : Rendre l'import SQLAlchemy optionnel dans `backend_worker/utils/celery_retry_config.py` :
```python
try:
    import sqlalchemy
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    sqlalchemy = None
```

**Commit** : `179dc93`

---

**Statut global** : 🟢 Fixes #1, #2 et #3 terminés - **Redémarrage des conteneurs requis**

### Commandes pour appliquer les changements

```powershell
# Créer le dossier pour le cache HuggingFace
mkdir -p data/huggingface_cache

# Redémarrer les conteneurs avec les nouveaux volumes
docker-compose up -d --force-recreate celery-worker frontend
```

### Vérification post-déploiement

1. **Test DNS** : `docker-compose exec celery-worker curl http://library:8001/api/healthcheck`
2. **Test retry** : Vérifier dans les logs que les erreurs DNS sont suivies de retries automatiques
3. **Test cache** : La deuxième exécution du training ne doit pas re-télécharger le modèle
