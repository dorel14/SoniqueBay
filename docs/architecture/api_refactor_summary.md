# Résumé de la Refactorisation API - Passage SQLite → PostgreSQL

## Contexte

Suite à la migration complète vers PostgreSQL et Redis, une refactorisation majeure de l'API a été réalisée pour supprimer tout code obsolète lié à SQLite, TinyDB et sqlite-vec.

## Changements Principaux

### 1. Suppression du Code Obsolète

**Fichiers supprimés :**
- `tinydb_handler.py` - Gestionnaire TinyDB pour la playqueue
- `sqlite_vec_init.py` - Initialisation des tables virtuelles sqlite-vec
- `track_vectors_model.py` (partie virtuelle) - Modèle pour tables sqlite-vec

**Dépendances supprimées de requirements.txt :**
- `aiosqlite==0.21.0`
- `tinydb==4.8.2`
- `sqlite-vec==0.1.6`

### 2. Restructuration du Dossier

**Avant :**
```
backend/api/
├── api/
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   └── services/
```

**Après :**
```
backend/api/
├── routers/
├── models/
├── schemas/
└── services/
```

Le sous-dossier `api/` redondant a été supprimé, simplifiant la structure.

### 3. Migration des Données

**Playqueue :**
- Passage de TinyDB vers modèle PostgreSQL `PlayQueue`
- Création du modèle `PlayQueueModel` avec relations appropriées
- Service refactorisé pour utiliser SQLAlchemy au lieu de TinyDB

**Analyses en attente :**
- Déjà gérées par les workers Celery, aucune migration nécessaire

### 4. Services Refactorisés

**PlayQueueService :**
- Remplacement des opérations TinyDB par des requêtes SQLAlchemy
- Gestion des positions et ordre des pistes via base de données

**Services vectoriels :**
- Suppression des références à sqlite-vec
- Utilisation directe de PostgreSQL avec pgvector (si disponible) ou stockage JSON

### 5. Configuration Mise à Jour

**settings.py :**
- Défaut changé de `'sqlite'` à `'postgres'`
- Support maintenu pour SQLite en cas de besoin

### 6. Imports Nettoyés

Tous les imports obsolètes ont été supprimés :
- `from backend.api.utils.tinydb_handler import TinyDBHandler`
- `from backend.api.utils.sqlite_vec_init import *`
- Références à `aiosqlite` et `sqlite3`

## Avantages de la Refactorisation

### Performance
- Élimination des accès fichiers locaux pour la playqueue
- Requêtes optimisées via PostgreSQL
- Réduction de la latence pour les opérations temps réel

### Maintenabilité
- Code unifié autour de PostgreSQL
- Suppression de dépendances externes non nécessaires
- Structure de dossiers simplifiée

### Fiabilité
- Persistance garantie de la playqueue après redémarrage
- Transactions ACID pour les opérations critiques
- Meilleure gestion des erreurs

## Tests de Validation

- Vérification que tous les endpoints fonctionnent
- Tests d'intégration pour la playqueue
- Validation des performances après migration

## Impact sur l'Architecture

Cette refactorisation renforce l'architecture en éliminant les solutions temporaires (TinyDB, SQLite) au profit d'une stack unifiée PostgreSQL/Redis, plus adaptée aux contraintes RPi4 et aux besoins de production.

---

*Refactorisation réalisée le 22 novembre 2025*