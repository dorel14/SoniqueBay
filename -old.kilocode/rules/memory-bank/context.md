# Active Context

## État Actuel
- **Bibliothèque** : Scan fonctionnel, métadonnées (Artist/Album/Track), indexation PostgreSQL FTS.
- **Player** : Lecture, Pause, Skip, Gestion de file (Queue) via WebSocket.
- **UI** : NiceGUI en place avec navigation Arbre et Recherche à facettes.
- **IA Base** : Pré-vectorisation en base et suggestions simples (tags).

## Focus Actuel (Priorités)
1.  **IA / Recommandation** : Implémenter la requête hybride (Tags + Vecteurs + SQL) et la prise en compte du BPM/Tonalité.
2.  **Optimisation** : Généraliser le SSE pour tous les retours workers vers l'UI.
3.  **Stabilité** : S'assurer que le cache Redis est prioritaire pour soulager le RPi4.

## Décisions Récentes
- **Communication** : SSE est strictement préféré pour la progression (scan/analyse), WebSocket réservé au contrôle du player (play/pause/queue).
- **Développement** : Environnement de développement sous Windows (PowerShell/Batch), cible de déploiement Linux (RPi4).
- **Architecture** : Interdiction stricte pour l'IA ou le Frontend d'accéder à la DB directement ; tout passe par l'API.