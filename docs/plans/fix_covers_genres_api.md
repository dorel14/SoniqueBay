# Plan de correction des tests d'API Covers et Genres

## Problèmes identifiés
- Échec des tests d'API pour les covers et les genres
- Problèmes avec la gestion des images de couverture
- Problèmes avec la gestion des genres

## Causes probables
1. **Stockage et récupération des covers**
   - Problèmes de chemin de fichiers pour les covers
   - Problèmes de permissions sur les fichiers
   - Problèmes de format d'image

2. **Validation des types de covers**
   - Problèmes avec l'énumération `EntityCoverType`
   - Problèmes de validation des données d'entrée

3. **Endpoints de genres**
   - Problèmes d'implémentation des endpoints CRUD
   - Problèmes de validation des données de genre

## Plan d'action
1. Vérifier l'implémentation du service de covers dans `backend/services/cover_service.py`
2. Examiner la gestion des fichiers d'image dans le système de fichiers
3. Vérifier les migrations liées à `EntityCoverType` (notamment `fix_entitycovertype_enum.py`)
4. Corriger l'implémentation des endpoints de genres dans `backend/api/`
5. Mettre à jour les tests pour refléter le comportement attendu
6. Vérifier les chemins de stockage des covers dans les paramètres de configuration
