# TODO — Fix LLM Connection Error (ConnectError)

## Contexte
Erreur `httpx.ConnectError: All connection attempts failed` lors des appels au LLM depuis `api-service`.
Cause racine : `KOBOLDCPP_BASE_URL=http://localhost:11434` pointe vers le container lui-même au lieu du service `llm-service`.

## Étapes

- [x] **1. `docker-compose.yml`**
  - [x] Corriger `KOBOLDCPP_BASE_URL` : `http://localhost:11434` → `http://llm-service:5001`
  - [x] Ajouter `llm-service` dans `depends_on` de `api-service` (`condition: service_started`)
  - [x] Ajouter section `networks` explicite à `llm-service`
  - [x] Ajouter un healthcheck pour `llm-service` (curl `/api/v1/info`, start_period: 120s)

- [x] **2. `backend/api/services/llm_service.py`**
  - [x] Corriger le fallback par défaut `KOBOLDCPP_BASE_URL` → `http://llm-service:5001`
  - [x] Améliorer le message d'erreur de connexion (mentionner le nom du service)
  - [x] Ajouter un log d'avertissement clair si la connexion échoue au démarrage

- [ ] **3. Validation**
  - [ ] Rebuild du container `api-service`
  - [ ] Vérifier les logs de connexion LLM

## Statut
- [x] Corrections appliquées — en attente de validation
