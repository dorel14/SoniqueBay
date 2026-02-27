# TODO - Correction connexion LLM persistante

## Problème
La connexion entre l'API et KoboldCpp est interrompue pendant les requêtes longues, causant des erreurs "Exceeded maximum retries (3) for output validation".

## Solution
Créer un client HTTPX partagé (singleton) avec keep-alive activé entre LLMService et KoboldNativeModel.

## Étapes

- [x] Analyser les fichiers concernés
- [x] Créer `backend/api/services/llm_http_client.py` - Client HTTPX partagé
- [x] Modifier `backend/api/services/llm_service.py` - Utiliser client partagé
- [x] Modifier `backend/ai/models/kobold_model.py` - Utiliser client partagé
- [x] Tester la connexion persistante (4 tests passent)

## Fichiers modifiés
- `backend/api/services/llm_http_client.py` (nouveau)
- `backend/api/services/llm_service.py`
- `backend/ai/models/kobold_model.py`
- `tests/test_llm_http_client.py` (nouveau)

## Configuration keep-alive
- `keepalive_expiry=300s` (5 minutes)
- `max_connections=10`, `max_keepalive_connections=5`
- Timeouts: connect=10s, read=None, write=30s, pool=10s
- Headers: `Connection: keep-alive`, `Keep-Alive: timeout=300, max=1000`

## Tests
```powershell
python -m pytest tests/test_llm_http_client.py -v
# 4 passed
