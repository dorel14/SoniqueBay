from nicegui import ui
import json
from typing import Callable, Dict

class WebSocketClient:
    def __init__(self):
        self.ws = None
        self.handlers: Dict[str, list[Callable]] = {}
        self.client_id = None

    async def connect(self):
        self.ws = await ui.websocket_connect('ws://localhost:8001/ws/client')
        await self.listen()

    def on(self, event_type: str, handler: Callable):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    async def listen(self):
        while True:
            try:
                message = await self.ws.receive()
                data = json.loads(message)
                event_type = data.get('event')
                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        await handler(data.get('data'))
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

ws_client = WebSocketClient()
