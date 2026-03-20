# Plan de correction des tests de workflow de chat

## Problèmes identifiés
- Échec de tous les tests de `TestChatWorkflow`
- Erreurs dans tous les tests de `TestConversationPersistence`
- Erreurs dans tous les tests d'intégration chat-bibliothèque

## Causes probables
1. **Connexion au service LLM (KoboldCpp)**
   - Vérifier que le service est accessible depuis les conteneurs de test
   - Vérifier les paramètres de connexion (URL, timeout)
   - Vérifier que les modèles sont correctement chargés

2. **Persistance des conversations**
   - Vérifier le schéma de base de données pour les conversations
   - Vérifier les migrations Alembic liées aux conversations
   - Vérifier les requêtes SQL pour la sauvegarde/récupération des conversations

3. **Intégration chat-bibliothèque**
   - Vérifier les appels API entre le service de chat et la bibliothèque
   - Vérifier les permissions d'accès aux données

## Plan d'action
1. Créer un test unitaire simple pour vérifier la connexion au service LLM
2. Vérifier les logs du service LLM pendant l'exécution des tests
3. Examiner les requêtes SQL générées lors des tests de persistance
4. Mettre à jour les mocks pour les tests d'intégration
5. Corriger les problèmes d'initialisation du chat dans `backend/ai/orchestrator.py`
