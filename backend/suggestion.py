# -*- coding: utf-8 -*-

import requests
from backend.utils.settings import get_setting

class APIConfigError(Exception):
    pass

def get_api_settings():
    settings = {
        'listenbrainz_user': get_setting('listenbrainz_user'),
        'listenbrainz_api_key': get_setting('listenbrainz_api_key'),
        'lastfm_user': get_setting('lastfm_user'),
        'lastfm_api_key': get_setting('lastfm_api_key')
    }

    if not all(settings.values()):
        missing = [k for k, v in settings.items() if not v]
        raise APIConfigError(f"Paramètres manquants: {', '.join(missing)}")

    return settings

def get_listenbrainz_recommendations():
    settings = get_api_settings()
    url = f'https://api.listenbrainz.org/1/user/{settings["listenbrainz_user"]}/recommendations'
    r = requests.get(url)
    if r.status_code == 200:
        return [r['recording_msid'] for r in r.json().get('payload', {}).get('recommendations', [])]
    return []

def get_lastfm_similar(track_title, artist_name):
    settings = get_api_settings()
    url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'track.getsimilar',
        'artist': artist_name,
        'track': track_title,
        'api_key': settings['lastfm_api_key'],
        'format': 'json'
    }
    r = requests.get(url, params=params)
    if r.status_code == 200:
        return [
            (t['name'], t['artist']['name'])
            for t in r.json().get('similartracks', {}).get('track', [])
        ]
    return []