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

def post_listenbrainz_scrobble(track_id, timestamp):
    settings = get_api_settings()
    url = 'https://api.listenbrainz.org/1/submit-listens'
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': f'ListenBrainz-Scrobbler/{settings["listenbrainz_user"]}'
    }
    data = {
        'listens': [
            {
                'recording_msid': track_id,
                'timestamp': timestamp
            }
        ]
    }
    r = requests.post(url, json=data, headers=headers)
    return r.status_code == 200


def post_lastfm_scrobble(track_id, timestamp):
    settings = get_api_settings()
    url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'track.scrobble',
        'api_key': settings['lastfm_api_key'],
        'artist': track_id.split(':')[0],
        'track': track_id.split(':')[1],
        'timestamp': timestamp,
        'format': 'json'
    }
    r = requests.get(url, params=params)
    return r.status_code == 200