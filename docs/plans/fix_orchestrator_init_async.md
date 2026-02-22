# Fix : Orchestrator init async + WebSocket disconnect

## Problème
- `TypeError: argument of type 'coroutine' is not iterable`
- `orchestrator.py` `__init__` appelle `load_enabled_agents()` sans `await`
- La méthode `init()` n'existe pas dans `Orchestrator` alors que `ws_ai.py` l'appelle

## TODO

- [x] Analyser `backend/ai/orchestrator.py`
- [x] Analyser `backend/ai/loader.py`
- [x] Analyser `backend/api/routers/ws_ai.py`
- [x] Corriger `backend/ai/orchestrator.py` : retirer l'appel async de `__init__`, ajouter `async def init()`
- [x] Corriger `backend/api/routers/ws_ai.py` : ajouter gestion `WebSocketDisconnect`
- [x] Tests unitaires créés : `tests/unit/ai/test_orchestrator.py` (20 tests, tous PASSED)
- [ ] Vérifier les logs après redémarrage du container

## Détail des corrections

### orchestrator.py
- `self.agents = {}` dans `__init__` (plus de coroutine non-awaitée)
- Nouvelle méthode `async def init(self)` qui await `load_enabled_agents()` et valide `"orchestrator"`

### ws_ai.py
- Import `WebSocketDisconnect`
- Try/except autour de la boucle `while True`
- Gestion `RuntimeError` (agent manquant) avec message d'erreur au client + close(1011)
- Gestion exception inattendue avec close propre

## Résultats des tests
```
20 passed in 2.39s
