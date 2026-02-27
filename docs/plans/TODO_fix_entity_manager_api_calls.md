# TODO - Correction des erreurs d'appels API et doublons d'artistes

## Objectif
Corriger les erreurs d'appels API dans `entity_manager.py` et les violations de contrainte d'unicité lors de la création d'artistes.

## Bugs identifiés
1. URLs incorrectes pour les tags dans `entity_manager.py`
2. Mutation `createArtists` sans protection contre les doublons
3. `bulk_create_artists` ne vérifie pas l'existence des artistes avant insertion

## Fichiers à modifier
- [x] `backend_worker/services/entity_manager.py` - Corriger URLs et mutation artistes
- [ ] `backend/api/services/artist_service.py` - Ajouter `bulk_get_or_create_artists`
- [ ] `backend/api/graphql/queries/mutations/artist_mutations.py` - Utiliser la nouvelle méthode

## Tests
- [x] Créer tests unitaires pour valider les corrections

## Validation
- [ ] Tester l'insertion d'artistes existants (ex: "Van Halen")
- [ ] Vérifier les appels API aux endpoints de tags
