# Plan de correction des tests d'API Recommandations et Recherche Vectorielle

## Problèmes identifiés
- Échec des tests d'API pour les recommandations hybrides
- Échec des tests d'API pour la recherche vectorielle
- Problèmes avec les filtres (BPM, clé, genre, style)
- Problèmes de pagination et de scoring

## Causes probables
1. **Extension pgvector**
   - Vérifier l'installation et la configuration de pgvector
   - Vérifier les migrations liées aux colonnes vectorielles (`add_pgvector_cols.py`)
   - Vérifier les index HNSW pour les recherches vectorielles

2. **Algorithmes de recommandation**
   - Problèmes d'implémentation des filtres (BPM, clé, genre)
   - Problèmes de combinaison des sources de recommandation
   - Problèmes de fallback SQL

3. **Calcul des scores**
   - Problèmes de normalisation des scores
   - Problèmes de pondération des différentes sources
   - Problèmes de tri des résultats

## Plan d'action
1. Vérifier la configuration de pgvector dans le conteneur PostgreSQL
2. Examiner l'implémentation du service de recommandation dans `backend/services/recommendation_service.py`
3. Vérifier l'implémentation des filtres dans `backend/services/filter_service.py`
4. Corriger les problèmes de pagination dans les requêtes SQL
5. Optimiser les requêtes vectorielles avec des index HNSW appropriés
6. Mettre à jour les tests pour refléter le comportement attendu
7. Vérifier la gestion des erreurs en cas d'absence de vecteurs
