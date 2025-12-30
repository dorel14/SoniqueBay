from nicegui import ui
from frontend.config import sonique_bay_logo
from frontend.utils.logging import logger
#from frontend.theme.layout import COMMON_LINK_CLASSES
from frontend.services.artist_service import ArtistService


async def get_artist_info(artist_id: int):
    """Récupère les informations d'un artiste depuis l'API."""
    return await ArtistService.get_artist(artist_id)

async def get_artist_albums(artist_id: int):
    """Récupère les albums d'un artiste depuis l'API."""
    return await ArtistService.get_artist_albums(artist_id)

async def get_artist_tracks(artist_id: int, album_id: int = None):
    """Récupère les pistes d'un artiste depuis l'API."""
    return await ArtistService.get_artist_tracks(artist_id, album_id)


def artist_details_page(artist_id: str):
    """Page de détails d'un artiste."""
    # Convertir artist_id en entier
    try:
        artist_id_int = int(artist_id)
    except (ValueError, TypeError):
        artist_id_int = 0
    
    render_artists_details(artist_id_int)
@ui.refreshable
async def artist_tracks_container(artist_id: int, album_id: int = None):
    # Si aucun album sélectionné, ne rien afficher ou afficher toutes les pistes
    
    if not album_id:
        ui.label("Sélectionnez un album pour voir ses pistes.").classes('italic text-gray-500')
        return

    tracks_data = await get_artist_tracks(artist_id, album_id)
    if not tracks_data:
        ui.label("Aucune piste trouvée pour cet album.").classes("text-red-500")
        return

    with ui.card().classes('w-full max-w-4xl  p-4 bordered bg-base-200 mt-4'):
        #ui.label(f"Pistes de l'album {album_id}").classes('text-xl font-bold mb-4')

        ui.table(columns=[
            {'name': 'title', 'label': 'Titre', 'field': 'title', 'sortable': True},
            {'name': 'duration', 'label': 'Durée', 'field': 'duration', 'sortable': True},
        ],
            rows=tracks_data,
            row_key='id')



@ui.refreshable
async def artist_container(artist_id: int):
    artist_data = await get_artist_info(artist_id)
    artist_container = ui.element('div').classes('w-full').props('id=artist-zone')
    with artist_container:
        with ui.card().classes('w-full bg-primary text-gray-10 p-4'):
            with ui.row().classes('w-full items-center gap-4 p-4'):
                # Zone photo artiste
                with ui.card().classes('w-48 h-48'):
                    try:
                        if artist_data and artist_data['covers']:
                            cover_value = artist_data['covers'][0]['cover_data']
                            mime_type = artist_data['covers'][0].get('mime_type', 'image/png')

                            # Vérifier si c'est une URL base64 valide
                            if cover_value and not cover_value.startswith('data:image/'):
                                # Les données semblent être des données base64 brutes, les formater correctement
                                cover_data = f"data:{mime_type};base64,{cover_value}"
                                logger.info(f"Conversion base64 réussie pour l'artiste {artist_id}")
                            else:
                                cover_data = cover_value
                        else:
                            logger.warning(f"Aucun cover trouvé pour l'artiste {artist_id}, utilisation du logo par défaut.")
                            cover_data = sonique_bay_logo
                    except (IndexError, KeyError, TypeError) as e:
                        logger.warning(f"Erreur lors de l'extraction du cover pour l'artiste {artist_id}: {e}, utilisation du logo par défaut.")
                        cover_data = sonique_bay_logo
                    ui.image(cover_data).classes('w-full h-full object-cover')
                # Zone infos artiste
                with ui.column().classes('flex-grow'):
                    ui.label(artist_data['name']).classes('text-2xl font-bold text-gray-100')
                    ui.separator()
                    with ui.row().classes('gap-4 text-sm mt-2 text-gray-100'):
                        albums_count = ui.label()
                        ui.label()
                        albums_count.set_text(f"Albums: {len(artist_data.get('albums', []))}")
        with ui.row().classes('w-full items-center justify-between mt-4'):
            albums_list = await get_artist_albums(artist_id)
            if albums_list:
                with ui.grid(columns='repeat(auto-fill, minmax(200px, 1fr))').classes('gap-4 p-4 w-full justify-center'):
                    for album in albums_list:
                        album_id_value = album.get('id')
                        with ui.card().tight().classes(
                            'cursor-pointer hover:scale-105 transition-all duration-200 w-[200px] h-[260px] flex flex-col overflow-hidden shadow-md rounded-xl'
                        ).on('click', lambda artist_id=artist_id, album_id=album_id_value: artist_tracks_container.refresh(artist_id=artist_id, album_id=album_id)):
                            # Check if album is a dictionary before calling get()
                            if isinstance(album, dict):
                                if album.get('covers') and isinstance(album.get('covers'), list) and len(album.get('covers')) > 0:
                                    cover_value = album['covers'][0].get('cover_data', '')
                                    mime_type = album['covers'][0].get('mime_type', 'image/png')

                                    # Vérifier si c'est une URL base64 valide
                                    if cover_value and not cover_value.startswith('data:image/'):
                                        # Les données semblent être des données base64 brutes, les formater correctement
                                        cover_data = f"data:{mime_type};base64,{cover_value}"
                                        logger.info(f"Conversion base64 réussie pour l'album {album.get('title', 'inconnu')}")
                                    else:
                                        cover_data = cover_value
                                else:
                                    logger.warning(f"Aucun cover trouvé pour l'album {album.get('title', 'inconnu')}, utilisation du logo par défaut.")
                                    cover_data = sonique_bay_logo
                            else:
                                logger.error(f"Unexpected album type: {type(album)}")
                                cover_data = sonique_bay_logo # provide a default
                            ui.image(cover_data).classes('aspect-[4/3] w-full object-cover')
                            ui.separator()
                            with ui.card_section().classes(
                                'flex flex-col items-center justify-between h-[90px] p-2 bg-gray-50 dark:bg-gray-800 text-center'
                            ):
                                ui.label(album['title']).classes('text-sm font-semibold text-gray-20')
                                ui.label(f"Année: {album.get('release_year', 'N/A')}").classes('text-sm text-gray-600')
                            with ui.card_actions().classes('w-full justify-end mt-3'):
                                ui.icon('play_circle_outline').classes('text-xl cursor-pointer')
                                ui.icon('o_favorite_border').classes('text-xl cursor-pointer')
            else:
                ui.label("Aucun album trouvé pour cet artiste.").classes("text-red-500")
        ui.separator().classes('my-4')

async def render_artists_details(artist_id: int):
    """Affiche les détails d'un artiste."""
    with ui.column().classes('w-full items-center p-4'):
        ui.link('Retour à la liste des artistes', '/artists')
        if artist_id and artist_id > 0:
            await artist_container(artist_id)
            with ui.row().classes('w-full justify-between'):
                await artist_tracks_container(artist_id=artist_id, album_id=None)
        else:
            ui.label("Aucun artiste sélectionné.").classes("text-red-500")