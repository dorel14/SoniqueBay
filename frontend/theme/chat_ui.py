"""
Interface utilisateur du chat IA pour SoniqueBay.
Classe maintenable inspirée de ChatDemo avec streaming WebSocket.
Auteur : Kilo Code
"""
import asyncio
import json
import websockets
from typing import List, Dict, Any, Optional
from nicegui import ui
from frontend.utils.logging import logger


class ChatUI:
    """Interface utilisateur pour le chat IA avec streaming temps réel."""

    def __init__(self):
        self.container = ui.column()
        self.messages: List[Dict[str, Any]] = []
        self.current_message: Optional[ui.chat_message] = None
        self.current_response_text = ""
        self.session_id: Optional[str] = None
        self.websocket = None
        self.input_field: Optional[ui.input] = None
        self.send_button: Optional[ui.button] = None
        self.messages_container = ui.column()

        # Initialiser l'interface
        with self.container:
            self._setup_ui()

        # WebSocket connection will be handled when needed
        # self._connect_websocket()  # Commented out as it's async and not awaited

    def _setup_ui(self):
        """Configure l'interface utilisateur du chat."""
        with ui.column().classes('w-full h-full flex flex-col'):
            # Conteneur des messages avec scroll
            with ui.scroll_area().classes('flex-grow w-full p-4 bg-gray-50 dark:bg-gray-900').style('height: calc(100vh - 200px); overflow-y: auto;'):
                self.messages_container = ui.column().classes('w-full space-y-2')

            # Zone de saisie en bas
            with ui.row().classes('w-full p-4 bg-white dark:bg-gray-800 border-t items-center gap-2'):
                self.input_field = ui.input(
                    placeholder='Posez une question sur votre musique...',
                    on_change=self._on_input_change
                ).classes('flex-1').props('outlined dense')

                # Gestion de l'appui sur Entrée
                self.input_field.on('keydown.enter', self._send_message)

                self.send_button = ui.button(
                    on_click=self._send_message,
                    icon='send'
                ).props('dense').classes('shrink-0')

    def _on_input_change(self, e):
        """Gère les changements dans le champ de saisie."""
        # Activer/désactiver le bouton en fonction du contenu
        value = e.get('value', '') if isinstance(e, dict) else getattr(e, 'value', '')
        has_text = bool(value.strip())
        self.send_button.set_enabled(has_text)

    async def _send_message(self, e=None):
        """Envoie un message au chat IA."""
        message_text = self.input_field.value.strip()
        if not message_text:
            return

        try:
            # Désactiver l'input pendant l'envoi
            self.input_field.set_enabled(False)
            self.send_button.set_enabled(False)

            # Ajouter le message utilisateur à l'interface
            self._add_user_message(message_text)

            # Pour l'instant, simuler une réponse (TODO: intégrer API réelle)
            await asyncio.sleep(1)  # Simulation de délai
            self._add_bot_message("Je suis l'assistant IA musical. Cette fonctionnalité est en développement.")

            # Vider le champ de saisie
            self.input_field.set_value('')

        except Exception as error:
            logger.error(f"Erreur envoi message: {error}")
            self._add_error_message("Erreur lors de l'envoi du message")
        finally:
            # Réactiver l'input
            self.input_field.set_enabled(True)
            self._on_input_change({'value': self.input_field.value})

    def _add_user_message(self, text: str):
        """Ajoute un message utilisateur à l'interface."""
        with self.messages_container:
            with ui.chat_message(name='Vous', avatar='./static/user_avatar.jpg').classes('self-end bg-gray-100 text-white'):
                ui.label(text).classes('text-sm')

        # Scroll vers le bas
        self._scroll_to_bottom()

    def _add_bot_message(self, text: str):
        """Ajoute un message du bot à l'interface."""
        with self.messages_container:
            with ui.chat_message(name='Assistant IA', avatar='./static/chat_agent.png').classes('self-start bg-gray-100 text-gray-800'):
                ui.label(text).classes('text-sm')

        # Scroll vers le bas
        self._scroll_to_bottom()

    def _add_bot_message_start(self):
        """Commence l'affichage d'un message du bot."""
        with self.messages_container:
            self.current_message = ui.chat_message(
                name='Assistant IA',
                avatar='./static/chat_agent.png',
                text_html=True
            )
            with self.current_message:
                ui.html('<span class="text-sm text-gray-500">Réfléchit...</span>')

        self.current_response_text = ""
        self._scroll_to_bottom()

    def _update_bot_message(self, chunk: str):
        """Met à jour le message du bot avec un nouveau chunk."""
        if self.current_message:
            self.current_response_text += chunk
            with self.current_message:
                ui.html(f'<span class="text-sm">{self.current_response_text}</span>')

    def _finish_bot_message(self):
        """Finalise l'affichage du message du bot."""
        if self.current_message:
            # Remplacer le texte temporaire par le texte final
            with self.current_message:
                ui.html(f'<span class="text-sm">{self.current_response_text}</span>')

        self.current_message = None
        self._scroll_to_bottom()

    def _add_error_message(self, text: str):
        """Ajoute un message d'erreur à l'interface."""
        with self.messages_container:
            with ui.chat_message(name='Erreur', avatar='⚠️').classes('self-center bg-red-100 text-red-800'):
                ui.label(text).classes('text-sm')

        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Fait défiler vers le bas du conteneur de messages."""
        # Utiliser JavaScript pour scroller
        ui.run_javascript('''
            const container = document.querySelector('.q-scrollarea__content');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        ''')

    async def _connect_websocket(self):
        """Établit la connexion WebSocket pour le chat (TODO: implémenter)."""
        # TODO: Implémenter la connexion WebSocket pour streaming temps réel
        pass

    def add_system_message(self, message: str):
        """Ajoute un message système (progression, notifications) au chat."""
        with self.messages_container:
            with ui.chat_message(name='SoniqueBay', avatar='library_music').classes('self-center bg-blue-50 text-blue-800 border border-blue-200'):
                ui.label(message).classes('text-sm font-medium')

        # Scroll vers le bas
        self._scroll_to_bottom()

    def clear_chat(self):
        """Vide l'historique du chat."""
        self.messages.clear()
        self.session_id = None
        with self.messages_container:
            ui.html('')  # Vider le conteneur

    def get_container(self):
        """Retourne le conteneur principal pour intégration."""
        return self.container