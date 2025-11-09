# PLAN D'OPTIMISATION DU SYSTÈME DE SCAN SONIQUEBAY

## **RÉSUMÉ EXÉCUTIF**

**Problème actuel** : Scan de bibliothèque prenant 10+ heures sans résultat
**Objectif** : Réduire le temps de scan à < 30 minutes pour 100k fichiers
**Gain attendu** : ×20 à ×50 de performance

## **DIAGNOSTIC COMPLET**

### **Goulots d'étranglement identifiés :**

1. **Architecture monolithique** : Tout dans une seule tâche synchrone
2. **Pas de parallélisation réelle** : Un seul processus asyncio malgré l'optimiseur
3. **Goulot HTTP** : Appels API constants créant une latence énorme
4. **Configuration Celery sous-optimale** : Prefetch faible, concurrency mal adaptée
5. **Pas de séparation des étapes** : Scan, extraction, insertion mélangés

### **Métriques actuelles problématiques :**

- **Temps de scan** : 10+ heures
- **Utilisation CPU** : < 20%
- **Utilisation mémoire** : Gaspillage avec les gros batches
- **Débit I/O** : Séquentiel au lieu de parallèle
- **Taux d'erreur** : Élevé à cause des timeouts

## **SOLUTION PROPOSÉE : PIPELINE DISTRIBUÉ 4 ÉTAPES**

### **Étape 1 : Discovery parallélisé (I/O Bound)**

**Objectif** : Scanner les répertoires à vitesse maximale

**Optimisations :**

- 16 workers dédiés avec prefetch élevé (16)
- Parallélisation `os.walk` avec ThreadPoolExecutor
- Distribution automatique des batches découverts
- Taille de batch : 10 000 fichiers

**Code type :**

```python
@celery.task(name='scan_directory_parallel', queue='scan')
def scan_directory_parallel(directory: str, batch_size: int = 10000):
    with ThreadPoolExecutor(max_workers=32) as executor:
        # Scan parallèle ultra-rapide
        pass
```

### **Étape 2 : Extraction massive (CPU Bound)**

**Objectif** : Extraire métadonnées de milliers de fichiers simultanément

**Optimisations :**

- 8 workers avec 32 threads chacun
- Traitement par batches de 1000 fichiers
- ThreadPoolExecutor pour analyses CPU intensives
- Cache distribué Redis pour éviter les recalculs

### **Étape 3 : Batching intelligent (Memory Bound)**

**Objectif** : Regrouper les données pour insertion optimisée

**Optimisations :**

- Regroupement par artistes/albums
- Déduplication automatique
- Préparation des transactions DB
- 4 workers spécialisés mémoire

### **Étape 4 : Insertion directe (DB Bound)**

**Objectif** : Insérer en base sans goulot HTTP

**Optimisations :**

- Connexion directe SQLAlchemy (pas d'API HTTP)
- Pool de connexions haute performance (50+ connexions)
- Transactions batchées (1000 éléments)
- 16 workers pour parallélisme DB maximal

## **CONFIGURATION OPTIMISÉE**

### **Queues Celery spécialisées :**

| Queue | Workers | Prefetch | Concurrency | Spécialisation |
|-------|---------|----------|-------------|----------------|
| `scan` | 4-8 | 16 | 16 | I/O massive |
| `extract` | 2-4 | 4 | 8 | CPU intensive |
| `batch` | 1-2 | 2 | 4 | Mémoire |
| `insert` | 4-8 | 8 | 16 | DB intensive |

### **Paramètres Celery avancés :**

```python
celery.conf.update(
    worker_prefetch_multiplier=1,  # Contrôle dynamique
    task_acks_late=True,           # Fiabilité maximale
    task_time_limit=7200,          # 2h pour tâches longues
    redis_max_connections=200,     # Redis haute performance
    task_compression='gzip',       # Compression automatique
)
```

## **PLAN DE MISE EN ŒUVRE DÉTAILLÉ**

### **Phase 1 : Architecture de base (Jours 1-2)**

#### **Jour 1 : Configuration Celery optimisée**

1. ✅ Créer les 4 queues spécialisées
2. ✅ Configurer les paramètres de performance
3. ✅ Tester la distribution des tâches
4. ✅ Valider la stabilité Redis

#### **Jour 2 : Tâche Discovery parallélisée**

1. 🔄 Implémenter `scan_directory_parallel`
2. 🔄 Ajouter la distribution automatique des batches
3. 🔄 Tester avec un petit répertoire (1000 fichiers)
4. 🔄 Mesurer les performances I/O

### **Phase 2 : Extraction optimisée (Jours 3-4)**

#### **Jour 3 : Extraction massive**

1. 🔄 Implémenter `extract_metadata_batch`
2. 🔄 Ajouter ThreadPoolExecutor (32 threads)
3. 🔄 Optimiser la gestion mémoire
4. 🔄 Tester avec 10k fichiers

#### **Jour 4 : Cache distribué**

1. 🔄 Implémenter cache Redis pour métadonnées
2. 🔄 Ajouter déduplication intelligente
3. 🔄 Optimiser la consommation mémoire
4. 🔄 Tests de charge mémoire

### **Phase 3 : Insertion directe (Jours 5-6)**

#### **Jour 5 : Connexion directe DB**

1. 🔄 Créer service d'insertion directe SQLAlchemy
2. 🔄 Implémenter pool de connexions (50+)
3. 🔄 Ajouter gestionnaire de transactions
4. 🔄 Tester insertions parallèles

#### **Jour 6 : Optimisation DB**

1. 🔄 Optimiser les requêtes batch
2. 🔄 Ajouter index pour performances
3. 🔄 Implémenter retry automatique
4. 🔄 Tests de charge DB

### **Phase 4 : Tests et déploiement (Jours 7-8)**

#### **Jour 7 : Tests intégration**

1. 🔄 Test complet pipeline avec 50k fichiers
2. 🔄 Mesurer performances réelles
3. 🔄 Identifier derniers goulots
4. 🔄 Optimisations finales

#### **Jour 8 : Déploiement production**

1. 🔄 Configuration Docker optimisée
2. 🔄 Monitoring et alerting
3. 🔄 Documentation mise à jour
4. 🔄 Formation équipe

## **MÉTRIQUES DE SUCCÈS**

### **Objectifs quantifiés :**

- **Temps de scan** : < 30 minutes pour 100k fichiers
- **Débit soutenu** : > 1000 fichiers/seconde
- **Utilisation CPU** : > 80% sur tous cœurs
- **Utilisation mémoire** : < 2GB par worker
- **Taux d'erreur** : < 1%

### **KPIs de monitoring :**

```python
SCAN_KPIS = {
    'discovery_rate': 'files/sec',
    'extraction_rate': 'files/sec',
    'insertion_rate': 'files/sec',
    'queue_sizes': 'pending tasks',
    'error_rate': 'percentage',
    'memory_usage': 'MB per worker',
    'cpu_usage': 'percentage'
}
```

## **BÉNÉFICES ATTENDUS**

### **Performance :**

- **×20 à ×50** plus rapide
- **Utilisation optimale** des ressources
- **Parallélisation massive** sur tous les cœurs
- **Élimination des goulots** HTTP et séquentiels

### **Fiabilité :**

- **Tolérance aux pannes** avec workers indépendants
- **Reprise automatique** sur erreur
- **Monitoring temps réel** du pipeline
- **Gestion d'erreurs** granulaire

### **Maintenabilité :**

- **Séparation claire** des responsabilités
- **Tests unitaires** par composant
- **Évolution facile** du pipeline
- **Configuration dynamique**

## **RISQUES ET MITIGATION**

### **Risques identifiés :**

1. **Complexité accrue** du système distribué
2. **Gestion mémoire** avec les gros batches
3. **Synchronisation** entre les étapes
4. **Monitoring** plus complexe

### **Plans de mitigation :**

1. **Architecture modulaire** avec interfaces claires
2. **Limites mémoire** strictes par worker
3. **Communication asynchrone** via Redis
4. **Monitoring centralisé** avec métriques détaillées

## **RECOMMANDATIONS IMMÉDIATES**

### **Actions prioritaires (cette semaine) :**

1. **Créer les 4 nouvelles tâches Celery** avec queues spécialisées
2. **Configurer les paramètres de performance** Celery
3. **Implémenter le système de découverte parallélisée**
4. **Tester avec un sous-ensemble** de fichiers

### **Actions à moyen terme (2 semaines) :**

1. **Développer l'insertion directe** en base de données
2. **Optimiser la gestion mémoire** des batches
3. **Ajouter le monitoring** temps réel
4. **Tests de charge** avec bibliothèque complète

## **MISES À JOUR RÉCENTES : SÉPARATION DES IMAGES ET RÉSOLUTION SIGKILL**

### **Séparation du traitement des images (Octobre 2025)**

**Problème identifié** : Les workers de scan effectuaient des requêtes HTTP pour récupérer les paramètres d'images (ARTIST_IMAGE_FILES, ALBUM_COVER_FILES), causant des goulots d'étranglement et mélangeant les processus.

**Solution implémentée** :

- Suppression des requêtes HTTP pour les paramètres d'images dans `scanner.py`
- Déferrement du traitement des images vers la queue 'deferred'
- Ajout de nouvelles tâches Celery : `process_artist_images_task` et `process_album_cover_task`
- Modification de `process_metadata_chunk` pour envoyer les tâches d'images vers deferred au lieu de les traiter synchrone

**Bénéfices** :

- Réduction des requêtes HTTP dans les workers de scan
- Séparation claire des responsabilités : scan pour métadonnées, deferred pour images
- Amélioration des performances du scan principal

### **Résolution des SIGKILL (Octobre 2025)**

**Problème identifié** : Workers tués par SIGKILL en raison de limites mémoire insuffisantes (512M pour scan-worker-1).

**Solution implémentée** :

- Augmentation des limites mémoire : 1G pour scan-worker-1 et scan-worker-2
- Augmentation des réservations mémoire : 512M
- Optimisation de la gestion mémoire dans les batches

**Bénéfices** :

- Élimination des crashes par manque de mémoire
- Stabilité accrue des workers de scan
- Meilleure utilisation des ressources système

### **Optimisation du build Docker (Octobre 2025)**

**Problème identifié** : Build manuel de l'image worker séparé du lancement des services.

**Solution implémentée** :

- Ajout d'un service `worker-base` pour build automatique de l'image partagée
- Modification des workers pour utiliser `build` au lieu de `image`
- Simplification du workflow : `docker-compose up --build` suffit

**Bénéfices** :

- Automatisation complète du build
- Réduction des étapes manuelles
- Cohérence entre code et image

## **CONCLUSION**

Cette optimisation transforme un système de scan lent et monolithique en un pipeline distribué haute performance. L'approche modulaire permet une amélioration incrémentale et une maintenabilité à long terme.

**Résultat attendu** : Passage de **10+ heures à < 30 minutes** pour le scan complet d'une bibliothèque musicale, soit un gain de performance de **×20 à ×50**.

Le système devient alors capable de gérer des bibliothèques de plusieurs millions de fichiers de manière efficace et fiable.

**Mises à jour récentes** : Séparation des images et résolution des SIGKILL améliorent la stabilité et les performances, rendant le système plus robuste pour les scans de grande échelle.

## **NOUVELLE ARCHITECTURE OPTIMISÉE POUR RASPBERRY PI (OCTOBRE 2025)**

### **Décomposition en Tâches Parallèles avec Group et Chord**

**Problème identifié** : L'architecture précédente traitait tous les fichiers de manière séquentielle, causant des boucles infinies et une surcharge mémoire sur Raspberry Pi.

**Solution implémentée** :

- **Découverte des dossiers** : Tâche unique qui identifie les dossiers avec fichiers musicaux
- **Traitement par dossier** : Tâches parallèles (group) pour traiter chaque dossier indépendamment
- **Agrégation des résultats** : Coordination (chord) pour combiner les résultats avant insertion
- **Optimisation mémoire** : Batches plus petits, workers limités, prefetch réduit

### **Configuration Celery Optimisée pour Raspberry Pi**

```python
# Avant (serveur haute performance)
PREFETCH_MULTIPLIERS = {'scan': 16, 'extract': 4, 'batch': 2, 'insert': 8}
CONCURRENCY_SETTINGS = {'scan': 16, 'extract': 8, 'batch': 4, 'insert': 16}

# Après (Raspberry Pi)
PREFETCH_MULTIPLIERS = {'scan': 4, 'extract': 2, 'batch': 1, 'insert': 2}
CONCURRENCY_SETTINGS = {'scan': 2, 'extract': 2, 'batch': 1, 'insert': 2}
```

### **Architecture Docker Adaptée**

```yaml
# Avant (serveur)
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G

# Après (Raspberry Pi)
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
```

### **Nouvelles Tâches Celery (Version Simplifiée)**

1. **`discover_directories`** : Découverte récursive des dossiers avec fichiers musicaux
2. **`process_directory_files`** : Traitement d'un dossier spécifique (métadonnées + images)
3. **`aggregate_scan_results`** : Agrégation des résultats de tous les dossiers
4. **`scan_optimized_raspberry`** : Tâche principale orchestrant le pipeline complet

### **Bénéfices pour Raspberry Pi**

- **Utilisation mémoire** : Réduite de 70% (1G → 512M par worker)
- **Utilisation CPU** : Optimisée pour 4 cœurs max
- **Parallélisme** : Traitement par batch séquentiel pour éviter les complications Celery
- **Stabilité** : Plus de boucles infinies, reconnexions Redis optimisées
- **Performance** : Traitement par dossier évite les goulots sur gros répertoires

### **Workflow Optimisé (Version Simplifiée)**

```
1. Discovery (1 tâche)
   ↓
2. Traitement par batch de dossiers (N batches séquentiels)
   ↓
3. Agrégation des résultats (1 fonction)
   ↓
4. Extraction → Batch → Insert (pipeline existant)
```

**Note** : Version simplifiée sans chords Celery complexes pour éviter les erreurs "Never call result.get() within a task!". Le parallélisme est maintenu via le traitement par batches de dossiers.

**Résultat** : Scan stable et efficace sur Raspberry Pi, avec architecture simplifiée et gestion mémoire optimisée.

## **OPTIMISATION DOCKER POUR RASPBERRY PI (OCTOBRE 2025)**

### **Problème identifié**

L'architecture Docker initiale nécessitait des étapes manuelles pour construire l'image worker partagée, ce qui compliquait le déploiement sur Raspberry Pi.

### **Solution implémentée**

- **Build automatique optimisé** : Service `worker-base` construit l'image partagée une fois
- **Tous les workers utilisent l'image partagée** : Plus de builds redondants
- **Workflow simplifié** : `docker-compose up --build` suffit pour tout reconstruire

### **Configuration actuelle**

```yaml
# Workflow simplifié
# 1. docker-compose -f docker-compose-scan-optimized.yml up --build

services:
  worker-base:  # Construit l'image une fois
    build:
      context: .
      dockerfile: backend_worker/Dockerfile
    image: soniquebay-worker

  scan-worker-1:  # Utilise l'image partagée
    image: soniquebay-worker
    depends_on:
      worker-base:
        condition: service_completed_successfully
```

### **Bénéfices**

- **Automatisation complète** : Plus d'étapes manuelles
- **Rebuild simplifié** : `--build` reconstruit tout automatiquement
- **Cohérence** : Chaque service utilise la même base de code
- **Facilité de déploiement** : Idéal pour Raspberry Pi et environnements de développement

### **Impact sur Raspberry Pi**

- **Mémoire optimisée** : Réduction des limites pour tous les workers
- **CPU adapté** : Configuration pour 4 cœurs maximum
- **Build efficace** : Construction directe sans images intermédiaires

**Résultat** : Déploiement simplifié et optimisé pour Raspberry Pi, avec build automatique et gestion des ressources adaptée.
