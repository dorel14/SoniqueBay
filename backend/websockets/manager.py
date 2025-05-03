from fastapi import WebSocket
from typing import Dict, List

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, client_id: str):
        self.active_connections[client_id].remove(websocket)
        if not self.active_connections[client_id]:
            del self.active_connections[client_id]

    async def broadcast(self, message: dict, event_type: str = "update"):
        for client_connections in self.active_connections.values():
            for connection in client_connections:
                await connection.send_json({
                    "event": event_type,
                    "data": message
                })

ws_manager = WebSocketManager()
