from nicegui import ui

def menu() -> None:
    with ui.menu().classes():
        with ui.menu_item(on_click=lambda: ui.navigate.to('/')).classes(''):
            with ui.item_section().props('avatar'):
                ui.icon('home')
            with ui.item_section():
                ui.label('Accueil')

        with ui.menu_item(on_click=lambda: ui.navigate.to('/recherche')).classes(''):
            with ui.item_section().props('avatar'):
                ui.icon('search')
            with ui.item_section():
                ui.label('Recherche')

        with ui.menu_item(on_click=lambda: ui.navigate.to('/api_docs')).classes(''):
            with ui.item_section().props('avatar'):
                ui.icon('description')
            with ui.item_section():
                ui.label('API Docs')

        with ui.menu_item(text='Paramètres', auto_close=False).classes(''):
            with ui.item_section().props('side'):
                ui.icon('keyboard_arrow_right')
                with ui.menu().props('anchor="top end" self="top start" auto-close').classes(''):
                    with ui.menu_item().classes('sonique-menu-item'):
                        with ui.item_section().props('avatar'):
                            ui.icon('settings')
                        with ui.item_section():
                            ui.label('Paramètres API')