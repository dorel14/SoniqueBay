# Architecture – Contexte Global (Persona)

## Objectif global
SoniqueBay est une application musicale modulaire (library + player + IA) fonctionnant sur Raspberry Pi 4 avec optimisation mémoire/CPU.

## Vue d'ensemble
- Frontend : NiceGUI + SSE & WebSocket pour le temps réel
- Backend principal : FastAPI + GraphQL
- Workers : Celery (scan / audio / vectorisation / enrichissement)
- Base : PostgreSQL/SQLite + Redis cache
- Cible hardware : Raspberry Pi 4 (optimisations obligatoires)

## Principes d'architecture
- Separation of concerns (UI / API / Workers / DB)
- Tous les traitements lourds → workers Celery
- L’API est la *seule* couche qui touche la DB
- Vectorisation stockée pour éviter recalcul
- SSE préféré au WS pour la progress bar et scan

## Flux internes simplifiés
Frontend → API (GraphQL/REST) → Workers → DB/Redis → SSE vers UI

## Enjeux
- Cohérence entre services
- Performance RPi4
- Maintenabilité modulaire
- Support futur d’intégration Napster/Soulseek
