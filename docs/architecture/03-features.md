# Features existantes – (Persona)

## Gestion de bibliothèque
- Scan de fichiers audio
- Métadonnées : Artist / Album / Track / Cover
- Téléchargement automatique des pochettes
- Index Whoosh pour recherche rapide

## Lecture multimédia
- Player intégré
- Play / Pause / Skip
- File de lecture en temps réel (WebSocket)
- Crossfade / transitions fluides

## Interface utilisateur (NiceGUI)
- Navigation par artiste / album avec vignettes
- Arborescence type TreeView animée
- Surlignage de l’élément actif
- Recherche avancée avec facettes

## Recommandation / IA (déjà partiellement en place)
- Prévectorisation en base
- Suggestions basées sur tags
- Évitement morceaux récemment joués

## Temps réel / backend
- SSE pour progression (scan, analyse…)
- WebSocket pour contrôle lecture
- Workers Celery (scan/audio/vectorisation)
