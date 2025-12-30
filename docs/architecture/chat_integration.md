# Intégration du Chat IA avec WebSocket

## Vue d'ensemble

Ce document décrit l'intégration du composant de chat IA avec le backend via WebSocket, permettant un streaming en temps réel des réponses.

## Architecture

### Frontend

Le composant `ChatUI` dans `frontend/components/chat.py` a été refactorisé pour:

1. **Communication WebSocket** : Utilise `ui.connect_websocket()` pour établir une connexion persistante avec le backend
2. **Streaming en temps réel** : Reçoit et affiche les réponses chunk par chunk
3. **Gestion des erreurs** : Gère les déconnexions et tente une reconnexion automatique
4. **UI responsive** : Interface utilisateur optimisée pour NiceGUI avec animations fluides

### Backend

Le router `chat_api.py` dans `backend/api/routers/` fournit:

1. **Endpoint WebSocket** : `/chat/ws` pour la communication bidirectionnelle
2. **Streaming asynchrone** : Utilise `ChatService.stream_response()` pour envoyer des chunks
3. **Validation des messages** : Vérifie le format des messages entrants
4. **Gestion des erreurs** : Retourne des messages d'erreur structurés

## Flux de données

```
Utilisateur → Frontend (ChatUI) → WebSocket → Backend (ChatService) → WebSocket → Frontend (ChatUI) → Utilisateur
```

## Bonnes pratiques

### Performance

1. **Streaming progressif** : Les réponses sont envoyées chunk par chunk pour éviter de surcharger la mémoire
2. **Reconnexion automatique** : En cas de déconnexion, le client tente de se reconnecter après 5 secondes
3. **Optimisation UI** : Le scroll automatique est limité pour éviter les calculs inutiles

### Code

1. **Séparation des responsabilités** : 
   - `ChatUI` gère uniquement l'interface utilisateur
   - `ChatService` gère la logique métier
   - Le WebSocket gère la communication

2. **Gestion d'état** : 
   - `is_connected` : Indique si la connexion WebSocket est active
   - `connecting` : Empêche les tentatives de reconnexion multiples
   - `reactions` : Stocke les réactions utilisateur par message

3. **Logs structurés** : Utilise `frontend.utils.logging` pour le suivi des événements

### Intégration

```python
# Dans frontend/main.py
chat_ui = ChatUI()

# Démarrer la connexion après le rendu de l'UI
async def start_chat():
    await chat_ui.start()

ui.timer(0.1, start_chat, once=True)
```

## Configuration

### URL WebSocket

Par défaut, le composant utilise `ws://localhost:8000/chat/ws`. Pour personnaliser:

```python
chat_ui = ChatUI(websocket_url="ws://votre-serveur:port/chat/ws")
```

### Messages

Format des messages envoyés via WebSocket:

```json
{
  "message": "Votre question ici",
  "timestamp": "2025-12-26T14:54:04.068Z"
}
```

Format des réponses reçues:

```json
{
  "type": "chunk",
  "message_id": "bot_1",
  "text": "Fragment de la réponse"
}
```

```json
{
  "type": "complete",
  "message_id": "bot_1"
}
```

```json
{
  "type": "error",
  "message": "Description de l'erreur"
}
```

## Dépannage

### Problèmes de connexion

1. Vérifier que le backend FastAPI est en cours d'exécution
2. Vérifier que l'URL WebSocket est correcte
3. Vérifier les logs du backend pour les erreurs
4. Vérifier les logs du frontend pour les messages de connexion

### Messages non reçus

1. Vérifier que le WebSocket est connecté (indicateur vert)
2. Vérifier que le backend traite correctement les messages
3. Vérifier les logs pour les erreurs de streaming

### Performance

1. Limiter la taille des messages pour éviter la surcharge
2. Utiliser le streaming pour les réponses longues
3. Éviter de charger trop d'historique de messages

## Tests

### Test de base

1. Démarrer le backend : `docker-compose up backend-api`
2. Démarrer le frontend : `docker-compose up frontend`
3. Ouvrir l'interface et envoyer un message
4. Vérifier que la réponse s'affiche en streaming

### Test de reconnexion

1. Envoyer un message
2. Arrêter le backend
3. Redémarrer le backend
4. Vérifier que le frontend se reconnecte automatiquement

## Améliorations futures

1. **Historique des conversations** : Persister les messages dans la base de données
2. **Typing** : Ajouter la complétion automatique des questions
3. **Multilingue** : Support pour plusieurs langues
4. **Rich media** : Affichage d'images et de musique dans les réponses
5. **Analyse des sentiments** : Réactions automatiques basées sur le ton du message

## Références

- [NiceGUI WebSocket](https://nicegui.io/documentation/web-socket)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [Architecture SoniqueBay](.kilocode/rules/memory-bank/00-architecture.md)