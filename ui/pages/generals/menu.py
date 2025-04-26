from nicegui import ui

def menu() -> None:
    with ui.column().classes('w-1/5 text-white h-screen p-4'):
        with ui.row().classes('items-center'):
            ui.label('SoniqueBay').classes('text-2xl font-bold mb-4')
        with ui.list().props('bordered separator'):
            ui.item_label('Navigation').props('header')
            ui.separator()

            with ui.item(on_click=lambda: ui.navigate.to('/')):
                with ui.item_section().props('avatar'):
                    ui.icon('home')
                with ui.item_section():
                    ui.label('Accueil')

            with ui.item(on_click=lambda: ui.navigate.to('/recherche')):
                with ui.item_section().props('avatar'):
                    ui.icon('search')
                with ui.item_section():
                    ui.label('Recherche')

            with ui.item(on_click=lambda: ui.navigate.to('/lecture')):
                with ui.item_section().props('avatar'):
                    ui.icon('play_arrow')
                with ui.item_section():
                    ui.label('Lecture')

            with ui.expansion(text='Paramètres', group='menu'):
                with ui.item(on_click=lambda: ui.navigate.to('/parametres')):
                    with ui.item_section().props('avatar'):
                        ui.icon('settings')
                    with ui.item_section():
                        ui.label('Paramètres API')