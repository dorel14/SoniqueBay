import os
from backend.api.services.llm_service import LLMService


class OllamaService:
    """
    Service Ollama - utilise maintenant le service LLM unifié.
    Maintient la compatibilité avec l'ancienne API.
    """
    
    def __init__(self, url: str = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')):
        self.model_list = []
        self.url = url
        # Utilise le service LLM unifié avec auto-détection
        self.llm_service = LLMService()

    def get_model_list(self):
        """
        Récupère la liste des modèles disponibles via le service LLM unifié.
        Supporte Ollama et KoboldCPP.
        """
        result = self.llm_service.get_model_list()
        self.model_list = result.get("models", [])
        return self.model_list
        
    def health_check(self):
        """
        Vérifie la santé du service LLM.
        """
        return self.llm_service.health_check()
