from nicegui import ui

def about_dialog():
    with ui.dialog() as about, ui.card().classes("items-center"):
        ui.label("Informations").classes("text-lg")
        # ui.label(f'Version {__version__}')
        ui.label("Made with ❤️ by David Orel")
        ui.button("", icon="close", on_click=about.close).classes(
            "px-3 py-2 text-xs ml-auto "
        )
    return about