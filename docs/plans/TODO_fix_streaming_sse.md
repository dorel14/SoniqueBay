# TODO — Fix Streaming SSE Interruption (Broken Pipe)

## Contexte
Le streaming SSE de KoboldCpp est interrompu avec des erreurs "Broken pipe" et "Token streaming was interrupted or aborted". Le client ferme la connexion HTTP avant que le streaming soit terminé.

Endpoints KoboldCpp :
- API KoboldCpp : `http://localhost:5001/api`
- API OpenAI compatible : `http://localhost:5001/v1`

## Corrections appliquées

### 1. `backend/api/services/llm_service.py` ✅
- [x] Augmenter le timeout pour le streaming (60s → 120s)
- [x] Améliorer la détection de la fin du stream SSE (`[DONE]`)
- [x] Ajouter des logs de debug pour le streaming
- [x] Gérer les commentaires SSE (lignes commençant par `:`)
- [x] Améliorer la gestion des erreurs de connexion

### 2. `backend/ai/runtime.py` ✅
- [x] Augmenter le timeout global du streaming (30s → 90s)
- [x] Augmenter le silence max (2.0s → 5.0s) pour les modèles lents
- [x] Ajouter des logs de debug pour le streaming
- [x] Améliorer la gestion des erreurs avec `exc_info=True`

### 3. `backend/ai/orchestrator.py` ✅
- [x] Corriger la gestion du résultat `AgentRunResult` (pydantic-ai)
- [x] Ajouter le parsing JSON pour les outputs string
- [x] Améliorer les fallbacks pour la détection d'intention
- [x] Augmenter le timeout de détection d'intention (10s → 30s)

### 4. Tests
- [x] Test de connexion WebSocket réussi
- [ ] Test de streaming complet (en attente de validation)

## Problèmes résolus

1. **Timeout trop court** : Augmenté de 30s à 90s pour le streaming et 30s pour la détection d'intention
2. **Gestion incorrecte de `AgentRunResult`** : Le résultat de `orch.run()` est maintenant correctement traité comme un objet pydantic-ai avec attribut `.output`
3. **Détection SSE `[DONE]`** : Améliorée avec `.strip()` pour gérer les espaces
4. **Commentaires SSE** : Les lignes commençant par `:` sont maintenant ignorées

## Validation

Pour tester les corrections :
```bash
# Test WebSocket
python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8001/api/ws/chat') as ws:
        await ws.send('Bonjour')
        async for msg in ws:
            print(json.loads(msg))
asyncio.run(test())
"
```

## Statut
- [x] Corrections appliquées
- [x] Tests de connexion réussis
- [ ] Validation complète du streaming (en cours)
