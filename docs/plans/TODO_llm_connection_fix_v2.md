# TODO - Correction connexion LLM persistante (COMPLET)

## Problème
La connexion entre l'API et KoboldCpp est interrompue pendant les requêtes longues, causant des erreurs "Exceeded maximum retries (3) for output validation".

## Solution implémentée
Créer un client HTTPX partagé (singleton) avec keep-alive activé entre LLMService et KoboldNativeModel.

## Fichiers créés/modifiés

### ✅ Nouveaux fichiers
- `backend/api/services/llm_http_client.py` - Client HTTPX singleton avec keep-alive
  - `get_llm_http_client()` - Récupère le client partagé
  - `close_llm_http_client()` - Ferme proprement le client
  - `reset_llm_http_client()` - Réinitialise le client en cas de problème
  - Configuration: keepalive_expiry=300s, max_connections=10, max_keepalive=5

- `backend/api/routers/simple_chat_api.py` - Endpoint de chat simple
  - `POST /api/simple-chat/` - Chat rapide sans validation stricte
  - `GET /api/simple-chat/health` - Health check
  - Utilise `build_simple_chat_agent()` pour des réponses instantanées

- `tests/test_llm_http_client.py` - Tests unitaires pour le client HTTPX
- `tests/test_simple_chat.py` - Tests pour l'endpoint de chat simple

### ✅ Fichiers modifiés
- `backend/api/services/llm_service.py`
  - Remplacé `self._client` par `get_llm_http_client()`
  - Supprimé la création de client local dans `__init__`

- `backend/ai/models/kobold_model.py`
  - Utilise `get_llm_http_client()` pour toutes les requêtes
  - Supprimé la création de client local dans `__init__`
  - `aclose()` ne ferme plus le client (partagé)

- `backend/ai/agents/builder.py`
  - Ajouté `build_simple_chat_agent()` pour chat sans validation stricte
  - Augmenté `retries=5` et `result_retries=5` pour tolérance

- `backend/api/__init__.py`
  - Ajouté l'import et l'inclusion de `simple_chat_router`

## Configuration keep-alive
```python
timeout = httpx.Timeout(
    connect=10.0,      # Connexion TCP
    read=None,         # Pas de limite (réponses LLM longues)
    write=30.0,        # Envoi payload
    pool=10.0,         # Attente connexion pool
)

limits = httpx.Limits(
    max_connections=10,
    max_keepalive_connections=5,
    keepalive_expiry=300.0,  # 5 minutes
)

headers = {
    "Connection": "keep-alive",
    "Keep-Alive": "timeout=300, max=1000",
}
```

## Tests
- ✅ `test_llm_http_client.py` - 4/4 tests passent
- ✅ `test_simple_chat.py` - Tests de l'endpoint chat

## Utilisation
```bash
# Test simple du chat
curl -X POST http://localhost:8001/api/simple-chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "coucou"}'

# Health check
curl http://localhost:8001/api/simple-chat/health
```

## Résultat attendu
- Connexion TCP persistante entre API et KoboldCpp
- Réduction des erreurs "connection was terminated"
- Chat rapide fonctionnel avec "coucou" → réponse instantanée
