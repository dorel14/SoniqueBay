# TODO - Correction erreur pydantic_ai "Exceeded maximum retries (1) for output validation"

## Description du problème
L'erreur `pydantic_ai.exceptions.UnexpectedModelBehavior: Exceeded maximum retries (1) for output validation` se produit lorsque le modèle LLM (KoboldCPP) génère une sortie qui ne correspond pas au schéma attendu. La valeur par défaut de `max_result_retries` est 1, ce qui est insuffisant.

## Plan de correction

### ✅ Étape 1 : Modifier `backend/ai/agents/builder.py`
- [x] Ajouter `max_result_retries=3` dans la fonction `build_agent()`
- [x] Ajouter `max_result_retries=3` dans la fonction `build_agent_with_inheritance()`
- [x] Ajouter des commentaires explicatifs

### ✅ Étape 2 : Tests et validation
- [x] Créer des tests unitaires dans `tests/test_agent_retries.py`
- [x] Exécuter les tests - 5 tests passent avec succès
- [x] Vérifier que `max_result_retries=3` est présent dans le code source
- [x] Valider que la valeur (3) est dans la plage recommandée [2, 5]

### ✅ Étape 3 : Documentation
- [x] Créer le fichier TODO de suivi
- [x] Documenter la correction et les tests effectués

## Notes techniques
- La valeur de 3 retries est un compromis entre robustesse et latence
- Chaque retry ajoute du temps de traitement, mais réduit les erreurs
- Pour des modèles locaux comme KoboldCPP, 3 retries est généralement suffisant
- Si le problème persiste, envisager d'augmenter à 5 ou d'améliorer les prompts système

## Fichiers modifiés
- `backend/ai/agents/builder.py` : Ajout du paramètre `max_result_retries=3` aux constructeurs Agent
