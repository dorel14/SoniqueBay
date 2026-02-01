from nicegui import ui

def settings_menu_component() -> None:
    with ui.menu().classes('sb-header'):
        with ui.menu_item(on_click=lambda: ui.navigate.to('/api_docs')).classes('text-sm sonique-menu-item'):
            with ui.item_section().props('avatar'):
                ui.icon('description').classes('text-white text-sm')
            with ui.item_section():
                ui.label('API Docs').classes('text-white text-sm')

        with ui.menu_item(text='Paramètres', auto_close=False).classes('text-white text-sm sonique-menu-item'):
            with ui.item_section().props('side'):
                ui.icon('keyboard_arrow_right')
                with ui.menu().props('anchor="top end" self="top start" auto-close').classes(''):
                    with ui.menu_item().classes('sonique-menu-item'):
                        with ui.item_section().props('avatar'):
                            ui.icon('settings').classes('text-white')
                        with ui.item_section():
                            ui.label('Paramètres API').classes('text-white')