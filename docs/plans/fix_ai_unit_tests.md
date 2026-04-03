# Plan de correction des tests unitaires AI

## Problèmes identifiés
- Échec des tests d'initialisation des agents AI
- Échec des tests d'exécution des agents
- Échec des tests de décorateur d'outil AI
- Échec des tests d'exécuteur d'outil

## Causes probables
1. **Implémentation des agents AI**
   - Problèmes avec le builder d'agent
   - Problèmes avec les schémas de réponse
   - Problèmes avec l'initialisation des agents

2. **Décorateur d'outil AI**
   - Problèmes de validation des paramètres
   - Problèmes d'exécution des outils
   - Problèmes de gestion de session

3. **Exécuteur d'outil**
   - Problèmes de recherche des outils
   - Problèmes d'exécution synchrone et asynchrone
   - Problèmes de gestion des erreurs

4. **Validation des paramètres**
   - Problèmes avec les helpers de validation
   - Problèmes de tracking d'utilisation des outils
   - Problèmes d'intégration avec le registre d'outils

## Plan d'action
1. Corriger l'implémentation du builder d'agent dans `backend/ai/agents/builder.py`
2. Vérifier les schémas de réponse des agents
3. Corriger l'implémentation du décorateur d'outil AI dans `backend/ai/tools/decorator.py`
4. Améliorer la validation des paramètres des outils
5. Corriger l'implémentation de l'exécuteur d'outil dans `backend/ai/tools/executor.py`
6. Mettre à jour les tests pour refléter le comportement attendu
7. Vérifier l'intégration avec le registre d'outils
8. Améliorer la gestion des erreurs dans les outils AI
