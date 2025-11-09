## 1. Architecture

- **Framework** : FastAPI
- **Base de données** : SQLite pour stockage local et léger
- **Communication temps réel** : WebSocket avec le frontend
- **Tâches asynchrones** : `asyncio` ou Celery pour indexation et vectorisation

## 2. Endpoints principaux

| Endpoint           | Méthode       | Description |
|-------------------|---------------|-------------|
| `/artists`        | GET           | Retourne la liste des artistes |
| `/albums`         | GET           | Retourne la liste des albums filtrables par artiste |
| `/tracks`         | GET           | Retourne la liste des pistes filtrables par album, genre, BPM |
| `/playqueue`      | GET/POST/DELETE | Gestion de la file de lecture |
| `/recommendations`| GET           | Suggestions basées sur vecteurs et tags |
| `/search`         | GET           | Recherche hybride SQL + vectorielle |
| `/ws`             | WS            | WebSocket pour mises à jour temps réel |

## 3. Gestion asynchrone

- Indexation musicale : lecture des métadonnées et génération des vecteurs.
- Téléchargements/synchronisation : Last.fm, ListenBrainz, Napster.
- Monitoring système : CPU, RAM, stockage pour ajuster la charge.

## 4. Sécurité

- API locale avec authentification par token.
- Limiter l’accès externe pour éviter les failles.

## 5. Bonnes pratiques

1. Pagination et lazy loading pour les réponses volumineuses.
2. Optimiser les requêtes SQL avec indexes.
3. Tester tous les endpoints sur Raspberry Pi avant déploiement.