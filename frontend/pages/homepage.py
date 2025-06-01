# -*- coding: UTF-8 -*-
from nicegui import ui


def content() -> None:
    ui.label('SoniqueBay').classes('text-2xl font-bold sonique-text-muted')
    ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg sonique-primary-text')
    ui.separator()
    ui.label('Bienvenue sur SoniqueBay !').classes('text-3xl font-bold w-full sonique-text-title')
