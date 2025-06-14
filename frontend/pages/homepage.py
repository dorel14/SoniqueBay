# -*- coding: UTF-8 -*-
from nicegui import ui


def content() -> None:
    """Contenu de la page d'accueil."""
    ui.label('SoniqueBay').classes('text-2xl font-bold').style('font-family: Poppins')
    ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg font-poppins')
    ui.separator()
    ui.label('Bienvenue sur SoniqueBay !').classes('text-3xl font-bold w-full text-center').style('font-family: Poppins')
