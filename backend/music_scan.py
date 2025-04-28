# -*- coding: utf-8 -*-
import os
from annotated_types import T
from mutagen import File
from .helpers.logging import logger



def scan_music_files(directory):
    logger.info("Scanning directory:", directory)
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.ogg')):
                full_path = os.path.join(root, f)
                logger.info("Processing file:", full_path)
                audio = File(full_path, easy=True)
                track = {
                    'title': audio.get('title', [f])[0],
                    'artist': audio.get('artist', ['Inconnu'])[0],
                    'album': audio.get('album', ['Inconnu'])[0],
                    'path': full_path,
                    'genre': audio.get('genre', [''])[0],
                    'year': audio.get('date', [''])[0],
                    'disc_number': audio.get('discnumber', [''])[0],
                    'track_number': audio.get('tracknumber', [''])[0]
                }
                logger.info(f"Track: {track}")
                yield track
