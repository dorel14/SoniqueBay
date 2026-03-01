# Plan de correction - Problème de création d'albums manquants

## Date

2025-01-XX

## Problème identifié

Après un scan complet de la bibliothèque musicale, les albums ne sont pas créés dans la base de données bien que les artistes et les tracks le soient.

## Causes racines identifiées

### 1. Incohérence des clés d'album

La clé d'album était créée différemment entre :

- `entity_manager.py` : utilisait `albumArtistId` (camelCase de la réponse GraphQL)
- `insert_batch_worker.py` : utilisait `album_artist_id` (snake_case)

### 2. Manque de validation de `album_artist_id`

Les albums sans `album_artist_id` valide étaient silencieusement ignorés sans logs explicites.

### 3. Recherche d'artiste insuffisante

La recherche d'artiste dans `artist_map` ne gérait pas correctement la casse des noms.

### 4. Manque de logs de diagnostic

Absence de logs détaillés pour tracer le flux de création des albums.

## Fichiers modifiés

### 1. `backend_worker/services/entity_manager.py`

- ✅ Ajout de validation stricte pour `title` et `album_artist_id`
- ✅ Logs de diagnostic détaillés pour chaque étape
- ✅ Standardisation des clés d'album (utilisation cohérente de tuples)
- ✅ Gestion des erreurs GraphQL améliorée
- ✅ Cohérence entre la création des clés dans `album_map` et `final_album_map`

### 2. `backend_worker/workers/insert/insert_batch_worker.py`

- ✅ Amélioration de `resolve_album_for_track()` avec :
  - Logs de diagnostic détaillés
  - Recherche insensible à la casse des artistes
  - Recherche alternative par titre seul si la clé complète échoue
- ✅ Amélioration du traitement des albums avec :
  - Logs des albums avant résolution
  - Gestion explicite des albums sans artiste
  - Comptage des albums ignorés
  - Vérification des discrepances (attendus vs retournés)
- ✅ Amélioration de la résolution des tracks avec :
  - Statistiques de résolution d'albums
  - Logs par track du résultat de résolution

### 3. `backend_worker/celery_tasks.py`

- ✅ Ajout de logs de diagnostic pour les albums détectés dans `batch_entities()`

## Tests recommandés

1. **Test de scan complet** :

   ```bash
   # Lancer un scan et observer les logs
   docker-compose logs -f celery-worker | grep -E "(ALBUM|RESOLVE_ALBUM|INSERT)"
   ```

2. **Vérification des logs** :
   - Rechercher les messages `[ALBUM] ✅` pour confirmer la création
   - Rechercher les messages `[ALBUM] ❌` pour identifier les échecs
   - Vérifier les statistiques `[INSERT] Statistiques album resolution`

3. **Vérification en base** :

   ```sql
   -- Vérifier que les albums sont créés
   SELECT COUNT(*) FROM albums;
   
   -- Vérifier l'association tracks-albums
   SELECT COUNT(*) FROM tracks WHERE album_id IS NOT NULL;
   ```

## Notes de mise en œuvre

- Les modifications sont rétrocompatibles
- Les nouveaux logs utilisent le niveau DEBUG pour les détails et INFO pour les résumés
- La gestion d'erreurs ne bloque plus le pipeline en cas d'échec partiel
- Les albums sans artiste valide sont maintenant explicitement ignorés avec log

## TODO futurs

- [ ] Ajouter des tests unitaires pour `create_or_get_albums_batch()`
- [ ] Ajouter des tests d'intégration pour le pipeline complet
- [ ] Optimiser la création d'artiste "à la volée" pour les albums
- [ ] Considérer l'ajout d'une file d'attente pour les albums en échec
