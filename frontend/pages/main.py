from nicegui import ui
from frontend.pages.layout.theme import apply_sonique_theme
import httpx
import os
from frontend.pages.components.artists_cards import artist_component

def get_artists_count():
    with httpx.Client() as client:
        response = client.get(os.getenv('API_URL', 'http://api:8001') + '/api/artists/count')
        response.raise_for_status()
        return response.json()["count"]

async def main():
    apply_sonique_theme()
    #ui.label('Hello, NiceGUI!')
    if get_artists_count() > 0: 
        await artist_component()
    else:
        ui.label('Pas d\'artistes dans la base de données')
    ui.link('Go to other page', '/other')
    ui.link('artist detail', '/artist_details?id=97')
