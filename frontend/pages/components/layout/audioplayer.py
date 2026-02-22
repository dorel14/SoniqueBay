from nicegui import ui


def audioplayer_component():
    with ui.row().classes('absolute bottom-0 inset-x-0 items-center justify-between no-wrap backdrop-blur-lg border-t border-white/15 p-4'):
            
            # --- ZONE GAUCHE : Infos Média ---
            with ui.row().classes('items-center gap-3 min-w-[200px]'):
                ui.image('https://via.placeholder.com/48').classes('w-12 h-12 rounded shadow-lg')
                with ui.column().classes('gap-0'):
                    ui.label('Titre du morceau').classes('text-white text-sm font-medium leading-none')
                    ui.label('Artiste').classes('text-gray-400 text-xs')

            # --- ZONE CENTRALE : Contrôles et Slider ---
            with ui.column().classes('grow items-center max-w-2xl px-8'):
                # Boutons de lecture
                with ui.row().classes('items-center gap-4'):
                    ui.button(icon='shuffle').props('flat round size=sm').classes('text-gray-400')
                    ui.button(icon='skip_previous').props('flat round size=md').classes('text-white')
                    
                    # Le bouton Play/Pause (à lier à l'état de l'audio)
                    play_btn = ui.button(icon='play_arrow', on_click=lambda: toggle_play()) \
                       .props('round size=lg').classes('bg-white text-black shadow-md')
                    
                    ui.button(icon='skip_next').props('flat round size=md').classes('text-white')
                    ui.button(icon='repeat').props('flat round size=sm').classes('text-gray-400')
                
                # Barre de progression personnalisée (Slider très fin)
                # Monochrome utilise un slider qui prend toute la largeur centrale
                progress_slider = ui.slider(min=0, max=100, value=0) \
                   .props('dense selection-color=white track-size=2px thumb-size=12px') \
                   .classes('w-full mt-[-8px]')

            # --- ZONE DROITE : Volume et Extras ---
            with ui.row().classes('items-center gap-3 min-w-[200px] justify-end'):
                ui.icon('lyrics').classes('text-gray-400 cursor-pointer hover:text-white')
                ui.icon('volume_up').classes('text-gray-400')
                ui.slider(min=0, max=1, step=0.01, value=0.7).classes('w-24') \
                   .props('dense selection-color=white')

    # L'élément audio est présent mais INVISIBLE (pas de props 'controls')
    audio = ui.audio(src='votre_musique.mp3').classes('hidden')
    def toggle_play():
        # Logique pour alterner entre play() et pause()
        pass