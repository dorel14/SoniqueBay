# -*- coding: utf-8 -*-
import os
from mutagen import File
from .helpers.logging import logger

def scan_music_files(directory):
    Track = [
        ('title', str),
        ('artist', str),
        ('album', str),
        ('path', str)
    ]
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.ogg')):
                full_path = os.path.join(root, f)
                audio = File(full_path, easy=True)
                track = Track(
                    title=audio.get('title', [f])[0],
                    artist=audio.get('artist', ['Inconnu'])[0],
                    album=audio.get('album', ['Inconnu'])[0],
                    path=full_path
                )
        logger.debug(f"Track: {track}")