# Plan de correction des tests de workflow du Player

## Problèmes identifiés
- Échec des tests de `TestPlayerWorkflow` (état initial, lecture, contrôles)
- Échec des tests de `TestPlayqueueManagement` (gestion de la file d'attente)
- Échec des tests de `TestPlayerWebSocketSync` (synchronisation WebSocket)

## Causes probables
1. **Communication WebSocket**
   - Problèmes de connexion WebSocket entre le frontend et l'API
   - Problèmes de format des messages WebSocket
   - Problèmes de gestion des événements WebSocket

2. **Gestion d'état du player**
   - État initial incorrect
   - Transitions d'état incorrectes
   - Problèmes de concurrence

3. **Synchronisation des événements**
   - Délais de synchronisation trop courts dans les tests
   - Problèmes de propagation des événements

## Plan d'action
1. Vérifier l'implémentation du gestionnaire WebSocket dans `backend/api/`
2. Examiner les logs WebSocket pendant l'exécution des tests
3. Vérifier la gestion d'état du player dans `backend/services/player_service.py`
4. Ajouter des délais appropriés dans les tests de synchronisation
5. Corriger les problèmes de gestion de la file d'attente dans `backend/services/playqueue_service.py`
6. Améliorer la robustesse des tests en ajoutant des assertions plus précises
