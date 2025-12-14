# router.py
# Routeur d'intentions pour l'orchestrateur IA SoniqueBay

from typing import Optional

class IntentRouter:
    """
    Détermine l'intention en lisant les mots-clés depuis orchestrator.yaml.
    L'orchestrateur utilise déjà orchestrator.yaml pour la décision finale,
    mais ce routeur permet d'effectuer des décisions fallback ou personnalisées.
    """

    def __init__(self):
        self.intent_keywords = {}

    def load_intents(self, intents_cfg: dict):
        """
        Charge dynamiquement les intentions à partir du YAML orchestrator.
        """
        self.intent_keywords = {
            name: data.get("keywords", []) for name, data in intents_cfg.items()
        }

    def resolve_intent(self, message: str) -> Optional[str]:
        """
        Retourne une intention basée sur la présence de mots-clés.
        Si rien ne correspond → None (l'orchestrateur décidera).
        """
        msg = message.lower()

        for intent, keywords in self.intent_keywords.items():
            if any(kw.lower() in msg for kw in keywords):
                return intent

        return None

    def route_to(self, config: dict, intent: Optional[str]) -> str:
        """
        Donne le nom de l'agent associé à l'intention.
        Si aucune intention reconnue → fallback.
        """
        if intent and intent in config["intents"]:
            return config["intents"][intent]["route_to"]
        return config.get("fallback_agent", "search_agent")