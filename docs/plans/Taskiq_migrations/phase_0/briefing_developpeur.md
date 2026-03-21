# Briefing Développeur — Phase 0 : Audit et Préparation

## 🎯 Objectif
Cartographier l'existant sans modifier le code. Cette phase est purement analytique.

---

## 📋 Tâches à Réaliser

### T0.1 : Lister toutes les tâches Celery avec leurs signatures
**Fichier** : `docs/plans/taskiq_migrations/audit/taches_celery.md`

**Actions** :
1. Ouvrir `backend_worker/celery_tasks.py`
2. Ouvrir `backend_worker/workers/` (tous les fichiers)
3. Lister chaque tâche Celery avec :
   - Nom complet (ex: `scan.discovery`)
   - Queue (ex: `scan`)
   - Priorité (ex: `5`)
   - Paramètres d'entrée
   - Type de retour
   - Idempotence (oui/non)
   - Criticité (basse/moyenne/haute)

**Commit** :
```bash
git add docs/plans/taskiq_migrations/audit/taches_celery.md
git commit -m "docs(taskiq): matrice complète des tâches Celery"
```

**Format** :
```markdown
# Matrice des Tâches Celery

## Tâches de Scan
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| scan.discovery | scan | 5 | directory: str | dict | Oui | Haute |

## Tâches de Métadonnées
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| metadata.extract_batch | extract | 5 | file_paths: list[str], batch_id: str | dict | Oui | Haute |

## Tâches de Batch
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| batch.process_entities | batch | 5 | metadata_list: list[dict], batch_id: str | dict | Oui | Haute |

## Tâches d'Insertion
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| insert.direct_batch | insert | 7 | insertion_data: dict | dict | Non | Haute |

## Tâches de Vectorisation
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| vectorization.calculate | vectorization | 5 | track_id: int, metadata: dict | dict | Oui | Moyenne |
| vectorization.batch | vectorization | 5 | track_ids: list[int] | dict | Oui | Moyenne |

## Tâches de Covers
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| covers.extract_embedded | deferred_covers | 7 | file_paths: list[str] | dict | Oui | Basse |

## Tâches d'Enrichissement
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| metadata.enrich_batch | deferred_enrichment | 8 | track_ids: list[int] | dict | Oui | Basse |

## Tâches GMM Clustering
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| gmm.cluster_all_artists | celery | 5 | force_refresh: bool | dict | Oui | Basse |
| gmm.cluster_artist | celery | 5 | artist_id: int | dict | Oui | Basse |
| gmm.refresh_stale_clusters | celery | 5 | max_age_hours: int | dict | Oui | Basse |
| gmm.cleanup_old_clusters | celery | 5 | - | dict | Oui | Basse |

## Tâches de Maintenance
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| maintenance.cleanup_old_data | maintenance | 5 | days_old: int | dict | Oui | Basse |

## Tâches d'Analyse Audio
| Nom | Queue | Priorité | Paramètres | Retour | Idempotent | Criticité |
|-----|-------|----------|------------|--------|------------|-----------|
| audio_analysis.extract_features | audio_analysis | 5 | file_paths: list[str] | dict | Oui | Moyenne |
```

**Validation** :
- [ ] Toutes les tâches sont listées
- [ ] Les informations sont complètes
- [ ] Le format est cohérent

---

### T0.2 : Documenter les dépendances entre tâches
**Fichier** : `docs/plans/taskiq_migrations/audit/dependances_taches.md`

**Actions** :
1. Analyser `backend_worker/celery_tasks.py`
2. Analyser `backend_worker/workers/` (tous les fichiers)
3. Identifier les appels `celery.send_task()`
4. Documenter les flux de tâches

**Commit** :
```bash
git add docs/plans/taskiq_migrations/audit/dependances_taches.md
git commit -m "docs(taskiq): documentation des dépendances entre tâches Celery"
```

**Format** :
```markdown
# Dépendances entre Tâches Celery

## Flux Principal de Scan
```
scan.discovery
    ↓
metadata.extract_batch (pour chaque batch de 50 fichiers)
    ↓
batch.process_entities
    ↓
insert.direct_batch
```

## Flux de Vectorisation
```
vectorization.calculate (pour chaque track)
    OU
vectorization.batch (pour un lot de tracks)
```

## Flux d'Enrichissement
```
metadata.enrich_batch (pour un lot de tracks)
```

## Flux de Covers
```
covers.extract_embedded (pour un lot de fichiers)
```

## Flux GMM Clustering
```
gmm.cluster_all_artists
    OU
gmm.cluster_artist (pour un artiste spécifique)
    OU
gmm.refresh_stale_clusters
    OU
gmm.cleanup_old_clusters
```

## Flux de Maintenance
```
maintenance.cleanup_old_data
```

## Flux d'Analyse Audio
```
audio_analysis.extract_features (pour un lot de fichiers)
```

## Dépendances Croisées
- `scan.discovery` déclenche `metadata.extract_batch`
- `metadata.extract_batch` déclenche `batch.process_entities`
- `batch.process_entities` déclenche `insert.direct_batch`
- Aucune autre dépendance directe entre les tâches
```

**Validation** :
- [ ] Tous les flux sont documentés
- [ ] Les dépendances sont correctes
- [ ] Le format est clair

---

### T0.3 : Exécuter la baseline des tests
**Fichier** : `docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt`

**Actions** :
1. Exécuter les tests unitaires worker
   ```bash
   python -m pytest tests/unit/worker -q --tb=no
   ```
2. Sauvegarder la sortie dans le fichier
3. Exécuter les tests d'intégration workers
   ```bash
   python -m pytest tests/integration/workers -q --tb=no
   ```
4. Sauvegarder la sortie dans `docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt`

**Commit** :
```bash
git add docs/plans/taskiq_migrations/audit/baseline_tests_unitaires.txt
git add docs/plans/taskiq_migrations/audit/baseline_tests_integration.txt
git commit -m "docs(taskiq): baseline des tests unitaires et intégration"
```

**Validation** :
- [ ] Les tests unitaires passent
- [ ] Les tests d'intégration passent
- [ ] Les fichiers de baseline sont créés

---

### T0.4 : Documenter la configuration Redis actuelle
**Fichier** : `docs/plans/taskiq_migrations/audit/configuration_redis.md`

**Actions** :
1. Ouvrir `backend_worker/celery_app.py`
2. Ouvrir `backend_worker/celery_config_source.py`
3. Ouvrir `backend/api/utils/celery_app.py`
4. Documenter :
   - URL du broker Redis
   - URL du backend Redis
   - Clés utilisées dans Redis
   - Format de sérialisation
   - TTL et patterns

**Commit** :
```bash
git add docs/plans/taskiq_migrations/audit/configuration_redis.md
git commit -m "docs(taskiq): documentation configuration Redis actuelle"
```

**Format** :
```markdown
# Configuration Redis Actuelle

## URLs
- **Broker URL** : `redis://redis:6379/0`
- **Backend URL** : `redis://redis:6379/0`

## Clés Redis Utilisées
- `celery_config:version` - Version de la configuration
- `celery_config:queues` - Configuration des queues
- `celery_config:routes` - Configuration des routes
- `celery_config:base` - Configuration de base

## Format de Sérialisation
- **Queues** : JSON (chaque queue est un objet JSON)
- **Routes** : JSON (chaque route est un objet JSON)
- **Base Config** : JSON (chaque paramètre est un objet JSON)

## TTL et Patterns
- **TTL** : Aucun (les clés persistent)
- **Patterns** : `celery_config:*`

## Configuration Celery
- **Serializer** : JSON
- **Accept Content** : JSON
- **Result Serializer** : JSON
- **Worker Send Task Events** : True
- **Task Send Sent Event** : True
- **Task Track Started** : True
- **Task Acks Late** : True
- **Task Reject On Worker Lost** : True
```

**Validation** :
- [ ] La configuration est documentée
- [ ] Les informations sont complètes
- [ ] Le format est clair

---

## 🧪 Tests à Exécuter

### Tests Unitaires
```bash
# Exécuter les tests unitaires worker
python -m pytest tests/unit/worker -q --tb=no
```

### Tests d'Intégration
```bash
# Exécuter les tests d'intégration workers
python -m pytest tests/integration/workers -q --tb=no
```

---

## ✅ Critères d'Acceptation

- [ ] Le fichier `taches_celery.md` est complet
- [ ] Le fichier `dependances_taches.md` est complet
- [ ] Le fichier `baseline_tests_unitaires.txt` est créé
- [ ] Le fichier `baseline_tests_integration.txt` est créé
- [ ] Le fichier `configuration_redis.md` est complet
- [ ] Tous les tests existants passent
- [ ] La documentation est claire et complète
- [ ] **Commit atomique** pour chaque livrable
- [ ] **Tag Git** `phase-0-complete` créé

---

## 🚨 Points d'Attention

1. **Ne pas modifier** le code existant
2. **Documenter** toutes les tâches, même celles qui semblent non critiques
3. **Vérifier** que les tests passent avant de documenter la baseline
4. **Être exhaustif** dans la documentation des dépendances

---

## 📞 Support

En cas de problème :
1. Consulter les fichiers source : `backend_worker/celery_tasks.py`, `backend_worker/workers/`
2. Exécuter les tests pour vérifier l'état actuel
3. Contacter le lead développeur

---

*Dernière mise à jour : 2026-03-20*
*Phase : 0 (Audit et Préparation)*
*Statut : En cours*
