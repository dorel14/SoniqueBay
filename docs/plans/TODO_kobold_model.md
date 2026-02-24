# TODO — KoboldNativeModel : Modèle PydanticAI natif pour KoboldCPP

## Contexte
Création d'une classe `KoboldNativeModel` compatible avec pydantic-ai 1.x qui utilise
l'API native KoboldCPP (`/api/v1/generate` + `/api/extra/generate/stream`) au lieu de
l'API OpenAI-compatible, pour éviter les problèmes de compatibilité.

## Étapes

- [x] **1. `backend/ai/models/__init__.py`** *(nouveau)*
  - [x] Créer le module `models` avec export de `KoboldNativeModel`

- [x] **2. `backend/ai/models/kobold_model.py`** *(nouveau — implémentation principale)*
  - [x] Implémenter `KoboldStreamedResponse(StreamedResponse)` avec `__aiter__` SSE natif
  - [x] Implémenter `KoboldNativeModel(Model)` avec `request()` et `request_stream()`
  - [x] Implémenter `_format_messages()` en format ChatML
  - [x] Implémenter `_build_payload()` avec paramètres natifs KoboldCPP
  - [x] Corriger toutes les erreurs de syntaxe du draft utilisateur

- [x] **3. `backend/ai/ollama.py`** *(modification)*
  - [x] Ajouter `get_kobold_model()` retournant `KoboldNativeModel`
  - [x] Modifier `get_ollama_model()` pour router vers `KoboldNativeModel` si provider=koboldcpp

- [x] **4. `tests/unit/test_kobold_model.py`** *(nouveau)*
  - [x] Test `request()` avec mock httpx
  - [x] Test `request_stream()` avec mock SSE
  - [x] Test `_format_messages()` format ChatML
  - [x] Test `_build_payload()` paramètres

## Statut
- [x] Implémentation terminée — en attente de validation par les tests
