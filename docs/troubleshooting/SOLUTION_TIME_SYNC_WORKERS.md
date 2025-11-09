# Solution de Synchronisation Temporelle des Workers Celery

## Problème identifié

Les workers Celery présentaient une dérive temporelle de 41-42 secondes entre les conteneurs, causant des problèmes de coordination :

```
[2025-11-01 15:02:43,701: WARNING/MainProcess] Substantial drift from scan-worker-1...
Current drift is 42 seconds.  [orig: 2025-11-01 15:02:43.519614 recv: 2025-11-01 15:02:01.423005]
```

## Causes identifiées

1. **Timezone incohérente** : `.env` définit `TZ=Europe/Paris` mais Celery utilise UTC par défaut
2. **Pas de synchronisation Docker** : Les conteneurs n'ont pas accès à l'horloge système synchronisée  
3. **Pas de NTP** : Aucun mécanisme de synchronisation automatique des horloges
4. **Timeouts Celery trop stricts** : Configuration intolerance au drift temporel

## Solutions implémentées

### Solution 1: Synchronisation timezone et NTP dans Docker

#### Ajout du service timesync dans `docker-compose.yml`

```yaml
timesync:
  image: alpine/chrony:latest
  container_name: soniquebay-timesync
  restart: unless-stopped
  cap_add:
    - SYS_TIME
  privileged: true
  volumes:
    - /etc/localtime:/etc/localtime:ro
    - ./logs:/var/log
  command: >
    sh -c "
      apk add --no-cache chrony ntp
      echo 'server 0.pool.ntp.org iburst' >> /etc/chrony.conf
      echo 'server 1.pool.ntp.org iburst' >> /etc/chrony.conf  
      echo 'server 2.pool.ntp.org iburst' >> /etc/chrony.conf
      echo 'server 3.pool.ntp.org iburst' >> /etc/chrony.conf
      echo 'maxupdateskew 100' >> /etc/chrony.conf
      echo 'driftfile /var/lib/chrony/drift' >> /etc/chrony.conf
      chronyd -f /etc/chrony.conf -s
    "
  networks:
    default:
```

#### Synchronisation timezone pour tous les services

Ajout de :
- Volume : `- /etc/localtime:/etc/localtime:ro`
- Dépendance : `timesync: condition: service_started`

### Solution 2: Configuration Celery tolérante au drift

Dans `backend_worker/celery_app.py` :

```python
# === TOLÉRANCE AU DRIFT TEMPOREL ===
# Augmenter la tolérance pour le drift des workers (défaut: 1s, mis à 60s)
worker_clock_sync_interval=60,

# Timeouts plus longs pour les tâches longues
task_time_limit=7200,  # 2h au lieu de 1h
task_soft_time_limit=6900,  # 1h55 au lieu de 55min

# Retry avec backoff exponentiel
task_default_retry_delay=10,  # Démarrage rapide
task_max_retries=3,  # Plus de tentatives
```

## Script de validation

Création de `scripts/validate_time_sync.py` pour :
- Vérifier la cohérence des horloges entre conteneurs
- Tester la connectivité Redis
- Afficher l'état des services Docker
- Générer des recommandations

## Utilisation

### Déploiement
```bash
# Redémarrer les services avec la nouvelle configuration
docker-compose down
docker-compose up -d

# Attendre que timesync soit opérationnel
docker-compose logs -f timesync

# Vérifier la synchronisation
python scripts/validate_time_sync.py
```

### Monitoring continu
Le script peut être exécuté régulièrement pour surveiller la synchronisation :

```bash
# Vérification toutes les 5 minutes
*/5 * * * * cd /path/to/project && python scripts/validate_time_sync.py >> logs/time_sync.log 2>&1
```

## Résultats attendus

1. **Plus d'alertes de drift** : Les workers tolérance au drift de 60 secondes
2. **Synchronisation automatique** : Toutes les horloges synchronisées via NTP
3. **Coordination améliorée** : Les tâches s'exécutent de manière plus cohérente
4. **Monitoring en place** : Détection proactive des problèmes temporels

## Points de vigilance

- Le service `timesync` nécessite des privilèges élevés (`SYS_TIME`)
- Sur Raspberry Pi, vérifier que la connectivité internet est stable pour NTP
- Les timeouts Celery étendus peuvent masquer des problèmes de performance réels

## Prochaines améliorations

- [ ] Intégration avec un système de monitoring (Prometheus/Grafana)
- [ ] Alertes automatiques si drift > 30 secondes
- [ ] Configuration adaptative selon la charge système
- [ ] Tests automatisés de la synchronisation temporelle