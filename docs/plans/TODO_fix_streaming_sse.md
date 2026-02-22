# TODO — Fix Streaming SSE Interruption (Broken Pipe)

## Contexte
Le streaming SSE de KoboldCpp est interrompu avec des erreurs "Broken pipe" et "Token streaming was interrupted or aborted". Le client ferme la connexion HTTP avant que le streaming soit terminé.

Endpoints KoboldCpp :
- API KoboldCpp : `http://localhost:5001/api`
- API OpenAI compatible : `http://localhost:5001/v1`

## Problèmes identifiés

1. **Timeout trop court** dans `_call_agent_stream_with_timeout` (30s) - insuffisant pour les réponses longues
2. **Gestion incorrecte de la fin du stream SSE** - le client ne détecte pas correctement `[DONE]`
3. **Pas de keep-alive** sur la connexion HTTP avec KoboldCpp
4. **Buffering qui peut causer des blocages** dans la boucle d'événements

## Étapes de correction

### 1. `backend/api/services/llm_service.py`
- [x] Augmenter le timeout pour le streaming (60s → 120s)
- [x] Améliorer la détection de la fin du stream SSE (`[DONE]`)
- [x] Ajouter des logs de debug pour le streaming
- [x] Gérer proprement la fermeture de la connexion avec gestion des commentaires SSE
- [ ] Ajouter un heartbeat pour maintenir la connexion vivante (optionnel)

### 2. `backend/ai/runtime.py`
- [x] Augmenter le timeout global du streaming (30s → 90s)
- [x] Améliorer la gestion des chunks vides et de la fin du stream
- [x] Ajouter des logs détaillés pour le streaming
- [x] Gérer proprement les erreurs de connexion interrompue

### 3. `backend/api/routers/ws_ai.py`
- [ ] Ajouter une gestion de déconnexion plus robuste côté WebSocket
- [ ] S'assurer que le client WebSocket ne ferme pas la connexion prématurément
- [ ] Ajouter des logs pour tracer la fermeture des connexions

### 4. Tests
- [ ] Créer un test unitaire pour le streaming SSE
- [ ] Vérifier la gestion de la fin du stream

## Statut
- [x] Corrections principales appliquées - En attente de validation
