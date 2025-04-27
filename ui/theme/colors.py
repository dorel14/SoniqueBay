# fichier: ui/theme/colors.py

THEME_DARK = {
    'primary': '#00B4D8',
    'background': '#0D1B2A',
    'surface': '#1B263B',
    'on_primary': '#E0E1DD',
    'on_background': '#E0E1DD',
    'on_surface': '#E0E1DD',
    'accent': '#0077B6',
}

THEME_LIGHT = {
    'primary': '#0077B6',
    'background': '#E0E1DD',
    'surface': '#FFFFFF',
    'on_primary': '#0D1B2A',
    'on_background': '#0D1B2A',
    'on_surface': '#0D1B2A',
    'accent': '#00B4D8',
}

def set_background(color: str) -> None:
    from nicegui import ui
    ui.query('body').style(f'background-color: {color}')

def apply_theme():
    from nicegui import ui

    def set_colors(dark: bool):
        theme = THEME_DARK if dark else THEME_LIGHT
        ui.colors(
            primary=theme['primary'],
            background=theme['background'],
            surface=theme['surface'],
            accent=theme['accent'],
            primary_text=theme['on_primary'],
            background_text=theme['on_background'],
            surface_text=theme['on_surface'],
        )

    ui.dark_mode().bind_value_to(lambda: set_colors(ui.dark_mode().value))
    set_colors(ui.dark_mode().value)

# Dans ton main.py tu feras :
# from ui.theme.colors import apply_theme
# apply_theme() juste avant ui.run()
