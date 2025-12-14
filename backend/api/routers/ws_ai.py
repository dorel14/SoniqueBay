from fastapi import WebSocket,  APIRouter
from backend.api.utils.database import AsyncSessionLocal
from backend.ai.orchestrator import Orchestrator


router = APIRouter()

@router.websocket("/ws/chat")
async def chat(ws: WebSocket):
    await ws.accept()

    async with AsyncSessionLocal() as db:
        orchestrator = Orchestrator(db)
        await orchestrator.init()  # ← LIGNE CRUCIALE

        while True:
            msg = await ws.receive_text()
            async for chunk in orchestrator.handle_stream(msg):
                await ws.send_json(chunk)