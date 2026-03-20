# Plan de correction des tests d'API WebSocket Player

## Problèmes identifiés
- Échec des tests de connexion WebSocket
- Échec des tests de contrôle du player via WebSocket
- Échec des tests de synchronisation d'état
- Échec des tests de gestion d'erreurs

## Causes probables
1. **Implémentation du gestionnaire WebSocket**
   - Problèmes d'initialisation des connexions WebSocket
   - Problèmes de gestion des déconnexions
   - Problèmes de concurrence avec plusieurs connexions

2. **Format des messages**
   - Problèmes de validation des schémas de messages
   - Problèmes de sérialisation/désérialisation JSON
   - Problèmes de structure des messages d'événement et de réponse

3. **Gestion des événements asynchrones**
   - Problèmes de propagation des événements entre les clients
   - Problèmes de timing dans les tests asynchrones
   - Problèmes de gestion des erreurs asynchrones

## Plan d'action
1. Examiner l'implémentation du gestionnaire WebSocket dans `backend/api/websockets/`
2. Vérifier la documentation sur la refactorisation WebSocket (`docs/websocket_refactor.md`)
3. Corriger les problèmes de validation des messages
4. Améliorer la gestion des erreurs dans le gestionnaire WebSocket
5. Ajouter des délais appropriés dans les tests asynchrones
6. Mettre à jour les tests pour utiliser des fixtures WebSocket plus robustes
7. Vérifier la gestion des événements de player dans le service WebSocket
