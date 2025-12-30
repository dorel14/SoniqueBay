# Refactorisation du Système de Communication WebSocket

## Vue d'ensemble

Ce document décrit la refactorisation du système de communication WebSocket pour SoniqueBay, qui introduit un service centralisé avec gestion de canaux multiples.

## Problèmes résolus

1. **URLs incohérentes** : Le chat utilisait le port 8000 (inexistant), tandis que SSE utilisait le port 8001
2. **Gestion fragmentée** : Chaque composant gérait sa propre connexion WebSocket
3. **Pas de canaux différenciés** : Impossible de différencier les messages par fonctionnalité
4. **Problèmes de reconnexion** : Gestion des déconnexions non optimisée

## Architecture nouvelle

### Service Centralisé : CentralWebSocketService

Localisation : `frontend/services/central_websocket_service.py`

Ce service centralise toute la gestion des connexions WebSocket et SSE avec les fonctionnalités suivantes :

- **Gestion de canaux** : Support pour plusieurs canaux de communication
  - `chat`: Communication avec les agents IA
  - `playqueue`: Gestion de la file de lecture
  - `system`: Messages système
  - `progress`: Messages de progression (scan, analyse, etc.)

- **Connexion unique** : Une seule connexion WebSocket pour tous les canaux
- **Reconnexion automatique** : Gestion transparente des déconnexions
- **Compatibilité** : API compatible avec l'ancien WebSocketService

### Canaux disponibles

| Canal | Description | Utilisation |
|-------|-------------|------------|
| `chat` | Communication avec les agents IA | ChatUI |
| `playqueue` | Mises à jour temps réel de la file de lecture | PlayQueue |
| `system` | Messages système et notifications | WebSocketService (compatibilité) |
| `progress` | Messages de progression des tâches | WebSocketService (compatibilité) |

## Migrations effectuées

### 1. WebSocketService

**Fichier** : `frontend/services/websocket_service.py`

**Changements** :
- Utilise maintenant `CentralWebSocketService` en interne
- Maintain la compatibilité avec l'API existante
- Enregistre les handlers dans le canal `system` par défaut

**Avant** :
```python
class WebSocketService:
    def __init__(self):
        self.ws_url = os.getenv("WS_URL", "ws://api:8001/api/ws")
        # Gestion propre des connexions
```

**Après** :
```python
class WebSocketService:
    def __init__(self):
        self._central_service = CentralWebSocketService()
        # Utilise le service centralisé
```

### 2. ChatUI

**Fichier** : `frontend/components/chat.py`

**Changements** :
- Utilise `CentralWebSocketService` avec le canal `chat`
- URL corrigée : `ws://api:8001/ws/chat` (port 8001 au lieu de 8000)
- Envoi et réception sur le canal `chat`

**Avant** :
```python
from frontend.services.websocket_service import WebSocketService

class ChatUI:
    def __init__(self):
        self.websocket_service = WebSocketService()
        # Utilisait l'ancien service
```

**Après** :
```python
from frontend.services.central_websocket_service import CentralWebSocketService

class ChatUI:
    def __init__(self):
        self.websocket_service = CentralWebSocketService()
        # Utilise le service centralisé avec canal 'chat'
```

### 3. Backend API

**Fichier** : `backend/api/routers/ws_ai.py`

**Changements** :
- Endpoint WebSocket existant : `/ws/chat`
- Compatible avec le nouveau système de canaux
- Pas de modification nécessaire (déjà correct)

## Configuration

### Variables d'environnement

| Variable | Valeur par défaut | Description |
|----------|------------------|-------------|
| `WS_URL` | `ws://api:8001` | URL de base pour WebSocket |
| `SSE_URL` | `http://api:8001/api/events` | URL pour Server-Sent Events |

### Exemple d'utilisation

```python
# Pour le chat
from frontend.services.central_websocket_service import CentralWebSocketService

ws_service = CentralWebSocketService()

# Enregistrer un handler pour le canal 'chat'
def chat_handler(data):
    print(f"Message reçu sur canal chat: {data}")

ws_service.register_handler('chat', chat_handler)

# Démarrer la connexion
await ws_service.connect()

# Envoyer un message
await ws_service.send('chat', {'message': 'Hello!'})
```

## Avantages

1. **Centralisation** : Une seule connexion WebSocket pour tous les canaux
2. **Évolutivité** : Ajout facile de nouveaux canaux
3. **Performance** : Réduction des connexions simultanées
4. **Maintenabilité** : Code plus modulaire et facile à maintenir
5. **Compatibilité** : Migration transparente pour les composants existants

## Migration pour les nouveaux composants

Pour créer un nouveau composant utilisant WebSocket :

1. Importer `CentralWebSocketService`
2. Enregistrer un handler pour le canal approprié
3. Utiliser `send(channel, data)` pour envoyer des messages

```python
from frontend.services.central_websocket_service import CentralWebSocketService

class MonComposant:
    def __init__(self):
        self.ws_service = CentralWebSocketService()
        self.ws_service.register_handler('mon_canal', self._handle_message)
    
    def _handle_message(self, data):
        # Traiter les messages
        pass
    
    async def send_message(self, data):
        await self.ws_service.send('mon_canal', data)
```

## Dépannage

### Problèmes de connexion

1. Vérifier que le backend FastAPI est en cours d'exécution sur le port 8001
2. Vérifier les logs du backend pour les erreurs WebSocket
3. Vérifier les logs du frontend pour les messages de connexion

### Messages non reçus

1. Vérifier que le handler est bien enregistré pour le bon canal
2. Vérifier que le message contient le bon champ `channel`
3. Vérifier les logs pour les erreurs de streaming

### Performance

1. Limiter la taille des messages pour éviter la surcharge
2. Utiliser le streaming pour les réponses longues
3. Éviter de charger trop d'historique de messages

## Tests

### Test de base

1. Démarrer le backend : `docker-compose up api_service`
2. Démarrer le frontend : `docker-compose up frontend`
3. Ouvrir l'interface et envoyer un message dans le chat
4. Vérifier que la réponse s'affiche en streaming

### Test de reconnexion

1. Envoyer un message dans le chat
2. Arrêter le backend
3. Redémarrer le backend
4. Vérifier que le frontend se reconnecte automatiquement

### Test de canaux multiples

1. Ouvrir plusieurs onglets avec différentes fonctionnalités
2. Vérifier que chaque canal reçoit uniquement ses messages
3. Vérifier qu'il n'y a qu'une seule connexion WebSocket active

## Références

- [NiceGUI WebSocket](https://nicegui.io/documentation/web-socket)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [Architecture SoniqueBay](.kilocode/rules/memory-bank/00-architecture.md)
- [Conventions de développement](.kilocode/rules/memory-bank/01-conventions-dev.md)