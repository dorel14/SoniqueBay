# 🌸 Flower - Monitoring Celery pour SoniqueBay

## Vue d'ensemble

Flower est un outil de monitoring web pour Celery qui offre une interface moderne et complète pour surveiller les tâches, workers et queues du système SoniqueBay optimisé.

## 🚀 Démarrage

### Accès à Flower

Une fois le système déployé, accédez à Flower sur :

```
http://localhost:5555/flower
```

### Authentification

- **Username** : `admin`
- **Password** : `soniquebay2024`

## 📊 Fonctionnalités

### Dashboard Principal

- **Vue d'ensemble** des workers actifs
- **État des queues** (scan, extract, batch, insert, deferred)
- **Métriques en temps réel** des tâches

### Monitoring des Workers

- **52 workers spécialisés** :
  - Scan : 16 workers I/O (2 conteneurs × 16)
  - Extract : 8 workers CPU (2 conteneurs × 8)
  - Batch : 4 workers mémoire (1 conteneur × 4)
  - Insert : 16 workers DB (2 conteneurs × 16)
  - Deferred : 6 workers background (1 conteneur × 6)

### Gestion des Tâches

- **Liste des tâches** actives, réservées, réussies, échouées
- **Détails des tâches** avec arguments et résultats
- **Historique** avec filtrage par état
- **Retry automatique** des tâches échouées

### Métriques Avancées

- **Latence** des messages broker
- **Débit** des tâches par queue
- **Utilisation mémoire** par worker
- **Temps d'exécution** moyen

## 🎯 Queues Surveillées

| Queue | Workers | Fonction | Prefetch |
|-------|---------|----------|----------|
| **scan** | 16 | Découverte fichiers | 16 |
| **extract** | 8 | Extraction métadonnées | 4 |
| **batch** | 4 | Regroupement données | 2 |
| **insert** | 16 | Insertion base | 8 |
| **deferred** | 6 | Tâches background | 6 |

## 🔧 Configuration Flower

### Commande Docker

```bash
celery -A backend_worker flower \
  --broker=redis://redis:6379/0 \
  --broker_api=http://redis:6379/0 \
  --url_prefix=flower \
  --auto_refresh=True \
  --format=json
```

### Options Principales

- `--auto_refresh=True` : Actualisation automatique
- `--format=json` : Format de sortie optimisé
- `--basic_auth` : Authentification sécurisée

## 📈 Utilisation Pratique

### Surveillance en Production

1. **Vérifier l'état des workers** sur le dashboard
2. **Monitorer les queues** pour détecter les goulots
3. **Analyser les tâches échouées** pour debugging
4. **Suivre les performances** en temps réel

### Debugging

- **Tâches bloquées** : Identifier et terminer si nécessaire
- **Workers inactifs** : Vérifier la connectivité Redis
- **Erreurs répétées** : Analyser les patterns d'échec

## 🌐 Interface Web

### Navigation

- **Dashboard** : Vue générale
- **Workers** : État des processus
- **Tasks** : Liste des tâches
- **Queues** : Gestion des files
- **Monitor** : Métriques détaillées

### Filtres Utiles

- Filtrer par **état** (active, reserved, success, failure)
- Filtrer par **nom de tâche** (scan, extract, batch, insert)
- Trier par **date** ou **durée d'exécution**

## 🔒 Sécurité

- **Authentification basique** activée
- **Accès restreint** aux métriques sensibles
- **Logs sécurisés** dans les volumes Docker

## 🚨 Alertes et Monitoring

Flower s'intègre parfaitement avec les systèmes de monitoring externes pour :

- Alertes sur **taux d'échec élevé**
- Monitoring de **latence des queues**
- Détection de **workers défaillants**

---

**Flower offre une visibilité complète sur le pipeline de traitement musical haute performance de SoniqueBay !** 🎵📊
