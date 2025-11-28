# Plan d'amélioration du Worker Cover - SoniqueBay

## Contexte

Le système actuel de gestion des covers fonctionne mais présente des limitations :

- Intégration complexe avec les callbacks
- Gestion insuffisante des erreurs
- Manque de fallback et de priorisation
- Pas de monitoring dédié

## Objectifs

1. **Créer un worker covers dédié** avec arquitectura modulaire
2. **Améliorer la robustesse** avec retry et fallback
3. **Optimiser les performances** sur Raspberry Pi 4
4. **Ajouter le monitoring** et la gestion de progression
5. **Intégrer avec les APIs externes** (MusicBrainz, Last.fm, etc.)

## Architecture proposée

### 1. Worker Cover spécialisé

```
backend_worker/background_tasks/
├── worker_cover.py              # ✅ Existe déjà - à améliorer
├── worker_cover_service.py      # 🆕 Service métier dédié
├── worker_cover_deferred.py     # 🆕 Tâches différées
└── worker_cover_optimizer.py    # 🆕 Optimisations RPi4
```

### 2. Services spécialisés

```
backend_worker/services/
├── image_service.py            # ✅ Existe déjà
├── coverart_service.py         # ✅ Existe déjà  
├── lastfm_service.py           # 🆕 Service Last.fm
├── musicbrainz_service.py      # 🆕 Service MusicBrainz
├── image_processor.py          # 🆕 Traitement d'images
└── cover_cache_service.py      # 🆕 Cache intelligent
```

### 3. Configuration améliorée

- Queue dédiée "cover_worker" avec ressources optimisées
- Retry automatique avec backoff exponentiel
- Priorisation des covers critiques
- Monitoring et métriques

## Plan d'implémentation

### Phase 1: Optimisation du worker existant

- [ ] Améliorer la gestion d'erreurs
- [ ] Ajouter le système de retry
- [ ] Optimiser pour Raspberry Pi 4
- [ ] Ajouter le monitoring

### Phase 2: Nouveaux services

- [ ] Service MusicBrainz pour covers d'albums
- [ ] Service Last.fm pour images d'artistes
- [ ] Cache intelligent des images
- [ ] Processeur d'images avec optimisation

### Phase 3: Intégration et tests

- [ ] Tests unitaires complets
- [ ] Tests d'intégration
- [ ] Documentation technique
- [ ] Déploiement

## Fonctionnalités spécifiques

### 1. Priorisation intelligente

- **High Priority**: Covers demandées par l'utilisateur
- **Normal Priority**: Covers d'artistes populaires
- **Low Priority**: Covers de fichiers de backup

### 2. Stratégies de fallback

1. **Embedded covers** (métadonnées du fichier)
2. **Local files** (dossier de l'album/artiste)
3. **Cover Art Archive** (MusicBrainz)
4. **Last.fm** (images d'artistes)
5. **Génération automatique** (placeholder)

### 3. Optimisations RPi4

- Compression d'images automatique
- Cache en mémoire limité
- Traitement asynchrone
- Nettoyage automatique

### 4. Monitoring avancé

- Métriques de performance
- Taux de succès par source
- Statistiques de cache
- Alertes en cas d'échec

## Fichiers à modifier/créer

### Modifications

- `backend_worker/background_tasks/worker_cover.py` - Améliorations
- `backend_worker/services/entity_manager.py` - ✅ Corrections déjà apportées

### Nouveaux fichiers

- `backend_worker/services/musicbrainz_service.py`
- `backend_worker/services/lastfm_service.py`
- `backend_worker/services/image_processor.py`
- `backend_worker/services/cover_cache_service.py`
- `backend_worker/services/worker_cover_service.py`
- `backend_worker/background_tasks/worker_cover_deferred.py`
- `backend_worker/background_tasks/worker_cover_optimizer.py`

### Tests

- `tests/worker/test_worker_cover_improvements.py`
- `tests/worker/test_cover_services.py`

## Intégration avec le flux existant

### 1. Scan de musique

```
Scan Worker → Metadata Worker → Entity Manager
                           ↓
                    Cover Worker (auto)
                           ↓
                    Database + Cache
```

### 2. Lecture de métadonnées

```
Metadata Worker → Extract Covers → Cover Worker
                           ↓
                    Artist Images + Album Covers
```

### 3. API requests

```
Frontend → Library API → Cover Worker (async)
                           ↓
                    Cache Service
```

## Métriques de succès

- [ ] 95% de taux de succès pour covers embedded
- [ ] 80% de taux de succès pour sources externes
- [ ] Temps de réponse < 5s pour covers local
- [ ] Utilisation mémoire < 200MB
- [ ] Zéro crash sur 24h de fonctionnement

## Prochaines étapes

1. **Implémenter Phase 1** (optimisations critiques)
2. **Créer les services spécialisés**
3. **Ajouter les tests**
4. **Déployer en production**

---
*Document créé le 2025-11-01*
