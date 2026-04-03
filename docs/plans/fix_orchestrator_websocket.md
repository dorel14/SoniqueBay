# Plan de correction des tests d'orchestrateur et WebSocket AI

## Problèmes identifiés
- Échec des tests WebSocket AI
- Problèmes avec l'endpoint WebSocket AI
- Problèmes de gestion des connexions WebSocket
- Problèmes de streaming des réponses

## Causes probables
1. **Implémentation de l'orchestrateur AI**
   - Problèmes d'initialisation asynchrone
   - Problèmes de chargement des agents
   - Problèmes de gestion du cache runtime

2. **Endpoint WebSocket AI**
   - Problèmes d'acceptation des connexions
   - Problèmes de gestion des déconnexions
   - Problèmes de traitement des messages

3. **Gestion des erreurs**
   - Problèmes de gestion des erreurs d'initialisation
   - Problèmes de gestion des exceptions inattendues
   - Problèmes de communication des erreurs au client

4. **Streaming des réponses**
   - Problèmes d'envoi des chunks de réponse
   - Problèmes de formatage des messages de streaming
   - Problèmes de timing dans les tests asynchrones

## Plan d'action
1. Corriger l'implémentation de l'orchestrateur dans `backend/ai/orchestrator.py`
2. Vérifier l'implémentation de l'endpoint WebSocket dans `backend/api/websockets/ai_endpoint.py`
3. Améliorer la gestion des erreurs dans l'orchestrateur et l'endpoint
4. Corriger les problèmes de streaming des réponses
5. Mettre à jour les tests pour utiliser des fixtures WebSocket plus robustes
6. Ajouter des délais appropriés dans les tests asynchrones
7. Vérifier la gestion des connexions multiples
8. Améliorer la documentation de l'orchestrateur et de l'endpoint WebSocket
