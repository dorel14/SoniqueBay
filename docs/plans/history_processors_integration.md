# Plan d'intégration des History Processors pour la gestion du contexte conversationnel

## Contexte

La table `conversations` existe déjà (migration `add_conversation_model.py`) avec les champs suivants :
- `messages` (JSON) : Stockage de l'historique des messages
- `context` (JSON) : Contexte de la conversation
- `session_id` : Identifiant de session unique
- `last_intent`, `last_agent`, `mood` : Métadonnées de conversation

## Objectif

Intégrer les `history_processors` de pydantic-ai 1.56.0 pour optimiser la gestion du contexte conversationnel et améliorer les performances sur Raspberry Pi 4.

## Architecture proposée

### 1. Structure des History Processors

```python
# backend/ai/utils/history_processors.py
from typing import List, Callable, Any
from pydantic_ai.messages import Message

HistoryProcessor = Callable[[List[Message]], List[Message]]

class ConversationHistoryManager:
    """
    Gestionnaire des processors d'historique pour optimiser le contexte LLM.
    """
    
    @staticmethod
    def limit_context_size(max_messages: int = 10) -> HistoryProcessor:
        """
        Limite le nombre de messages dans le contexte.
        Garde les messages les plus récents.
        """
        def processor(messages: List[Message]) -> List[Message]:
            if len(messages) <= max_messages:
                return messages
            return messages[-max_messages:]
        return processor
    
    @staticmethod
    def summarize_old_messages(threshold: int = 5) -> HistoryProcessor:
        """
        Résume les messages anciens quand le contexte dépasse un seuil.
        À implémenter avec un appel LLM pour condensation.
        """
        def processor(messages: List[Message]) -> List[Message]:
            if len(messages) <= threshold:
                return messages
            # TODO: Implémenter la logique de résumé
            # - Garder les 2 derniers messages complets
            # - Résumer les messages plus anciens
            return messages
        return processor
    
    @staticmethod
    def filter_system_messages() -> HistoryProcessor:
        """
        Filtre ou condense les messages système redondants.
        """
        def processor(messages: List[Message]) -> List[Message]:
            # Garder uniquement le dernier message système
            system_msgs = [m for m in messages if m.role == 'system']
            other_msgs = [m for m in messages if m.role != 'system']
            
            if system_msgs:
                return [system_msgs[-1]] + other_msgs
            return messages
        return processor
    
    @staticmethod
    def prioritize_recent_context(window_size: int = 3) -> HistoryProcessor:
        """
        Donne plus de poids/priorité aux messages récents.
        Peut ajouter des marqueurs de priorité dans les métadonnées.
        """
        def processor(messages: List[Message]) -> List[Message]:
            # Marquer les messages récents comme "high_priority"
            for i, msg in enumerate(messages):
                if i >= len(messages) - window_size:
                    msg.metadata = msg.metadata or {}
                    msg.metadata['priority'] = 'high'
            return messages
        return processor
```

### 2. Intégration avec le modèle Conversation

```python
# backend/api/models/conversation_model.py (existant)
class ConversationModel:
    # ... champs existants ...
    
    def get_history_processors(self) -> List[HistoryProcessor]:
        """
        Retourne les processors adaptés selon l'état de la conversation.
        """
        processors = []
        
        # Si conversation longue, activer le résumé
        if len(self.messages) > 20:
            processors.append(
                ConversationHistoryManager.summarize_old_messages(threshold=10)
            )
        
        # Toujours limiter la taille du contexte pour RPi4
        processors.append(
            ConversationHistoryManager.limit_context_size(max_messages=15)
        )
        
        # Filtrer les messages système redondants
        processors.append(
            ConversationHistoryManager.filter_system_messages()
        )
        
        return processors
    
    def to_pydantic_messages(self) -> List[Message]:
        """
        Convertit les messages JSON en objets Message pydantic-ai.
        """
        return [
            Message(
                role=msg['role'],
                content=msg['content'],
                timestamp=msg.get('timestamp'),
                metadata=msg.get('metadata', {})
            )
            for msg in self.messages
        ]
```

### 3. Modification du Agent Builder

```python
# backend/ai/agents/builder.py

async def build_agent(
    agent_model: AgentModel,
    conversation: Optional[ConversationModel] = None  # Nouveau paramètre
) -> Agent:
    """
    Construit un agent avec gestion optimisée de l'historique.
    """
    # ... code existant ...
    
    # Configuration des history processors si conversation fournie
    history_processors = None
    if conversation:
        history_processors = conversation.get_history_processors()
    
    agent = Agent(
        name=agent_model.name,
        model=ollama_model,
        system_prompt=system_prompt,
        tools=tools,
        retries=5,
        output_type=str,
        history_processors=history_processors,  # NOUVEAU
    )
    
    return agent
```

### 4. Service de gestion des conversations

```python
# backend/ai/services/conversation_service.py

class ConversationService:
    """
    Service pour gérer les conversations avec optimisation du contexte.
    """
    
    @staticmethod
    async def get_or_create_conversation(session_id: str) -> ConversationModel:
        """
        Récupère ou crée une conversation par session_id.
        """
        # Implémentation avec SQLAlchemy
        pass
    
    @staticmethod
    async def add_message(
        conversation_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Ajoute un message à la conversation avec validation.
        """
        # Vérifier la taille avant ajout
        # Déclencher le résumé si nécessaire
        pass
    
    @staticmethod
    async def compress_conversation(conversation_id: int) -> None:
        """
        Compresse l'historique quand il devient trop long.
        Utilise un LLM pour créer un résumé.
        """
        # TODO: Implémenter la compression intelligente
        pass
```

## Plan de mise en œuvre

### Phase 1 : Infrastructure (1-2 jours)
1. [ ] Créer `backend/ai/utils/history_processors.py`
2. [ ] Ajouter les tests unitaires pour les processors
3. [ ] Créer `backend/ai/services/conversation_service.py`

### Phase 2 : Intégration (2-3 jours)
1. [ ] Modifier `build_agent()` pour accepter une conversation
2. [ ] Mettre à jour `ConversationModel` avec les méthodes utilitaires
3. [ ] Intégrer dans le WebSocket `/ws/chat`

### Phase 3 : Optimisation (1-2 jours)
1. [ ] Implémenter le résumé automatique avec LLM
2. [ ] Ajouter des métriques de performance (taille du contexte, temps de traitement)
3. [ ] Tests de charge sur RPi4

### Phase 4 : Documentation (1 jour)
1. [ ] Documenter l'API des conversations
2. [ ] Créer des exemples d'utilisation
3. [ ] Mise à jour du guide de déploiement RPi4

## Considérations pour RPi4

| Aspect | Stratégie |
|--------|-----------|
| Mémoire | Limiter à 10-15 messages maximum |
| CPU | Résumé asynchrone en tâche de fond |
| Stockage | Compression JSON des anciens messages |
| Latence | Cache des conversations actives en Redis |

## Fichiers à modifier/créer

### Nouveaux fichiers
- `backend/ai/utils/history_processors.py`
- `backend/ai/services/conversation_service.py`
- `tests/unit/ai/test_history_processors.py`

### Fichiers à modifier
- `backend/ai/agents/builder.py` (ajouter paramètre conversation)
- `backend/api/models/conversation_model.py` (ajouter méthodes)
- `backend/api/routers/ws_ai.py` (intégrer le service)

## Notes de mise en garde

1. **Compatibilité** : Les `history_processors` sont disponibles depuis pydantic-ai 0.0.20+
2. **Migration** : Pas de migration DB nécessaire (utilise la table existante)
3. **Rollback** : Facile à désactiver (paramètre optionnel)
4. **Tests** : Nécessite des tests avec données réelles de conversation

## Prochaines étapes immédiates

1. Valider ce plan avec l'équipe
2. Créer une branche feature/history-processors
3. Commencer par l'implémentation basique (limit_context_size)
4. Tester sur environnement de dev avant RPi4

---

**Date de création** : 2025-02-28  
**Priorité** : Moyenne (optimisation)  
**Estimation** : 5-7 jours de développement
