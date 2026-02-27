# TODO: Ajouter des logs pour diagnostiquer les appels API incorrects

## Objectif
Ajouter des logs détaillés dans `backend_worker/workers/metadata/enrichment_worker.py` pour identifier quand le worker fait des appels API à `/api/artists/search` avec des genres comme "90s" ou "usa".

## Tâches

- [x] Lire le fichier `backend_worker/workers/metadata/enrichment_worker.py` pour identifier l'emplacement exact
- [x] Ajouter des logs informatifs avant chaque appel API de recherche d'artiste
- [x] Ajouter des logs pour indiquer la raison de l'appel (genre suspect détecté)
- [x] Ajouter des logs après l'appel API pour indiquer le résultat
- [ ] Tester et vérifier que les logs apparaissent correctement

## Fichier concerné
- `backend_worker/workers/metadata/enrichment_worker.py`

## Notes
- L'appel API se fait dans la fonction `_clean_single_genre` via `check_artist_in_api_cached()`
- Les genres "90s" et "usa" sont actuellement traités comme des noms d'artistes potentiels
- Les logs doivent être informatifs mais pas trop verbeux
