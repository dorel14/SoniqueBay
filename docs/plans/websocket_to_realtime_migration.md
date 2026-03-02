# Migration WebSocket → Supabase Realtime

## Vue d'ensemble

Ce document décrit la migration des websockets FastAPI vers Supabase Realtime pour les fonctionnalités temps réel.

## Websockets existants à remplacer

| Endpoint | Fichier | Usage | Remplacement |
|----------|---------|-------|--------------|
| `/ws/chat` | `backend/api/routers/ws_ai.py` | Chat IA streaming | `RealtimeServiceV2` + `chat_realtime_api.py` |
| `/ws` | `backend/api/routers/realtime_router.py` | Notifications temps réel | `RealtimeServiceV2.subscribe_*` |
| `/ws` (chat) | `backend/api/routers/chat_api.py` | Chat streaming | `ChatRealtimeManager` |

## Architecture cible

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (NiceGUI)                   │
│         ┌─────────────────────────────────────┐          │
│         │  Supabase Realtime Client           │          │
│         │  • subscribe("chat:{id}")           │          │
│         │  • subscribe("notifications")       │          │
│         │  • subscribe("progress")            │          │
│         └─────────────────────────────────────┘          │
├─────────────────────────────────────────────────────────┤
│                    BACKEND (FastAPI)                    │
│  ┌─────────────────────────────────────────────────────┐│
│  │  RealtimeServiceV2                                  ││
│  │  • broadcast(channel, event, payload)                 ││
│  │  • subscribe(channel, callback)                       ││
│  │  • send_chat_message(), send_notification()           ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │  chat_realtime_api.py (endpoints HTTP)              ││
│  │  • POST /chat/send                                  ││
│  │  • POST /chat/stream                                ││
│  │  • GET /chat/history/{chat_id}                      ││
│  └─────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│                    SUPABASE REALTIME                    │
│         WebSocket persistant vers PostgreSQL             │
└─────────────────────────────────────────────────────────┘
```

## Changements pour le Frontend

### Avant (WebSocket)

```python
# frontend/services/websocket_service.py
async def connect_chat():
    ws = websocket.connect("ws://api:8001/ws/chat")
    await ws.send(json.dumps({"message": "Hello"}))
    response = await ws.recv()
```

### Après (Supabase Realtime)

```python
# frontend/utils/supabase_realtime.py
from frontend.utils.supabase_client import get_supabase_client

async def connect_chat(chat_id: str):
    supabase = get_supabase_client()
    
    # S'abonner au canal de chat
    channel = supabase.channel(f"chat:{chat_id}")
    channel.on('broadcast', {'event': '*'}, handle_message)
    channel.subscribe()
    
    # Envoyer un message via API HTTP
    await supabase.table("chat_messages").insert({
        "chat_id": chat_id,
        "content": "Hello",
        "sender": "user"
    })
```

## Changements pour le Backend

### Avant (WebSocket)

```python
# backend/api/routers/ws_ai.py
@router.websocket("/ws/chat")
async def chat(ws: WebSocket):
    await ws.accept()
    async for chunk in orchestrator.handle_stream(msg):
        await ws.send_json(chunk)
```

### Après (Supabase Realtime)

```python
# backend/api/routers/chat_realtime_api.py
@router.post("/chat/stream")
async def stream_response(request: ChatStreamRequest):
    # Démarrer le streaming en arrière-plan
    background_tasks.add_task(_stream_ai_response, request.chat_id, request.message)
    return {"success": True}

async def _stream_ai_response(chat_id: str, message: str):
    service = get_realtime_service_v2()
    
    async for chunk in orchestrator.handle_stream(message):
        # Envoyer via Realtime au lieu de WebSocket
        await service.broadcast(
            channel_name=f"chat:{chat_id}",
            event="ai_chunk",
            payload={"chunk": chunk["content"]}
        )
```

## Plan de migration

### Phase 1: Préparation (✅ Complétée)
- [x] Créer `RealtimeServiceV2`
- [x] Créer `ChatRealtimeManager`
- [x] Créer `chat_realtime_api.py`
- [x] Tests unitaires

### Phase 2: Frontend (⏳ À venir)
- [ ] Créer `frontend/utils/supabase_realtime.py`
- [ ] Refactoriser `frontend/services/websocket_service.py`
- [ ] Mettre à jour les pages utilisant les websockets

### Phase 3: Remplacement progressif
- [ ] Feature flag `USE_SUPABASE_REALTIME`
- [ ] Tester les deux systèmes en parallèle
- [ ] Basculer progressivement (10% → 50% → 100%)

### Phase 4: Nettoyage
- [ ] Supprimer les routers websockets obsolètes
- [ ] Supprimer `backend/api/routers/ws_ai.py`
- [ ] Supprimer `backend/api/routers/realtime_router.py`
- [ ] Mettre à jour la documentation

## Avantages de Supabase Realtime

| Aspect | WebSocket FastAPI | Supabase Realtime |
|--------|-------------------|-------------------|
| **Persistance** | Connexion volatile | Reconnexion automatique |
| **Scalabilité** | 1 connexion = 1 thread | Pool de connexions géré |
| **Fiabilité** | Gestion manuelle | ACK, retry, heartbeat intégrés |
| **Intégration DB** | Manuelle | Native (écoute PostgreSQL) |
| **Multi-client** | Complexe | Broadcast automatique |
| **Mobile/PWA** | Gestion complexe | Client SDK optimisé |

## Points d'attention

1. **Migration des données**: L'historique des chats doit être migré vers Supabase
2. **Authentification**: Les canaux Realtime utilisent les mêmes JWT que l'API
3. **RLS**: Configurer les policies Row Level Security pour les canaux
4. **Fallback**: Garder les websockets comme fallback pendant la transition

## Configuration RLS pour Realtime

```sql
-- Activer Realtime sur une table
alter publication supabase_realtime add table chat_messages;

-- Policy pour les messages de chat
create policy "Users can view their chat messages"
on chat_messages for select
using (auth.uid() = user_id);

create policy "Users can send messages"
on chat_messages for insert
with check (auth.uid() = user_id);
```

## Code de test

```python
# Test de connexion Realtime
async def test_realtime():
    service = get_realtime_service_v2()
    
    # S'abonner
    await service.subscribe_chat("test123", lambda e: print(e))
    
    # Envoyer un message
    await service.send_chat_message("test123", {
        "content": "Hello Realtime!",
        "sender": "test"
    })
```

## Références

- [Supabase Realtime Docs](https://supabase.com/docs/guides/realtime)
- [supabase-py Realtime](https://github.com/supabase-community/supabase-py)
- [Migration Guide WebSocket](https://supabase.com/docs/guides/realtime/bring-your-own-database)
