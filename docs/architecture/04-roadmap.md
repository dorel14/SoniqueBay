# Roadmap – (Persona)

## IA / Recommandation
- Requête hybride : tags + vectorisation + SQL
- Prise en compte BPM et tonalité
- Exclusion automatique morceaux récents
- Suggestions en continu dans UI

## Intégrations externes
- Last.fm / ListenBrainz : historique + enrichissement
- Napster : playlists + historique écoute
- Soulseek (slskd) : auto-téléchargement morceaux manquants

## UI / UX à venir
- Meilleure transition entre tracks (gapless)
- Navigation rapide par filtres combinés
- Aperçu vectoriel d’affinité (plus tard)

## Architecture & optimisation
- SSE généralisé pour les retours workers
- Cache Redis prioritaire
- Génération playlist → M3U téléchargeable

## Objectif IA
Lors de l’écriture de nouvelle feature :
1. Utiliser workers pour long-running
2. Publier progression via SSE
3. Respecter contraintes RPi4
