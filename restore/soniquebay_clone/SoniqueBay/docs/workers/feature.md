# SoniqueBay - Features à implémenter

## 1. Gestion de la bibliothèque

- Scan automatique des fichiers musicaux
- Stockage des métadonnées (Artist, Album, Track, Cover)
- Téléchargement automatique des pochettes manquantes

## 2. Lecture multimédia

- Play, Pause, Skip
- Crossfade et transitions fluides
- File de lecture gérée en temps réel via WebSocket
- Gestion des playlists locales et dynamiques

## 3. Interface utilisateur

- Navigation par artiste / album avec vignettes
- TreeView animé pour explorer la bibliothèque
- Surbrillance des éléments actifs
- Recherche avancée avec filtres et facettes

## 4. Recommandation et IA

- Recommandations basées sur vecteurs et tags
- Éviter les morceaux récemment joués
- Suggestions dynamiques dans l’interface
- Chat IA pour créer des playlists hybrides

## 5. Intégration services externes

- Last.fm / ListenBrainz : récupération historique et métadonnées
- Napster : playlists et historique
- Soulseek : recherche et téléchargement de morceaux manquants

## 6. Optimisation et performance

- Indexation Whoosh pour recherche rapide
- Vectorisation pré-calculée pour recommandations
- Tâches asynchrones pour analyse et téléchargement

## 7. Extensibilité

- Architecture modulaire
- GraphQL généré automatiquement pour chaque modèle
- Possibilité d’ajouter des plugins pour de nouveaux services
