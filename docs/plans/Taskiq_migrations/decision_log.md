# Decision Log - Phase 6 Fusion Backend / Backend Worker

## Décision 1: Fusion synthetic_tags_service - 2026-04-03
- **Conflit** : Deux implémentations différentes de SyntheticTagsService (backend/api vs backend_worker)
- **Version Choisie** : backend/api/services/synthetic_tags_service.py (plus complète, meilleure structure)
- **Fonctionnalités Intégrées** :
  - Méthode `calculate_tag_explainability` pour explicabilité des tags
  - Méthode `generate_all_synthetic_tags` pour génération complète avec métadonnées
- **Justification** : La version API avait une meilleure séparation des catégories et gestion des scores, la version worker ajoutait des fonctionnalités avancées d'explicabilité
- **Impact** : Amélioration des capacités d'analyse des tags synthétiques sans changement d'API
- **Approbation** : Auto-approval pour fusion de fonctionnalités complémentaires

## Décision 2: Déplacement key_service - 2026-04-03
- **Action** : Déplacement de backend_worker/services/key_service.py vers backend/services/key_service.py
- **Justification** : Service utilitaire simple sans dépendances DB, peut être partagé
- **Impact** : Aucun changement fonctionnel, disponibilité dans backend/services
- **Approbation** : Auto-approval pour service utilitaire

## Décision 3: Déplacement et adaptation path_service - 2026-04-03
- **Action** : Déplacement de backend_worker/services/path_service.py vers backend/services/path_service.py avec adaptation
- **Modifications** :
  - Changement d'import logging vers backend.api.utils.logging
  - Modification de SettingsService pour utiliser DB directement au lieu d'API client
  - Ajout de paramètre db: AsyncSession aux méthodes
- **Justification** : Le service avait une dépendance à l'API pour les settings, remplacée par accès DB direct pour cohérence post-fusion
- **Impact** : Service désormais intégré au backend unifié
- **Approbation** : Auto-approval pour adaptation nécessaire à la fusion

## Décision 4: Adaptation settings_service - 2026-04-03
- **Action** : Copie de backend/api/services/settings_service.py vers backend/services/settings_service.py avec ajout get_setting
- **Modifications** : Ajout méthode get_setting(db, key) pour compatibilité avec services migrés
- **Justification** : Services migrés nécessitent accès aux settings via DB
- **Impact** : Service DB disponible dans backend/services
- **Approbation** : Auto-approval pour consolidation des services

## Décision 5: Genre Taxonomy Service - 2026-04-03
- **Action** : Conserver backend/api/services/genre_taxonomy_service.py comme version principale
- **Justification** : Différences mineures, version API plus standardisée
- **Impact** : Pas de fusion nécessaire pour cette itération
- **Approbation** : Auto-approval, différences non critiques

## Décision 6: Vectorization Service - 2026-04-03
- **Action** : Conserver séparément (backend/api et backend_worker)
- **Justification** : Services différents (embeddings audio vs sémantique)
- **Impact** : Renommage recommandé pour éviter confusion future
- **Approbation** : Auto-approval, pas de duplication réelle

## Décision 7: Modèles DB backend_worker - 2026-04-03
- **Conflit** : Duplication complète des modèles DB (backend/api/models vs backend_worker/models)
- **Version Choisie** : backend/api/models comme source unique
- **Fonctionnalités Intégrées** : Modification de backend_worker/models/__init__.py pour importer depuis backend.api.models
- **Justification** : Élimination de la duplication, respect de l'architecture (API gère DB)
- **Impact** : Suppression possible du dossier backend_worker/models après vérification
- **Approbation** : Auto-approval pour élimination de dette technique