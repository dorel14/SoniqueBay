from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.websockets.manager import ws_manager
import uuid

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    if not client_id:
        client_id = str(uuid.uuid4())

    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Traiter les messages reçus si nécessaire
            await ws_manager.broadcast(data)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, client_id)
