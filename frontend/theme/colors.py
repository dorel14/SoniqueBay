# ui/theme/colors.py
from nicegui import ui

THEME_DARK = {
    'primary': '#00bcd4',         # cyan SoniqueBay
    'secondary': '#041b2d',       # fond sombre
    'accent': '#0077B6',          # bleu secondaire
    'dark': '#041b2d',
    'dark_page': '#041b2d',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}

THEME_LIGHT = {
    'primary': '#0077B6',         # bleu Sonique
    'secondary': '#eaf7fa',       # fond clair doux
    'accent': '#00bcd4',          # accent cyan
    'dark': '#f5f5f5',
    'dark_page': '#fafafa',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}

def set_body_class(class_name: str):
    ui.run_javascript(f'document.body.className = "{class_name}";')

def apply_theme():
    from nicegui import ui

    def set_colors(dark: bool):
        theme = THEME_DARK if dark else THEME_LIGHT
        ui.colors(
            primary=theme['primary'],
            secondary=theme['secondary'],
            accent=theme['accent'],
            dark=theme['dark'],
            positive=theme['positive'],
            negative=theme['negative'],
            info=theme['info'],
            warning=theme['warning'],
        )
    set_body_class('sonique-background' if THEME_DARK else 'bg-white')
    # Applique automatiquement selon le switch
    ui.dark_mode().bind_value_to(lambda: set_colors(ui.dark_mode().value))
    set_colors(ui.dark_mode().value)
