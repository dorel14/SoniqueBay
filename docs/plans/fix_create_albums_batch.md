# Plan de correction : Méthode create_albums_batch manquante

## Problème
L'erreur `AttributeError: 'AlbumService' object has no attribute 'create_albums_batch'` se produit lors des appels GraphQL et REST API pour créer des albums en batch.

## Fichier concerné
- `backend/api/services/album_service.py` - Ajout de la méthode manquante

## Étapes de correction

- [x] Analyser le code existant et comprendre les dépendances
- [x] Créer la méthode `create_albums_batch` dans AlbumService
- [x] Importer `AlbumCreate` depuis le schéma Pydantic
- [x] Implémenter la logique get_or_create pour éviter les doublons
- [x] Retourner les données au format dict pour compatibilité GraphQL
- [x] Ajouter la gestion des logs et erreurs
- [x] Tester la correction (5 tests unitaires passés)

## Détails d'implémentation

La méthode doit :
1. Accepter `List[AlbumCreate]` (objets Pydantic)
2. Pour chaque album, appeler `get_or_create_album` avec :
   - title
   - album_artist_id
   - release_year
   - musicbrainz_albumid (si disponible)
3. Retourner une liste de dictionnaires avec les champs :
   - id, title, album_artist_id, release_year, musicbrainz_albumid
