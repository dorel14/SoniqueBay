# -*- coding: utf-8 -*-
import os
from mutagen import File
from mutagen.id3 import ID3
from helpers.logging import configure_worker_logging



def scan_music_files(directory):
    # Obtenir le logger configuré pour ce processus
    worker_logger = configure_worker_logging()
    worker_logger.info("Scanning directory:", directory)
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.ogg')):
                full_path = os.path.join(root, f)
                worker_logger.info("Processing file:", full_path)
                audio = File(full_path, easy=True)
                tags = ID3(full_path)
                infos = audio.info
                print(tags.pprint())
                #worker_logger.info(f"Audio: {audio}")
                track = {
                    'title': audio.get('title', [f])[0],
                    'artist': audio.get('artist', ['Inconnu'])[0],
                    'album': audio.get('album', ['Inconnu'])[0],
                    'path': full_path,
                    'genre': audio.get('genre', [''])[0],
                    'year': audio.get('date', [''])[0],
                    'disc_number': audio.get('discnumber', [''])[0],
                    'track_number': audio.get('tracknumber', [''])[0],
                    'acoustid_fingerprint': audio.get('acoustid_fingerprint', [''])[0],
                    'duration': int(infos.length),
                    'musicbrain_id': audio.get('musicbrainz_trackid', [''])[0],
                    'musicbrain_albumid': audio.get('musicbrainz_albumid', [''])[0],
                    'musicbrain_artistid': audio.get('musicbrainz_artistid', [''])[0],
                    'musicbrain_albumartistid': audio.get('musicbrainz_albumartistid', [''])[0],
                    'musicbrain_genre': audio.get('musicbrainz_genre', [''])[0],
                    'cover': tags.get('APIC:').data if tags.get('APIC:') else None,
                }
                #worker_logger.info(f"Track: {track}")
                yield track
