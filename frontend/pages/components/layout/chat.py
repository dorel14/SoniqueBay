from nicegui import App, ui
from datetime import datetime
from frontend.utils.app_state import get_state, Appstate
from frontend.utils.logging import logger

messages = Appstate.chat_messages

@ui.refreshable
def chat_messages(own_id: str) -> None:
    if messages:
        for user_id, avatar, text, stamp in messages:
            ui.chat_message(text=text, stamp=stamp, avatar=avatar, sent=own_id == user_id)
    else:
        ui.label('No messages yet').classes('mx-auto my-36')
    ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

