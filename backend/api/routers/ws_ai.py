from fastapi import WebSocket, APIRouter
from fastapi.websockets import WebSocketDisconnect
from backend.api.utils.database import AsyncSessionLocal
from backend.ai.orchestrator import Orchestrator
from backend.api.utils.logging import logger


router = APIRouter()


@router.websocket("/ws/chat")
async def chat(ws: WebSocket) -> None:
    """
    Endpoint WebSocket pour le chat IA.
    - Accepte la connexion
    - Initialise l'orchestrateur (chargement async des agents)
    - Boucle de réception/envoi des messages
    - Gère proprement la déconnexion du client
    """
    await ws.accept()
    logger.info("WebSocket /ws/chat : connexion acceptée")

    try:
        async with AsyncSessionLocal() as db:
            orchestrator = Orchestrator(db)
            await orchestrator.init()  # Chargement async des agents

            while True:
                try:
                    msg = await ws.receive_text()
                    logger.debug(
                        "WebSocket /ws/chat : message reçu",
                        extra={"message_preview": msg[:80]}
                    )
                    async for chunk in orchestrator.handle_stream(msg):
                        await ws.send_json(chunk)

                except WebSocketDisconnect:
                    logger.info("WebSocket /ws/chat : client déconnecté proprement")
                    break

    except RuntimeError as exc:
        # Erreur d'initialisation de l'orchestrateur (ex: agent manquant)
        logger.error(
            f"WebSocket /ws/chat : erreur d'initialisation de l'orchestrateur — {exc}",
            exc_info=True
        )
        await ws.send_json({
            "type": "error",
            "content": "Erreur d'initialisation du service IA. Veuillez réessayer.",
        })
        await ws.close(code=1011)

    except Exception as exc:
        logger.error(
            f"WebSocket /ws/chat : erreur inattendue — {exc}",
            exc_info=True
        )
        try:
            await ws.send_json({
                "type": "error",
                "content": "Une erreur inattendue est survenue.",
            })
            await ws.close(code=1011)
        except Exception:
            pass  # Le socket est peut-être déjà fermé
