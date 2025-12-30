# Plan de Refactorisation Frontend SoniqueBay - Pattern MVC

## Objectif

Refactoriser le frontend pour appliquer le pattern MVC, séparer les fonctions utilitaires en services, et assurer la continuité du fonctionnement.

## Structure MVC proposée

- **Model** : Services métier (services/)
- **View** : Interfaces utilisateur (pages/, theme/)
- **Controller** : Logique de contrôle (controllers/)

## Étapes de refactorisation

### 1. Analyse des fonctions utilitaires

- Identifier les fonctions dans utils/, services/, websocket_manager/ et theme/ qui sont des services métier
- utils/logging.py : configuration des logs (rester en utils)
- utils/music_tree_data.py : fonctions get_library_tree() et get_albums_for_artist() - services d'accès données
- services/progress_message_service.py : déjà un service (rester)
- websocket_manager/ws_client.py : gestion WS/SSE - service de communication
- theme/layout.py : contient logique métier (search, refresh_library, etc.) - à extraire

### 2. Création des répertoires

- Créer frontend/controllers/ pour la logique de contrôle
- Assurer que frontend/services/ existe (déjà présent)

### 3. Déplacement et création de services

- Déplacer utils/music_tree_data.py vers services/library_service.py
- Créer services/search_service.py pour la logique de recherche
- Créer services/scan_service.py pour la gestion des scans et sessions
- Créer services/websocket_service.py pour centraliser WS/
- Mettre en place l'utilisation de graphql pour la page de detail artist (artists_detail) afin d'optimiser l'appel api
- Préparer la gestion du chat avecagantg IA 

### 4. Extraction de la logique métier de layout.py

- Extraire les fonctions : search(), make_progress_handler(), delete_scan_session(), refresh_library()
- Les placer dans les services appropriés
- Nettoyer layout.py pour ne garder que la vue

### 5. Réorganisation de theme/

- Garder theme/ pour les vues : layout.py (nettoyé), menu.py, chat_ui.py, colors.py

### 6. Mise à jour des imports

- Mettre à jour tous les imports dans les fichiers affectés
- Assurer la compatibilité avec les nouveaux chemins

### 7. Gestion des fichiers obsolètes

- Créer frontend/_old/ pour isoler les fichiers obsolètes
- Identifier et déplacer les fichiers non utilisés

### 8. Test de continuité

- Tester que l'application démarre et fonctionne après refactorisation
- Vérifier que toutes les fonctionnalités sont préservées

## Avantages attendus

- Séparation claire des responsabilités (MVC)
- Code plus maintenable et modulaire
- Réutilisabilité des services
- Facilité de test et d'extension
