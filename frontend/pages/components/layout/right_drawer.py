from nicegui import ui
from frontend.utils.app_state import get_state
from frontend.utils.logging import logger
import time


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
            with ui.column().classes('sb-glass h-full w-full p-6 gap-4'):
                with ui.tabs().classes('text-white text-sm') as tabs:
                    chat_tab = ui.tab('Chat', label='Chat', icon='chat')
                    queue_tab = ui.tab('Queue', label='File d\'attente', icon='queue_music')
                with ui.tab_panels(tabs, value=state.active_tab).bind_value(state, 'active_tab').classes('flex-1'):
                    with ui.tab_panel('Chat').classes('p-2'):
                        ui.label('Chat')
                    with ui.tab_panel('Queue').classes('p-2'):
                        ui.label('Queue')
                        
        logger.debug(f"Initialisation du right_drawer terminée en {time.time() - start_time:.2f} secondes")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du right_drawer: {e}")
        raise
