# ui/theme/colors.py

THEME_DARK = {
    'primary': '#00B4D8',
    'secondary': '#1B263B',
    'accent': '#CAF0F8',
    'dark': '#1d1d1d',
    'dark_page': '#121212',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}

THEME_LIGHT = {
    'primary': '#0077B6',
    'secondary': '#E0E1DD',
    'accent': '#00B4D8',
    'dark': '#f5f5f5',  # En light mode c'est moins utilisé
    'dark_page': '#fafafa',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}

def apply_theme():
    from nicegui import ui

    def set_colors(dark: bool):
        theme = THEME_DARK if dark else THEME_LIGHT
        ui.colors(
            primary=theme['primary'],
            secondary=theme['secondary'],
            accent=theme['accent'],
            dark=theme['dark'],
            #dark_page=theme['dark_page'],
            positive=theme['positive'],
            negative=theme['negative'],
            info=theme['info'],
            warning=theme['warning'],
        )

    ui.dark_mode().bind_value_to(lambda: set_colors(ui.dark_mode().value))
    set_colors(ui.dark_mode().value)
