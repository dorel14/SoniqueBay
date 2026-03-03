from nicegui import ui
import httpx
import os
import datetime
from frontend.utils.config import sonique_bay_logo
from frontend.utils.logging import logger
from frontend.utils.app_state import get_state

from frontend.services.artist_service import ArtistService

api_url = os.getenv('API_URL', 'http://api:8001')
PUBLIC_API_URL = os.getenv('PUBLIC_API_URL', 'http://localhost:8001')

async def get_artist_details(artist_id: int) -> dict | None:
    """Récupère les informations complètes d'un artiste (infos, albums, pistes) via GraphQL.

    Args:
        artist_id: L'identifiant de l'artiste.

    Returns:
        Un dictionnaire contenant les données de l'artiste ou None si non trouvé.
    """
    logger.info(f"get_artist_details() :: Récupération des données pour l'artiste {artist_id}")

    query = '''
    query GetArtistDetails($artistId: Int!) {
        artist(id: $artistId) {
            id
            name
            covers {
                url
            }
            albums {
                id
                title
                releaseYear
                covers {
                    url
                }
                tracks {
                    id
                    trackNumber
                    title
                    duration
                }
            }
        }
    }
    '''

    variables = {'artistId': artist_id}

    try:
        result = await ArtistService.query_graphql(query, variables)
        logger.debug(f"get_artist_details() :: Résultat GraphQL pour l'artiste {artist_id}: {result}")

        if result and 'artist' in result:
            return result['artist']

        logger.error(f"get_artist_details() :: Aucun artiste trouvé avec l'ID {artist_id}")
        return None

    except Exception as e:
        logger.error(f"get_artist_details() :: Erreur GraphQL pour l'artiste {artist_id}: {e}")
        return await _get_artist_details_fallback_rest(artist_id)


async def _get_artist_details_fallback_rest(artist_id: int) -> dict | None:
    """Fallback REST pour récupérer les détails d'un artiste si GraphQL échoue.

    Args:
        artist_id: L'identifiant de l'artiste.

    Returns:
        Un dictionnaire structuré comme la réponse GraphQL ou None si échec.
    """
    logger.info(f"_get_artist_details_fallback_rest() :: Fallback REST pour l'artiste {artist_id}")

    async with httpx.AsyncClient() as client:
        # Récupérer les infos de base de l'artiste
        artist_response = await client.get(f"{api_url}/api/artists/{artist_id}")
        if artist_response.status_code != 200:
            logger.error(f"Fallback REST échoué pour l'artiste {artist_id}")
            return None

        artist_data = artist_response.json()

        # Récupérer les albums
        albums_response = await client.get(f"{api_url}/api/albums/artists/{artist_id}")
        albums = albums_response.json() if albums_response.status_code == 200 else []

        # Pour chaque album, récupérer les pistes
        for album in albums:
            album_id = album.get('id')
            if album_id:
                tracks_response = await client.get(f"{api_url}/api/tracks/artists/{artist_id}/albums/{album_id}")
                album['tracks'] = tracks_response.json() if tracks_response.status_code == 200 else []

        artist_data['albums'] = albums
        return artist_data


def format_duration(seconds: float) -> str:
    """Convertit une durée en secondes en format MM:SS ou HH:MM:SS.

    Args:
        seconds: Durée en secondes.

    Returns:
        Chaîne formatée (MM:SS si < 60min, sinon HH:MM:SS).
    """
    try:
        seconds = int(seconds)
        if seconds < 3600:  # Moins de 60 minutes
            minutes, secs = divmod(seconds, 60)
            return f"{minutes:02d}:{secs:02d}"
        else:  # 60 minutes ou plus
            delta = datetime.timedelta(seconds=seconds)
            return str(delta)
    except (ValueError, TypeError):
        return "00:00"

@ui.refreshable
async def artist_container(artist_id: int) -> None:
    """Affiche les détails d'un artiste avec ses albums et pistes.

    Args:
        artist_id: L'identifiant de l'artiste à afficher.
    """
    logger.info(f"artist_container() :: Affichage de l'artiste {artist_id}")

    # Une seule requête GraphQL pour tout récupérer
    artist_data = await get_artist_details(artist_id)

    if artist_data is None:
        ui.label("Impossible de charger les informations de l'artiste.").classes("text-red-500")
        logger.error(f"artist_container() :: artist_data est None pour l'artiste {artist_id}")
        return

    albums_list = artist_data.get('albums', [])

    with ui.element('div').classes('w-full').props('id=artist-zone'):
        # Carte d'en-tête avec photo et infos
        with ui.card().classes('w-full sb-card-artist flex gap-6 items-center'):
            with ui.row().classes('w-full items-center gap-4 p-4'):
                # Zone photo artiste
                with ui.card().classes('w-48 h-48 rounded-xl bg-white p-2'):
                    try:
                        if artist_data.get('covers'):
                            cover_url = f"{PUBLIC_API_URL}/api/covers/artist/{artist_id}"
                        else:
                            logger.warning(f"Aucun cover trouvé pour l'artiste {artist_id}, utilisation du logo par défaut.")
                            cover_url = sonique_bay_logo
                    except (IndexError, KeyError, TypeError) as e:
                        logger.warning(f"Erreur lors de l'extraction du cover pour l'artiste {artist_id}: {e}")
                        cover_url = sonique_bay_logo

                    ui.image(cover_url).classes('w-full h-full object-cover').props('loading=lazy')

                # Zone infos artiste
                with ui.column().classes('flex-grow'):
                    ui.label(artist_data['name']).classes('text-2xl font-bold text-gray-100')
                    ui.separator().classes('opacity-20 my-1')
                    with ui.row().classes('gap-4 text-sm mt-2 text-gray-100'):
                        ui.label(f"Albums: {len(albums_list)}")

        # Liste des albums
        with ui.row().classes('w-full items-center justify-between mt-4'):
            if not albums_list:
                ui.label("Aucun album trouvé pour cet artiste.").classes("text-red-500")
            else:
                for album in albums_list:
                    await _render_album_expansion(album)

        ui.separator().classes('my-4')


async def _render_album_expansion(album: dict) -> None:
    """Rend l'expansion d'un album avec ses pistes.

    Args:
        album: Dictionnaire contenant les données de l'album (id, title, covers, tracks).
    """
    if not isinstance(album, dict):
        logger.error(f"_render_album_expansion() :: Type d'album inattendu: {type(album)}")
        return

    album_title = album.get('title', 'Album inconnu')
    tracks_data = album.get('tracks', [])

    with ui.expansion(album_title).classes('w-full text-white').props('dense expand-separator duration:10') as expansion:
        # Header de l'expansion avec cover
        with expansion.add_slot('header'):
            with ui.grid(columns='auto 1fr').classes('w-full flex-wrap align-start gap-2'):
                # Récupération du cover
                cover_url = sonique_bay_logo
                try:
                    covers = album.get('covers')
                    if covers and isinstance(covers, list) and len(covers) > 0:
                        cover_url = f"{PUBLIC_API_URL}/api/covers/album/{album.get('id')}"
                        logger.info(f"Cover URL généré pour l'album {album_title}: {cover_url}")
                except (KeyError, TypeError) as e:
                    logger.warning(f"Erreur cover pour l'album {album_title}: {e}")

                ui.image(cover_url).classes('aspect-[4/3] w-16 object-cover').props('loading=lazy')
                ui.label(album_title).classes('text-white')

        # Contenu: liste des pistes
        if not tracks_data:
            ui.label("Aucune piste trouvée pour cet album.").classes("text-red-500")
            return

        # Formatage des pistes avec durée
        formatted_tracks = []
        for track in tracks_data:
            try:
                track['duration_formatted'] = format_duration(track.get('duration', 0))
                formatted_tracks.append(track)
            except Exception as e:
                logger.error(f"Erreur formatage durée pour la piste {track.get('title', 'inconnu')}: {e}")
                track['duration_formatted'] = "00:00"
                formatted_tracks.append(track)

        # Tableau des pistes
        tracks_table = ui.table(
            columns=[
                {'name': 'track_number', 'label': 'N°', 'field': 'trackNumber', 'sortable': True},
                {'name': 'title', 'label': 'Titre', 'field': 'title', 'sortable': True},
                {'name': 'duration_formatted', 'label': 'Durée', 'field': 'duration_formatted', 'sortable': True},
                {'name': 'action', 'label': 'Action', 'align': 'center'},
            ],
            rows=formatted_tracks,
            row_key='id',
            column_defaults={
                'align': 'left',
                'headerClasses': 'uppercase text-black font-bold',
            },
        ).classes('sb-table-tracks w-full').props('flat bordered dense')

        # Slot pour les actions
        with tracks_table.add_slot('body-cell-action'):
            with tracks_table.cell('action'):
                with ui.row().classes('left-0 gap-3 w-full'):
                    ui.icon('play_circle_outline').classes('text-xl cursor-pointer text-gray-500 hover:text-bg-gray-900')
                    ui.icon('o_favorite_border').classes('text-xl cursor-pointer text-gray-500 hover:text-bg-gray-900')


async def artist_details_page(artist_id: int):
    def go_back():
        state = get_state()
        logger.info(f"Retour aux artistes, last_artists_page={state.last_artists_page}")
        ui.run_javascript(f"window.location.href = '/?page={state.last_artists_page}'")

    with ui.column().classes('w-full p-4'):
        ui.button('Retour aux artistes', icon='arrow_back', on_click=go_back)\
            .props('outline rouded dense')\
            .classes('sb-subtitle p-2 m-2 shadow-xl/10 shadow-indigo-500/50')
        ui.separator().classes('my-4')
        logger.info(f"DEBUG: artist_details_page() appelée avec artist_id={artist_id}")
        if artist_id:
            await artist_container(artist_id)
        else:
            ui.label("Aucun artiste sélectionné.").classes("text-red-500")