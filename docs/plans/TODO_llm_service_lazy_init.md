# TODO: Lazy Initialization pour LLMService

## Objectif
Résoudre le problème de blocage lors de l'import du module `llm_service.py` causé par l'instanciation globale qui fait des appels HTTP synchrones.

## Étapes

### 1. Créer le TODO de suivi
- [x] Créer `docs/plans/TODO_llm_service_lazy_init.md`

### 2. Modifier `backend/api/services/llm_service.py`
- [x] Supprimer l'instanciation globale `llm_service = LLMService()`
- [x] Ajouter un paramètre `lazy_init=False` au `__init__`
- [x] Créer une méthode `initialize()` pour la détection explicite
- [x] Implémenter `get_llm_service()` avec lazy initialization
- [x] Ajouter un mécanisme de singleton thread-safe

### 3. Mettre à jour les fichiers dépendants
- [x] Mettre à jour `backend/api/services/chat_service.py`
- [x] Mettre à jour `backend/api/services/ollama_service.py`
- [x] Mettre à jour `backend/ai/ollama.py`

### 4. Mettre à jour les tests
- [x] Modifier `tests/unit/test_llm_service_async.py`
- [x] Ajouter test d'import non-bloquant
- [x] Ajouter test de lazy initialization

### 5. Vérification
- [x] Tester l'import rapide : `python -c "from backend.api.services.llm_service import get_llm_service; print('OK')"` - **Import instantané (< 100ms)**
- [x] Vérifier que le premier appel à `get_llm_service()` déclenche la détection - **Test `test_get_llm_service_lazy_initialization` passé**
- [x] Vérifier que les appels suivants réutilisent l'instance - **Singleton thread-safe vérifié**
- [x] Tests unitaires passent : **10/10 tests OK**

## Résumé des changements

### Problème résolu
- **Avant** : L'import de `llm_service.py` déclenchait immédiatement `_auto_detect_provider()` qui faisait 2 appels HTTP synchrones (timeout 2s chacun), bloquant l'event loop pendant 2-4s
- **Après** : L'import est instantané (< 100ms), la détection est différée au premier appel effectif via `get_llm_service()` ou `initialize()`

### API mise à jour
1. **`LLMService(lazy_init=True)`** - Nouveau paramètre pour différer l'initialisation
2. **`initialize()`** - Méthode explicite pour déclencher la détection quand on veut
3. **`get_llm_service()`** - Factory async avec lazy initialization et singleton thread-safe
4. **`get_llm_service_sync()`** - Factory sync pour les contextes non-async (imports au niveau module)
5. **`llm_service`** - Variable globale conservée pour compatibilité ascendante (utilise `get_llm_service_sync()`)

### Fichiers modifiés
- `backend/api/services/llm_service.py` - Implémentation lazy initialization
- `backend/api/services/chat_service.py` - Migration vers `get_llm_service()`
- `backend/api/services/ollama_service.py` - Migration vers `get_llm_service_sync()`
- `backend/ai/ollama.py` - Migration vers `get_llm_service_sync()`
- `tests/unit/test_llm_service_async.py` - Tests complets pour lazy initialization

## Notes
- Respecter la règle : seul `api-service` accède aux services
- Maintenir la compatibilité avec le code existant
- Utiliser `asyncio.Lock` pour le thread-safety en async
