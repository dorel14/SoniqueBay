# Configuration Redis Actuelle — SoniqueBay

## 📋 Résumé

**Date** : 2026-03-20  
**Phase** : 0 (Audit et Préparation)  
**Objectif** : Documenter l'utilisation actuelle de Redis par Celery pour préparer la migration TaskIQ

---

## 🔗 URLs Redis Utilisées

### Worker Celery
- **Broker** : `redis://redis:6379/0` (par défaut)
- **Backend résultats** : `redis://redis:6379/0` (par défaut)
- **Variable d'environnement** : `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

### API FastAPI
- **Broker** : `redis://redis:6379/0` (par défaut)
- **Backend résultats** : `redis://redis:6379/0` (par défaut)
- **Variable d'environnement** : `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

### TaskIQ (à venir)
- **Broker** : `redis://redis:6379/1` (DB différente pour coexistence)
- **Backend résultats** : `redis://redis:6379/1`
- **Variable d'environnement** : `TASKIQ_BROKER_URL`, `TASKIQ_RESULT_BACKEND`

---

## 📊 Clés Redis Utilisées par Celery

### Broker (Queue)
- **Pattern** : `_kombu.binding.*`
- **Exemple** : `_kombu.binding.scan`, `_kombu.binding.extract`
- **TTL** : Persistant (supprimé après consommation)
- **Format** : Messages JSON sérialisés

### Backend Résultats
- **Pattern** : `celery-task-meta-*`
- **Exemple** : `celery-task-meta-abc123-def456`
- **TTL** : 86400 secondes (24 heures) par défaut
- **Format** : JSON avec statut, résultat, traceback

### Configuration Partagée
- **Clé** : `celery_config`
- **Contenu** : Configuration Celery complète (task_routes, task_queues, etc.)
- **TTL** : Persistant
- **Format** : JSON

### Heartbeat Workers
- **Pattern** : `celery-worker-heartbeat-*`
- **Exemple** : `celery-worker-heartbeat-worker@hostname`
- **TTL** : 300 secondes (5 minutes)
- **Format** : JSON avec timestamp, hostname, load

### Pidbox (Inspection)
- **Pattern** : `celery.pidbox.*`
- **Exemple** : `celery.pidbox.worker@hostname`
- **TTL** : Éphémère (supprimé après réponse)
- **Format** : Messages JSON

---

## ⚙️ Configuration Redis Optimisée

### Pool de Connexions
```python
'redis_max_connections': 20,  # Réduit pour éviter surcharge
'broker_pool_limit': 5,       # Pool plus petit pour stabilité
```

### Timeouts
```python
'result_backend_transport_options': {
    'socket_timeout': 30,           # Timeout plus long pour stabilité
    'socket_connect_timeout': 20,   # Connexion plus tolérante
    'retry_on_timeout': True,
    'socket_keepalive': True,
    'socket_keepalive_options': {},
    'health_check_interval': 30,    # Health check plus espacé
}
```

### Sérialisation
```python
'task_serializer': 'json',
'accept_content': ['json'],
'result_serializer': 'json',
'result_accept_content': ['json'],
'timezone': 'UTC',
'enable_utc': True,
```

---

## 🔄 Synchronisation Configuration

### Mécanisme
1. **Worker** : Écrit la configuration dans Redis (clé `celery_config`)
2. **API** : Lit la configuration depuis Redis au démarrage
3. **Fréquence** : Mise à jour à chaque redémarrage du worker

### Fichiers Impliqués
- [`backend_worker/celery_config_source.py`](backend_worker/celery_config_source.py) — Source de vérité (worker)
- [`backend/api/utils/celery_config_loader.py`](backend/api/utils/celery_config_loader.py) — Lecture depuis Redis (API)

---

## 📦 Queues Configurées

### Queues Prioritaires
| Queue | Priorité | Tâches |
|-------|----------|--------|
| `scan` | 5 | `scan.discovery` |
| `extract` | 5 | `metadata.extract_batch` |
| `batch` | 5 | `batch.process_entities` |
| `insert` | 7 | `insert.direct_batch` |

### Queues Normales
| Queue | Priorité | Tâches |
|-------|----------|--------|
| `covers` | 5 | Tâches covers |
| `deferred_covers` | 7 | `covers.extract_embedded` |
| `maintenance` | 5 | Tâches maintenance |
| `vectorization_monitoring` | 5 | Monitoring vectorisation |
| `celery` | 5 | Tâches par défaut |
| `audio_analysis` | 5 | Analyse audio |
| `mir` | 5 | Pipeline MIR |

### Queues Différées (Priorité Basse)
| Queue | Priorité | Tâches |
|-------|----------|--------|
| `deferred_vectors` | 9 | Vectorisation différée |
| `deferred_enrichment` | 8 | Enrichissement différé |
| `deferred` | 9 | Tâches différées (GMM, Last.fm, Synonymes) |

---

## 🔍 Patterns de Clés pour Monitoring

### À Surveiller
```bash
# Messages en attente
redis-cli KEYS "_kombu.binding.*" | wc -l

# Résultats stockés
redis-cli KEYS "celery-task-meta-*" | wc -l

# Heartbeats actifs
redis-cli KEYS "celery-worker-heartbeat-*" | wc -l

# Configuration
redis-cli GET celery_config
```

### Métriques Importantes
- **Queue depth** : Nombre de messages en attente par queue
- **Result count** : Nombre de résultats stockés
- **Worker count** : Nombre de heartbeats actifs
- **Memory usage** : Mémoire Redis utilisée

---

## 🎯 Points d'Attention pour Migration TaskIQ

### 1. Séparation des Bases Redis
- **Celery** : DB 0 (existant)
- **TaskIQ** : DB 1 (nouveau)
- **Raison** : Éviter les conflits pendant la coexistence

### 2. Clés à Migrer
- `celery_config` → `taskiq_config` (ou garder les deux)
- Patterns de résultats : `celery-task-meta-*` → `taskiq-result-*`
- Heartbeats : Adapter le format pour TaskIQ

### 3. Queue Names
- TaskIQ peut utiliser les mêmes noms de queues
- Les routing_keys doivent être adaptés
- Les priorités peuvent être gérées différemment

### 4. Sérialisation
- TaskIQ supporte JSON natif (compatible avec Celery)
- Pas de changement nécessaire pour les payloads

### 5. Monitoring
- Adapter les scripts de monitoring pour TaskIQ
- Garder la compatibilité avec les outils existants pendant la coexistence

---

## 📝 Recommandations

1. **Phase 1** : Utiliser DB 1 pour TaskIQ (coexistence propre)
2. **Phase 2** : Migrer progressivement les clés de configuration
3. **Phase 3** : Adapter les scripts de monitoring
4. **Phase 5** : Nettoyer les clés Celery après décommission

---

## 🔗 Références

- [`backend_worker/celery_config_source.py`](backend_worker/celery_config_source.py) — Configuration source
- [`backend/api/utils/celery_app.py`](backend/api/utils/celery_app.py) — Configuration API
- [`backend/api/utils/celery_config_loader.py`](backend/api/utils/celery_config_loader.py) — Chargement config

---

*Dernière mise à jour : 2026-03-20*
*Phase : 0 (Audit et Préparation)*
