# TODO - Correction du bug de streaming pydantic-ai

## Objectif
Corriger l'erreur `TypeError: 'async for' requires an object with __aiter__ method, got StreamedRunResult` dans `backend/ai/runtime.py`.

## Étapes

### 1. Analyse du problème ✅
- [x] Identifier que `Agent.run_stream()` retourne `StreamedRunResult` 
- [x] Comprendre que `StreamedRunResult` n'est pas directement itérable avec `async for`
- [x] Identifier la solution : utiliser `.stream_text()` ou `.stream()`

### 2. Correction du fichier runtime.py ✅
- [x] Modifier la méthode `_call_agent_stream` pour utiliser l'API pydantic-ai correcte
- [x] Adapter `_normalize_stream_event` pour gérer les événements de streaming correctement
- [ ] Tester la correction

### 3. Vérification
- [ ] Vérifier que le streaming fonctionne sans erreur
- [ ] S'assurer que les événements sont correctement normalisés

## Notes techniques

L'API pydantic-ai pour le streaming :
```python
# Mauvais (actuel)
async with fn(message, context=context) as stream:
    async for ev in stream:
        yield ev

# Correct
result = await fn(message, context=context)
async for text in result.stream_text():
    yield text
