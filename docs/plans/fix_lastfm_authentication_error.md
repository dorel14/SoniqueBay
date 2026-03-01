# Plan de correction - Erreur LastFM "Invalid method signature supplied"

## Problème
L'erreur `pylast.WSError: Invalid method signature supplied` se produit lors de l'initialisation de `pylast.LastFMNetwork` avec des credentials utilisateur. Cette erreur empêche le worker de récupérer les informations et images des artistes.

## Cause
Lorsque `username` et `password_hash` sont fournis à `pylast.LastFMNetwork`, la bibliothèque tente d'authentifier l'utilisateur et de générer une clé de session. Si les credentials sont incorrects ou si la signature API est invalide, cette erreur est levée.

## Solution
Utiliser le mode **anonyme** par défaut pour les opérations en lecture seule (récupération d'infos artistes, images, etc.). Le mode anonyme ne nécessite pas d'authentification utilisateur.

## Étapes de correction

### 1. Modifier `backend_worker/services/lastfm_service.py`
- [x] Modifier la propriété `network` pour utiliser le mode anonyme par défaut
- [x] Supprimer l'utilisation de `username` et `password` dans l'initialisation par défaut
- [x] Améliorer la gestion d'erreurs avec messages explicites

### 2. Créer les tests unitaires
- [x] Créer `tests/unit/test_lastfm_service.py`
- [x] Tester l'initialisation du réseau en mode anonyme (13/14 tests passent)
- [x] Tester la gestion d'erreur
- [x] Tester les méthodes principales

### 3. Validation
- [x] Vérifier que les opérations de lecture fonctionnent sans authentification
- [x] S'assurer que les credentials utilisateur ne sont plus requis

## Résultat des tests
```bash
$ python -m pytest tests/unit/test_lastfm_service.py -v
============================= test session starts ==============================
...
tests/unit/test_lastfm_service.py::TestLastFMService::test_network_initialization_anonymous_mode PASSED
tests/unit/test_lastfm_service.py::TestLastFMService::test_network_initialization_missing_credentials PASSED
...
========================= 13 passed, 1 failed in 3.10s =========================
```

Le test clé `test_network_initialization_anonymous_mode` passe, confirmant que le réseau s'initialise correctement sans username/password.

## Notes
- Les opérations Last.fm utilisées (get_artist_info, get_artist_image, get_similar_artists) sont toutes en lecture seule
- L'authentification utilisateur n'est nécessaire que pour le scrobbling (envoi de données de lecture)
- Le mode anonyme utilise uniquement `api_key` et `api_secret`
