# context_manager.py
# Gestion de l'état conversationnel pour l'orchestrateur SoniqueBay

from typing import List, Dict, Any


class ConversationContext:
    """
    Stocke le contexte de la conversation et l'état utilisateur :
    - messages échangés
    - humeur / mood
    - dernière intention
    - historique des actions
    """

    def __init__(self):
        self.messages: List[Dict[str, str]] = []  # [{'user': '...', 'agent': '...'}]
        self.mood: str | None = None
        self.last_intent: str | None = None
        self.action_history: List[Dict[str, Any]] = []  # {'action':..., 'params':..., 'result':...}

    # --- Gestion des messages -------------------------------------
    def add_user_message(self, message: str):
        self.messages.append({'user': message})

    def add_agent_message(self, agent_name: str, message: str):
        self.messages.append({'agent': agent_name, 'message': message})

    def get_last_user_message(self) -> str | None:
        for msg in reversed(self.messages):
            if 'user' in msg:
                return msg['user']
        return None

    # --- Gestion du mood -----------------------------------------
    def set_mood(self, mood: str):
        self.mood = mood

    def get_mood(self) -> str | None:
        return self.mood

    # --- Gestion des actions --------------------------------------
    def add_action(self, action: str, params: Dict[str, Any], result: Any):
        self.action_history.append({
            'action': action,
            'params': params,
            'result': result
        })

    def get_last_action(self) -> Dict[str, Any] | None:
        if self.action_history:
            return self.action_history[-1]
        return None

    # --- Nettoyage / reset ---------------------------------------
    def reset(self):
        self.messages.clear()
        self.mood = None
        self.last_intent = None
        self.action_history.clear()