from nicegui import ui
from frontend.pages.layout.theme import apply_sonique_theme
import httpx
import os
from frontend.pages.components.artists_cards import artist_component
from frontend.utils.logging import logger

async def get_artists_count_async():
    """Version async de get_artists_count pour éviter le blocage de la boucle."""
    api_url = os.getenv('API_URL', 'http://api:8001')
    logger.info(f"DEBUG get_artists_count_async: Appel API {api_url}/api/artists/count")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/artists/count", timeout=10.0)
        response.raise_for_status()
        count = response.json()["count"]
        logger.info(f"DEBUG get_artists_count_async: count={count}")
        return count

async def main():
    apply_sonique_theme()

    # Récupérer le client courant pour logging
    client = ui.context.client
    logger.info(f"DEBUG main: client_id={client.id if client else 'None'}, has_socket={client.has_socket_connection if client else 'N/A'}")

    try:
        count = await get_artists_count_async()
        logger.info(f"DEBUG main: artists_count={count}")

        if count > 0:
            logger.info("DEBUG main: Appel artist_component()")
            await artist_component()
        else:
            ui.label('Pas d\'artistes dans la base de données')
    except Exception as e:
        logger.error(f"DEBUG main: Erreur dans main(): {e}")
        ui.notify(f"Erreur lors du chargement: {e}", color='negative')

    ui.link('Go to other page', '/other')
    ui.link('artist detail', '/artist_details?id=97')
