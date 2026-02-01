from dataclasses import dataclass, field
from nicegui import app

@dataclass
class Appstate:
    left_drawer_open: bool = True
    right_drawer_open: bool = True
    active_tab: str = 'Queue'
    chat_messages: list[tuple[str, str, str, str]] =  field(default_factory=list)
    total_pages: int = 1
    page_size: int = 10
    current_page: int = 1
    last_rendered_page: int = None
    artists_page: int = current_page
    artists_total_pages: int = total_pages
    artists_page_size: int = 10
    artists_cached_pages: dict[int, list] = field(default_factory=dict)  # Clé: skip, Valeur: liste d'artistes
    covers_cache: dict[int, str] = field(default_factory=dict)  # Clé: artist_id, Valeur: URL base64 complète
    view_mode: str = 'list'  # Possible values: 'list', 'grid', etc.
    last_artists_page: int = 1


def get_state():
    if 'state' not in app.storage.user:
        app.storage.user['state'] = Appstate()
    # Convert ObservableDict back to Appstate if needed
    state = app.storage.user['state']
    if not isinstance(state, Appstate):
        # Create a new Appstate instance from the dict
        new_state = Appstate()
        # Update with stored values
        for key, value in state.items():
            if hasattr(new_state, key):
                setattr(new_state, key, value)
        app.storage.user['state'] = new_state
        return new_state
    return state


def toggle_left():
    state = get_state()
    state.left_drawer_open = not state.left_drawer_open


def toggle_right():
    state = get_state()
    state.right_drawer_open = not state.right_drawer_open


def set_tab(tab: str):
    state = get_state()
    state.active_tab = tab


def skip_page(current_page):
    state = get_state()
    return (current_page - 1) * state.page_size

def get_current_page():
    state = get_state()
    return state.current_page

def update_page_size(value: str):
    state = get_state()
    if value.isdigit():
        state.page_size = int(value)


def update_artists_page_size(value: int):
    state = get_state()
    state.artists_page_size = value
    state.artists_cached_pages = {}


def update_current_page(value: str):
    state = get_state()
    if value.isdigit():
        state.current_page = int(value)


def set_view_mode(mode: str):
    state = get_state()
    state.view_mode = mode
