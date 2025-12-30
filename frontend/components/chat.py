import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from nicegui import ui
from frontend.services.central_websocket_service import CentralWebSocketService
from frontend.utils.logging import logger

# État global du chat pour @ui.refreshable
chat_messages: List[Dict[str, Any]] = []
chat_ws: Optional[CentralWebSocketService] = None
chat_connected = False
chat_connecting = False
current_agent: Optional[str] = None
current_spinner: Optional[bool] = None  # Indicateur booléen pour l'affichage
current_label: Optional[bool] = None    # Indicateur booléen pour l'affichage
streaming_text = ""

# Instance globale pour le binding
connection_status = "🔴 Déconnecté"


@ui.refreshable
def chat_component():
    """Composant de chat IA avec @ui.refreshable pour gestion facile des états."""
    global chat_messages, chat_connected, chat_connecting, current_spinner, current_label, current_agent, streaming_text, connection_status

    with ui.column().classes("w-full h-full"):

        with ui.scroll_area().classes("flex-grow p-4"):
            messages_container = ui.column().classes("w-full gap-3")

            # Message système initial
            if not chat_messages:
                with messages_container:
                    ui.chat_message(
                        name="Système",
                        text="🎵 Bienvenue sur SoniqueBay Assistant\nPosez une question sur votre musique.",
                    ).classes("opacity-70 text-sm")

            # Afficher tous les messages
            with messages_container:
                for msg in chat_messages:
                    if msg["type"] == "user":
                        ui.chat_message(
                            name="Vous",
                            text=msg["content"],
                            sent=True,
                            stamp=msg.get("stamp", ""),
                        )
                    elif msg["type"] == "agent":
                        ui.chat_message(
                            name=msg.get("agent_name", "Assistant IA"),
                            avatar="./static/chat_agent.png",
                            text=msg["content"],
                            stamp=msg.get("stamp", ""),
                        )
                    elif msg["type"] == "system":
                        ui.chat_message(
                            name="Système",
                            text=msg["content"],
                        ).classes("opacity-70 text-sm")

                # Spinner en cours
                if current_spinner:
                    with ui.chat_message(
                        name=current_agent or "Assistant IA",
                        avatar="./static/chat_agent.png",
                        text="…",
                        stamp=_now(),
                    ):
                        ui.spinner(type="dots", size="lg")

                # Label de streaming
                if current_label and streaming_text:
                    with ui.chat_message(
                        name=current_agent or "Assistant IA",
                        avatar="./static/chat_agent.png",
                        text=streaming_text,
                        stamp=_now(),
                    ):
                        ui.label(streaming_text).classes("whitespace-pre-wrap")

        with ui.row().classes("w-full p-3 border-t border-white/5 items-center gap-2 bg-slate-800/50"):
            input_field = ui.input(
                placeholder="Votre message…",
                on_change=lambda e: _check_input(input_field, send_btn),
            ).classes("flex-1 bg-slate-700 border-slate-600 text-white placeholder:text-slate-400").props("outlined dark")
            input_field.on("keydown.enter", lambda: _send_message(input_field))

            send_btn = ui.button(
                icon="send",
                on_click=lambda: _send_message(input_field),
            ).props("dense color=indigo").classes("text-indigo-400")

        # Créer un label d'état lié à la variable globale connection_status
        ui.label(connection_status).classes("text-xs opacity-60 text-blue-100")

        # Démarrer la connexion si pas encore fait
        if not chat_connecting and not chat_connected:
            asyncio.create_task(_start_chat())


# ------------------------------------------------------------------
# Fonctions auxiliaires
# ------------------------------------------------------------------

async def _start_chat():
    """Démarre la connexion WebSocket pour le chat."""
    global chat_ws, chat_connected, chat_connecting, connection_status

    if chat_connecting or chat_connected:
        logger.info("Connexion déjà en cours ou déjà connecté, annulation")
        return

    chat_connecting = True
    connection_status = "🟡 Connexion…"
    logger.info("Début de la connexion WebSocket pour le chat")

    try:
        logger.info("Création de l'instance CentralWebSocketService")
        chat_ws = CentralWebSocketService()
        logger.info(f"URL WebSocket configurée: {chat_ws.base_ws_url}")

        def on_message(raw: Dict[str, Any]):
            try:
                logger.debug(f"Message brut reçu: {raw}")
                payload = raw.get("data", raw)
                logger.debug(f"Payload extrait: {payload}")

                if isinstance(payload, str):
                    payload = payload.strip()
                    if payload.startswith("```") and payload.endswith("```"):
                        payload = payload[3:-3].strip()

                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload_clean = payload.replace('\n', '').replace('\r', '').strip()
                        if payload_clean.startswith("```") and payload_clean.endswith("```"):
                            payload_clean = payload_clean[3:-3].strip()
                        payload = json.loads(payload_clean)

                logger.debug(f"Payload analysé: {payload}")
                if payload.get("type") != "text":
                    logger.debug(f"Message non texte ignoré, type: {payload.get('type')}")
                    return

                state = payload.get("state")
                content = payload.get("content", "")
                agent = payload.get("agent_name", "Assistant IA")

                logger.info(f"Message agent reçu - État: {state}, Agent: {agent}")
                _handle_agent_message(state, content, agent)

            except Exception as e:
                logger.error(f"Erreur message chat: {e}", exc_info=True)

        logger.info("Enregistrement du handler pour le canal 'chat'")
        chat_ws.register_handler("chat", on_message)
        
        # S'assurer que la connexion utilise le bon endpoint
        logger.info(f"Endpoint WebSocket configuré: {chat_ws.base_ws_url}")
        
        logger.info("Appel de la méthode connect()")
        connection_success = await chat_ws.connect()
        
        # Vérifier si la connexion a réussi
        if connection_success:
            logger.info("Connexion WebSocket établie avec succès")
            chat_connected = True
            chat_connecting = False
            connection_status = "🟢 Connecté"
            chat_component.refresh()
        else:
            logger.error("Connexion WebSocket échouée")
            chat_connecting = False
            connection_status = "🔴 Connexion échouée"
            chat_component.refresh()

    except Exception as e:
        logger.error(f"Erreur connexion chat: {e}", exc_info=True)
        chat_connecting = False
        connection_status = "🔴 Erreur connexion"
        chat_component.refresh()


def _handle_agent_message(state: str, content: str, agent: str):
    """Gère les messages des agents."""
    global current_agent, current_spinner, current_label, chat_messages

    # Nouvel agent → reset UI
    if current_agent != agent:
        _reset_agent_ui()
        current_agent = agent

    if state == "thinking":
        _show_thinking(agent, text=content)

    elif state in ("stream", "done"):
        _update_stream(content, agent)

        if state == "done":
            _finalize_stream()

    chat_component.refresh()


def _show_thinking(agent: str, text: str = "…"):
    """Affiche l'état thinking."""
    global current_spinner, current_agent

    if current_spinner:
        return

    current_agent = agent
    current_spinner = True  # Indicateur pour l'affichage


def _update_stream(text: str, agent: str):
    """Met à jour le streaming."""
    global current_spinner, current_label, streaming_text, current_agent

    # Supprimer spinner si présent
    if current_spinner:
        current_spinner = False

    # Mettre à jour le texte de streaming
    if not current_label:
        current_agent = agent
        current_label = True

    streaming_text = text


def _finalize_stream():
    """Finalise le streaming."""
    global chat_messages, current_label, current_spinner, current_agent, streaming_text

    if streaming_text:
        chat_messages.append({
            "type": "agent",
            "agent_name": current_agent or "Assistant IA",
            "content": streaming_text,
            "stamp": _now()
        })

    current_label = False
    current_spinner = False
    current_agent = None
    streaming_text = ""


def _reset_agent_ui():
    """Reset l'UI de l'agent."""
    global current_spinner, current_label, streaming_text

    current_spinner = False
    current_label = False
    streaming_text = ""


async def _send_message(input_field: ui.input):
    """Envoie un message utilisateur."""
    global chat_ws, chat_connected, chat_messages

    text = (input_field.value or "").strip()
    logger.info(f"Tentative d'envoi de message: '{text}'")
    logger.info(f"État de la connexion: {chat_connected}")
    logger.info(f"Service WebSocket: {chat_ws}")
    
    if not text:
        logger.warning("Message vide, envoi annulé")
        return
        
    if not chat_connected:
        logger.error("Impossible d'envoyer - pas connecté au WebSocket")
        return

    # Ajouter message utilisateur
    chat_messages.append({
        "type": "user",
        "content": text,
        "stamp": _now()
    })

    input_field.value = ""

    # Reset état IA
    _reset_agent_ui()

    logger.info(f"Appel de chat_ws.send() avec canal 'chat' et données: {text}")
    try:
        await chat_ws.send(
            "chat",
            {"message": text, "timestamp": datetime.now().isoformat()}
        )
        logger.info("Message envoyé avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message: {e}", exc_info=True)
        return

    chat_component.refresh()


def _check_input(input_field: ui.input, send_btn: ui.button):
    """Vérifie l'état de l'input."""
    global chat_connected

    has_text = bool((input_field.value or "").strip())
    if has_text and chat_connected:
        send_btn.enable()
    else:
        send_btn.disable()


def _now() -> str:
    """Retourne l'heure actuelle."""
    return datetime.now().strftime("%H:%M:%S")
