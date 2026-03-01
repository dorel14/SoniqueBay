# Plan de correction des tests kobold_model

## Problèmes identifiés

1. **test_system_prompt_formatting** et **test_user_prompt_formatting**: Les tests vérifient la présence de `ö` mais la sortie réelle contient `</s>`. C'est une typo dans les tests.

2. **test_request_success**, **test_request_connect_error_raises**, **test_request_invalid_response_format_raises**: Les tests essaient de patcher `self.model._client`, mais `KoboldNativeModel` n'a plus cet attribut. Il utilise maintenant `get_llm_http_client()` pour obtenir un client partagé.

## Fichier à modifier

- `tests/unit/test_kobold_model.py`

## Étapes de correction

- [x] Fix test_system_prompt_formatting: changer `assert "ö" in result` en `assert "</s>" in result`
- [x] Fix test_user_prompt_formatting: changer `assert "ö" in result` en `assert "</s>" in result`
- [x] Fix test_request_success: patcher `backend.ai.models.kobold_model.get_llm_http_client` au lieu de `self.model._client`
- [x] Fix test_request_connect_error_raises: même approche de patching
- [x] Fix test_request_invalid_response_format_raises: même approche de patching
- [x] Exécuter les tests pour vérifier

## Résultat

✅ **Tous les 33 tests passent avec succès !**

## Notes techniques

Le client HTTP est maintenant géré par `llm_http_client.py` (singleton partagé). Pour les tests, il faut:
1. Patcher `backend.ai.models.kobold_model.get_llm_http_client`
2. Retourner un mock client avec une méthode `post` (AsyncMock)
3. Configurer le mock pour retourner la réponse souhaitée ou lever l'exception attendue
