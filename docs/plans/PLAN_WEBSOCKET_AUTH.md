"""Plan d'authentification pour les endpoints WebSocket SoniqueBay.

Ce document décrit la stratégie pour sécuriser les connexions WebSocket
avec une authentification par token, en s'appuyant sur Supabase Auth.

Auteur: SoniqueBay Team
Version: 1.0.0
Date: 2026-03-03
"""

# Plan : Authentification WebSocket — SoniqueBay

**Statut** : 📋 Planifié  
**Priorité** : Haute (sécurité)  
**Branche cible** : `blackboxai/feature/websocket-auth`  
**Dépendances** : Phase 8 migration Supabase (Auth activé)

---

## Contexte

Le reviewer de la PR #38 a identifié que l'endpoint WebSocket `/ws/chat`
(`backend/api/routers/ws_ai.py`) accepte toute connexion sans vérification
d'identité. Cela expose le service IA (orchestrateur + LLM KoboldCpp) à :

- Consommation non contrôlée de ressources LLM (CPU/mémoire sur RPi4)
- Accès non autorisé à l'historique de conversation
- Injection de prompts arbitraires vers l'orchestrateur

---

## Endpoints WebSocket concernés

| Endpoint | Fichier | Risque | Priorité |
|----------|---------|--------|----------|
| `/ws/chat` | `backend/api/routers/ws_ai.py` | Critique | Haute |
| `/ws/ai` (si existant) | `backend/api/routers/ws_ai.py` | Critique | Haute |
| `/api/realtime/*` | `backend/api/routers/realtime_router.py` | Moyen | Moyenne |
| `/api/sse/*` | `backend/api/routers/sse_api.py` | Moyen | Moyenne |

---

## Architecture Cible

```
Client (NiceGUI)
    │
    │  ws://api:8001/ws/chat?token=<JWT>
    ▼
FastAPI WebSocket Handler
    │
    ├─ 1. Extraire token (query param ou header)
    ├─ 2. Vérifier token (Supabase JWT ou token interne)
    ├─ 3. Si invalide → ws.close(code=1008) AVANT ws.accept()
    └─ 4. Si valide → ws.accept() + traitement normal
```

---

## Phase 1 : Token Interne Simple (Court terme)

### Approche
Utiliser un token partagé simple (API key) stocké dans les variables
d'environnement, sans dépendance à Supabase Auth.

### Implémentation

**Nouveau fichier** : `backend/api/utils/ws_auth.py`

```python
"""
Authentification pour les endpoints WebSocket.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import os
from fastapi import WebSocket
from backend.api.utils.logging import logger


async def verify_ws_token(ws: WebSocket) -> bool:
    """
    Vérifie le token d'authentification WebSocket.

    Le token est attendu dans le query parameter 'token'.
    Exemple : ws://localhost:8001/ws/chat?token=<WS_API_KEY>

    Args:
        ws: Instance WebSocket FastAPI

    Returns:
        True si le token est valide, False sinon.
    """
    expected_token = os.getenv("WS_API_KEY")

    if not expected_token:
        # TODO: En production, lever une erreur si WS_API_KEY non définie
        # Pour l'instant, log un avertissement et autoriser (mode développement)
        logger.warning(
            "WS_API_KEY non définie — authentification WebSocket désactivée "
            "(mode développement uniquement)"
        )
        return True

    token = ws.query_params.get("token")
    if not token:
        logger.warning(
            f"WebSocket {ws.url.path} : connexion refusée — token manquant "
            f"(client: {ws.client.host})"
        )
        return False

    if token != expected_token:
        logger.warning(
            f"WebSocket {ws.url.path} : connexion refusée — token invalide "
            f"(client: {ws.client.host})"
        )
        return False

    logger.debug(f"WebSocket {ws.url.path} : token valide (client: {ws.client.host})")
    return True
```

**Modification** : `backend/api/routers/ws_ai.py`

```python
from backend.api.utils.ws_auth import verify_ws_token

@router.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    # Vérification AVANT ws.accept()
    if not await verify_ws_token(ws):
        await ws.close(code=1008)  # 1008 = Policy Violation
        return

    await ws.accept()
    # ... reste du code inchangé
```

**Variable d'environnement** à ajouter dans `.env` et `docker-compose.yml` :
```bash
WS_API_KEY=<token-aleatoire-securise>
```

---

## Phase 2 : Authentification Supabase JWT (Long terme)

### Prérequis
- Phase 8 migration Supabase complétée (Auth activé)
- `SUPABASE_JWT_SECRET` configuré
- Utilisateurs créés dans Supabase Auth

### Approche
Vérifier le JWT Supabase transmis en query parameter ou header.

**Nouveau fichier** : `backend/api/utils/supabase_ws_auth.py`

```python
"""
Authentification WebSocket via Supabase JWT.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import os
from typing import Optional, Dict, Any
import jwt
from fastapi import WebSocket
from backend.api.utils.logging import logger


async def verify_supabase_jwt(ws: WebSocket) -> Optional[Dict[str, Any]]:
    """
    Vérifie un JWT Supabase transmis en query parameter.

    Args:
        ws: Instance WebSocket FastAPI

    Returns:
        Payload JWT décodé si valide, None sinon.
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError("SUPABASE_JWT_SECRET must be set for WebSocket auth")

    token = ws.query_params.get("token")
    if not token:
        logger.warning(
            f"WebSocket {ws.url.path} : token JWT manquant "
            f"(client: {ws.client.host})"
        )
        return None

    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        logger.debug(
            f"WebSocket {ws.url.path} : JWT valide "
            f"(user: {payload.get('sub')}, client: {ws.client.host})"
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning(
            f"WebSocket {ws.url.path} : JWT expiré (client: {ws.client.host})"
        )
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(
            f"WebSocket {ws.url.path} : JWT invalide — {e} "
            f"(client: {ws.client.host})"
        )
        return None
```

---

## Phase 3 : Rate Limiting WebSocket (Optionnel)

Même avec authentification, limiter le nombre de messages par connexion
pour protéger le LLM sur RPi4 :

```python
# TODO: Ajouter rate limiting dans ws_ai.py
MAX_MESSAGES_PER_MINUTE = 10
message_count = 0
last_reset = time.time()

# Dans la boucle while True:
if message_count >= MAX_MESSAGES_PER_MINUTE:
    await ws.send_json({"type": "error", "content": "Rate limit atteint"})
    await asyncio.sleep(1)
    continue
```

---

## Checklist d'implémentation

### Phase 1 (Court terme)
- [ ] Créer `backend/api/utils/ws_auth.py`
- [ ] Modifier `backend/api/routers/ws_ai.py` — vérification avant `ws.accept()`
- [ ] Modifier `backend/api/routers/realtime_router.py` — même pattern
- [ ] Ajouter `WS_API_KEY` dans `docker-compose.yml` (obligatoire via `:?`)
- [ ] Ajouter `WS_API_KEY` dans `.env.example`
- [ ] Modifier frontend `frontend/utils/supabase_realtime.py` — transmettre token
- [ ] Tests unitaires `tests/unit/test_ws_auth.py`
- [ ] Commit "feat(security): add token-based websocket authentication"

### Phase 2 (Long terme — après Phase 8 Supabase)
- [ ] Créer `backend/api/utils/supabase_ws_auth.py`
- [ ] Remplacer `verify_ws_token` par `verify_supabase_jwt`
- [ ] Ajouter `PyJWT>=2.8.0` dans `backend/api/requirements.txt`
- [ ] Tests d'intégration avec Supabase Auth
- [ ] Documentation mise à jour

### Phase 3 (Optionnel)
- [ ] Rate limiting par connexion WebSocket
- [ ] Monitoring des connexions WebSocket (métriques)

---

## Impact sur le Frontend

Le frontend NiceGUI devra transmettre le token lors de la connexion WebSocket :

```python
# frontend/utils/supabase_realtime.py ou ws_client.py
import os

WS_API_KEY = os.getenv("WS_API_KEY", "")
ws_url = f"ws://api:8001/ws/chat?token={WS_API_KEY}"
```

---

## Variables d'environnement requises

| Variable | Phase | Description | Obligatoire |
|----------|-------|-------------|-------------|
| `WS_API_KEY` | 1 | Token partagé pour WebSocket | Phase 1 |
| `SUPABASE_JWT_SECRET` | 2 | Secret JWT Supabase (déjà requis) | Phase 2 |

---

## Risques et Mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Token WS_API_KEY exposé dans logs | Moyen | Ne jamais logger le token complet |
| JWT expiré côté client | Faible | Refresh automatique côté frontend |
| Surcharge LLM sans rate limit | Haute | Phase 3 rate limiting |
| Compatibilité NiceGUI WebSocket | Moyen | Tester query params avec NiceGUI |

---

**Créé par** : BLACKBOXAI  
**Date** : 2026-03-03  
**Statut** : 📋 Planifié — implémentation après Phase 8 Supabase Auth
