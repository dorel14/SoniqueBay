# 🎵 SoniqueBay - Application de Gestion de Bibliothèque Musicale

**SoniqueBay** est une application moderne de gestion de bibliothèque musicale avec des fonctionnalités avancées de scan, d'analyse audio, de vectorisation et de recommandation.

## ✨ Nouvelles Fonctionnalités

### 📡 Streaming de Progression en Temps Réel (SSE)

SoniqueBay utilise maintenant **Server-Sent Events (SSE)** pour afficher la progression du scan en temps réel, remplaçant l'ancien système WebSocket qui ne fonctionnait pas correctement.

- **Barre de progression live** pendant le scan
- **Messages détaillés** sur chaque étape du processus
- **Interface responsive** avec mises à jour instantanées
- **Performance optimisée** avec connexions HTTP persistantes

```bash
# Le système SSE démarre automatiquement avec l'application
# Configuration dans les variables d'environnement
SSE_URL=http://library:8001/api/events
```

## 🚀 Démarrage Rapide

### Prérequis

- Docker et Docker Compose
- Python 3.11+
- Redis
- PostgreSQL (optionnel, SQLite par défaut)

### Installation

1. **Cloner le repository**

   ```bash
   git clone https://github.com/dorel14/SoniqueBay-app.git
   cd SoniqueBay-app
   ```

2. **Configuration**

   ```bash
   # Copier le fichier d'environnement
   cp .env.example .env

   # Ajuster les variables si nécessaire
   # SSE_URL=http://localhost:8001/api/events
   ```

3. **Démarrer les services**

   ```bash
   # Services principaux
   docker-compose up -d

   # Services optimisés (scan haute performance)
   docker-compose -f docker-compose-scan-optimized.yml up -d
   ```

4. **Accéder à l'application**
   - Frontend : <http://localhost:8080>
   - API Backend : <http://localhost:8001/api/docs>
   - Monitoring Celery (Flower) : <http://localhost:5555>

## 📁 Architecture

```
📦 SoniqueBay-app/
├── 🎨 frontend/              # Interface utilisateur NiceGUI
│   ├── theme/layout.py       # Layout avec barre de progression SSE
│   └── websocket_manager/     # Client SSE pour temps réel
├── 🔧 backend/library_api/   # API FastAPI + GraphQL
│   ├── api_app.py           # Endpoint SSE /api/events
│   └── services/            # Services métier
├── ⚙️ backend_worker/        # Workers Celery optimisés
│   ├── optimized_scan.py    # Scan avec progression SSE
│   └── background_tasks/    # Tâches avec publish_event
├── 🧪 tests/                # Tests d'intégration SSE
└── 📚 docs/                 # Documentation complète
    └── SSE_PROGRESSION.md   # Guide SSE détaillé
```

## 🎯 Fonctionnalités Principales

### 📊 Scan et Indexation

- **Scan parallélisé** : Traitement de milliers de fichiers simultanément
- **Extraction de métadonnées** : Tags ID3, FLAC, M4A avec Mutagen
- **Analyse audio** : BPM, clé, caractéristiques avec Librosa
- **Vectorisation** : Embeddings pour recommandations IA
- **Progression temps réel** : Via SSE avec détails étape par étape

### 🎵 Gestion de Bibliothèque

- **Artistes, Albums, Pistes** : Modèles SQLAlchemy complets
- **Recherche full-text** : Indexation Whoosh avancée
- **GraphQL API** : Mutations batch optimisées
- **Covers automatiques** : Téléchargement depuis Last.fm/MusicBrainz

### 🤖 Intelligence Artificielle

- **Recommandations** : Basées sur vecteurs et métadonnées
- **Analyse de similarité** : Recherche sémantique audio
- **Enrichissement automatique** : Métadonnées depuis APIs externes

## 🧪 Tests

```bash
# Tests unitaires
python -m pytest tests/ -v

# Tests d'intégration SSE
python -m pytest tests/test_sse_integration.py -v

# Tests de performance
python tests/benchmark/benchmark_optimized_scan.py

# Tests complets avec coverage
python -m pytest tests/ --cov=backend_worker --cov-report=html
```

## 📈 Performance

### Benchmarks Cibles

- **Scan** : 1000+ fichiers/minute
- **Extraction** : 500+ fichiers/minute
- **Insertion DB** : 2000+ enregistrements/minute
- **SSE** : 1000+ messages/seconde
- **Mémoire** : < 2GB pour 100k fichiers

### Optimisations Implémentées

- **Pipeline distribué** : 4 étapes parallèles (scan/extract/batch/insert)
- **Workers spécialisés** : Configuration Celery par type de tâche
- **Cache Redis** : Éviter les recalculs
- **Batch processing** : GraphQL mutations optimisées
- **Streaming SSE** : Progression temps réel efficace

## 🔧 Configuration

### Variables d'Environnement

```bash
# API
API_URL=http://library:8001
SSE_URL=http://library:8001/api/events
WS_URL=ws://library:8001/api/ws

# Base de données
DATABASE_URL=sqlite:///data/music.db

# Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Scan
CHUNK_SIZE=500
SCAN_TIMEOUT=300
```

### Services Docker

```yaml
services:
  # API avec SSE
  library_api:
    image: soniquebay-api:latest
    ports:
      - "8001:8001"
    environment:
      - SSE_URL=http://library:8001/api/events

  # Workers optimisés
  scan_worker:
    image: soniquebay-worker:latest
    command: celery -A backend_worker worker --queues=scan --concurrency=16

  # Frontend avec client SSE
  frontend:
    image: soniquebay-frontend:latest
    ports:
      - "8080:8080"
    environment:
      - SSE_URL=http://library:8001/api/events
```

## 📚 Documentation

- [📡 Guide SSE Complet](docs/SSE_PROGRESSION.md) - Server-Sent Events pour la progression
- [🏗️ Architecture Optimisée](docs/architecture.md) - Vue d'ensemble technique
- [⚙️ Configuration Celery](docs/celery_optimization_config.md) - Workers haute performance
- [🔍 Plan d'Optimisation](docs/plan_optimisation_scan.md) - Améliorations du scan
- [🧪 Tests d'Optimisation](docs/README_OPTIMIZATION_TESTS.md) - Validation des performances

## 🤝 Contribution

1. **Fork** le repository
2. **Créez** une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. **Committez** vos changements (`git commit -am 'Ajoute une nouvelle fonctionnalité'`)
4. **Pushez** vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. **Ouvrez** une Pull Request

### Règles de Contribution

- ✅ **Tests** : Tous les tests doivent passer
- ✅ **Documentation** : Mettre à jour la documentation
- ✅ **Code review** : Validation par les pairs
- ✅ **Performance** : Tests de performance avant merge
- ✅ **SSE** : Utiliser SSE pour les nouvelles fonctionnalités temps réel

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🙏 Remerciements

- **NiceGUI** pour l'interface utilisateur moderne
- **FastAPI** pour l'API performante
- **Celery** pour le traitement distribué
- **Redis** pour le cache et la communication
- **SQLAlchemy** pour l'ORM robuste

---

**🎵 SoniqueBay - Votre bibliothèque musicale, réinventée avec SSE !** 🚀
