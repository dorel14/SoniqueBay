from nicegui import ui
from frontend.utils.app_state import get_state
from frontend.utils.logging import logger
import time


def left_drawer_component():
    logger.debug("Début de l'initialisation du left_drawer")
    start_time = time.time()
    
    state = get_state()
    try:
        # Définir explicitement la valeur initiale pour éviter la détection automatique (qui cause les timeouts)
        with ui.left_drawer(value=state.left_drawer_open)\
            .bind_value(state, 'left_drawer_open')\
            .classes('items-center justify-between px-8 bg-[#020617] border-r border-white/5') as left_drawer:
            with ui.column().classes('sb-glass h-full w-full p-8 gap-2 items-center'):
                ui.icon('music_note').classes('text-4xl text-white')
                ui.label('Exploration').classes('sb-subtitle')
                ui.separator().classes('bg-white')
                ui.button('Médiathèque', icon='library_music', on_click=lambda: ui.navigate.to('/'))\
                    .props('outline rouded dense')\
                    .classes('sb-subtitle p-2 m-2 shadow-xl/10 shadow-indigo-500/50')
                
        logger.debug(f"Initialisation du left_drawer terminée en {time.time() - start_time:.2f} secondes")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du left_drawer: {e}")
        raise
