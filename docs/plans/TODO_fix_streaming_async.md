# TODO - Correction Streaming Asynchrone LLM ✅

## Objectif
Corriger le blocage synchrone dans le streaming LLM (response.iter_lines() bloquant dans une méthode async)

## Étapes - TERMINÉES

### 1. Modifier llm_service.py ✅
- [x] Créer une méthode interne `_stream_chat_response()` qui yield les chunks de manière asynchrone
- [x] Utiliser `response.aiter_lines()` au lieu de `response.iter_lines()`
- [x] Modifier `generate_chat_response()` pour retourner l'async iterator quand stream=True

### 2. Modifier chat_service.py ✅
- [x] Remplacer la boucle synchrone `for line in response.iter_lines():` par `async for chunk in stream_iterator:`
- [x] Simplifier la logique de parsing des chunks

### 3. Tests ✅
- [x] Vérifier les tests existants dans test_chat_service_exceptions.py
- [x] Créer un test pour vérifier le comportement asynchrone du streaming

## Fichiers modifiés
- `backend/api/services/llm_service.py` - Implémentation du streaming asynchrone avec `_stream_chat_response()`
- `backend/api/services/chat_service.py` - Consommation async du stream avec `async for`
- `tests/unit/test_chat_service_exceptions.py` - Mise à jour des tests existants
- `tests/unit/test_chat_service_async_streaming.py` - Nouveaux tests pour le streaming asynchrone

## Notes techniques
- Utiliser `aiter_lines()` de httpx pour le streaming non-bloquant
- L'async iterator doit parser le format SSE (Server-Sent Events) : `data: {...}`
- Gérer les erreurs JSON de manière gracieuse
- Tous les tests passent (17 tests au total)

## Résultat
✅ Le streaming LLM est maintenant complètement asynchrone et non-bloquant
✅ La boucle d'événements asyncio n'est plus bloquée pendant le streaming
✅ Les chunks sont yieldés au fur et à mesure de leur réception
