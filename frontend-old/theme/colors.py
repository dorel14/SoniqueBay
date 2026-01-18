# frontend/theme/colors.py
from nicegui import ui

THEME_LIGHT = {
    'primary': '#042f50',
    'secondary': "#c6c9ca",
    'accent': '#00BCD4',
    'dark': "#413e46",
    #'dark_page': '#fafafa',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}

THEME_DARK = {
    'primary': '#00BCD4',
    'secondary': "#042f50",
    'accent': '#0077B6',
    'dark': "#0e283b",
    #'dark_page': '#041b2d',
    'positive': '#21ba45',
    'negative': '#c10015',
    'info': '#31ccec',
    'warning': '#f2c037',
}


def apply_theme():
    dark_mode_state = ui.dark_mode()
    
    def update_colors(is_dark: bool):
        theme = THEME_DARK if is_dark else THEME_LIGHT
        ui.colors(**theme)
    
    dark_mode_state.on('value_change', lambda e: update_colors(e.value))
    update_colors(dark_mode_state.value)