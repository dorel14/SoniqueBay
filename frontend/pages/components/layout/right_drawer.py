from nicegui import ui
from frontend.utils.app_state import get_state
from frontend.utils.logging import logger
import time
from frontend.pages.components.layout.chat import chat_messages, send_message

def right_drawer_component():
    logger.debug("Début de l'initialisation du right_drawer")
    start_time = time.time()
    
    state = get_state()
    logger.debug(f"right_drawer_open initial: {state.right_drawer_open}")
    logger.debug(f"active_tab initial: {state.active_tab}")
    
    try:
        # Définir explicitement la valeur initiale pour éviter la détection automatique (qui cause les timeouts)
        with ui.right_drawer(value=state.right_drawer_open)\
            .bind_value(state, 'right_drawer_open')\
            .classes('bg-[#020617] border-r border-white/5') as right_drawer:
            with ui.column().classes('sb-glass h-full w-full p-2 gap-1 flex flex-col'):
                with ui.tabs().classes('text-white text-sm w-full') as tabs:
                    chat_tab = ui.tab('Chat', label='Chat', icon='chat')
                    queue_tab = ui.tab('Queue', label='File d\'attente', icon='queue_music')
                
                with ui.tab_panels(tabs, value=state.active_tab).bind_value(state, 'active_tab').classes('flex-1 flex flex-col w-full'):
                    # Panel Chat avec flexbox pour prendre toute la hauteur disponible
                    with ui.tab_panel('Chat').classes('p-1 flex flex-col h-full'):
                        # Conteneur principal avec flexbox
                        with ui.column().classes('gap-2 w-full h-full flex flex-col'):
                            # Zone de messages avec défilement (flex-grow pour prendre l'espace disponible)
                            with ui.card().classes('flex-grow w-full overflow-hidden p-0 bg-slate-900/50 border border-white/10'):
                                chat_messages(state.user_id)
                            
                            # Zone de saisie avec bouton d'envoi
                            with ui.row().classes("w-full items-center bg-slate-800/50 rounded-md p-2 border border-white/10"):
                                # Input avec flex-grow pour prendre l'espace disponible
                                message_input = ui.input(placeholder='Tapez votre message...').classes(
                                    'w-full flex-grow bg-transparent border border-white/20 rounded-md '
                                    'text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500'
                                )
                                
                                # Bouton d'envoi
                                send_btn = ui.button(icon='send').props('flat round dense').classes(
                                    'text-blue-400 hover:text-blue-300'
                                )
                                
                                # Fonction pour envoyer le message
                                async def handle_send():
                                    if message_input.value:
                                        await send_message(message_input.value, state.user_id)
                                        message_input.value = ''  # Vider l'input après envoi
                                
                                # Connecter les événements
                                send_btn.on('click', handle_send)
                                message_input.on('keydown.enter', handle_send)
                    
                    # Panel Queue
                    with ui.tab_panel('Queue').classes('p-2'):
                        ui.label('Queue')

        logger.debug(f"Initialisation du right_drawer terminée en {time.time() - start_time:.2f} secondes")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du right_drawer: {e}")
        raise
