# Project Brief: SoniqueBay

## Vue d'ensemble
SoniqueBay est une application musicale modulaire (Library + Player + IA + Chat) auto-hébergée, conçue pour fonctionner de manière performante sur un Raspberry Pi 4. Elle combine une gestion locale de bibliothèque, un lecteur audio fluide, des fonctionnalités d'IA pour la recommandation, un système de chat intelligent et des capacités d'enrichissement automatique des métadonnées.

## Composants Clés
1.  **Frontend** : Interface utilisateur réactive construite avec NiceGUI.
2.  **Backend API** : FastAPI + GraphQL servant de point d'entrée unique vers les données.
3.  **Workers** : Système asynchrone (Celery) pour les tâches lourdes (Scan, Analyse Audio, Vectorisation, Enrichissement).
4.  **Data Layer** : PostgreSQL pour le stockage robuste et Redis pour le cache/PubSub.
5.  **Service de Chat IA** : Agent conversationnel intelligent intégré pour l'interaction utilisateur avec PydanticAi.
6.  **Module de Recherche Hybride** : Combinaison intelligente SQL + Vectorielle + PostgreSQL FTS pour une recherche optimisée.
7.  **Système de Couvertures** : Extraction et gestion automatique des pochettes d'albums avec traitement d'images.
8.  **Service d'Enrichissement** : Métadonnées enrichies via intégrations externes (Last.fm, etc.) et analyse audio avancée.
9.  **Moteur de Recommandations Avancées** : Basé sur BPM, tonalité, styles musicaux et vectorisation sémantique.

## Technologies Clés
- **Indexation** : PostgreSQL FTS pour la recherche textuelle locale
- **Communication Temps Réel** : SSE (Server-Sent Events) pour les progressions, WebSocket pour le contrôle du player
- **Vectorisation** : Ollama (LLM local) pour les embeddings sémantiques
- **Analyse Audio** : Extraction de caractéristiques audio (BPM, tonalité, spectral)

## Objectifs Principaux
- Offrir une expérience utilisateur fluide (SPA) malgré les contraintes matérielles du RPi4.
- Fournir des recommandations intelligentes via vectorisation et analyse de métadonnées.
- Maintenir une architecture stricte "Separation of Concerns" pour la maintenabilité.
- Intégrer un agent conversationnel pour une interaction naturelle avec la bibliothèque musicale.
- Assurer l'enrichissement automatique et la découverte de contenu musical.