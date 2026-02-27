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
- [ ] Tester la connexion persistante

## Fichiers modifiés
- `backend/api/services/llm_http_client.py` (nouveau)
- `backend/api/services/llm_service.py`
- `backend/ai/models/kobold_model.py`
