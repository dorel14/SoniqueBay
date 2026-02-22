"""
Service LLM unifié pour SoniqueBay.
Gère l'accès aux modèles LLM via Ollama ou KoboldCPP.
Fournit une interface commune pour les différents fournisseurs de LLM.

Auteur: SoniqueBay Team
"""
import os
import requests
from typing import Optional, Dict, Any, List
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.ollama import OllamaProvider
from backend.api.utils.logging import logger


class LLMService:
    """
    Service unifié pour l'accès aux modèles LLM (Ollama et KoboldCPP).
    Fournit une interface commune pour les différents fournisseurs de LLM.
    """

    def __init__(self, provider_type: str = None):
        """
        Initialise le service LLM avec le fournisseur spécifié.
        
        Args:
            provider_type: Type de fournisseur ('ollama', 'koboldcpp', ou None pour auto-détection)
        """
        # Configuration par défaut
        self.provider_type = provider_type or os.getenv('LLM_PROVIDER', 'auto')
        self.base_url = os.getenv('LLM_BASE_URL', None)
        self.default_model = os.getenv('AGENT_MODEL', 'Qwen/Qwen3-4B-Instruct:Q3_K_M')
        
        # Auto-détection du fournisseur si nécessaire
        if self.provider_type == 'auto':
            self._auto_detect_provider()
        
        # Configuration des URLs par défaut selon le fournisseur
        if not self.base_url:
            if self.provider_type == 'ollama':
                self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            elif self.provider_type == 'koboldcpp':
                self.base_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://localhost:11434')
        
        logger.info(f"[LLM] Service initialisé avec {self.provider_type} à {self.base_url}")

    def _auto_detect_provider(self):
        """
        Auto-détecte le fournisseur LLM disponible.
        Essaie d'abord KoboldCPP, puis Ollama.
        """
        # Essayer KoboldCPP
        try:
            kobold_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://localhost:11434')
            response = requests.get(f"{kobold_url}/v1/models", timeout=2)
            if response.status_code == 200:
                self.provider_type = 'koboldcpp'
                self.base_url = kobold_url
                logger.info(f"[LLM] KoboldCPP détecté à {kobold_url}")
                return
        except Exception as e:
            logger.debug(f"[LLM] KoboldCPP non détecté: {e}")
        
        # Essayer Ollama
        try:
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.provider_type = 'ollama'
                self.base_url = ollama_url
                logger.info(f"[LLM] Ollama détecté à {ollama_url}")
                return
        except Exception as e:
            logger.debug(f"[LLM] Ollama non détecté: {e}")
        
        # Fallback sur KoboldCPP (par défaut pour l'utilisateur)
        logger.warning("[LLM] Aucun fournisseur LLM détecté, fallback sur KoboldCPP")
        self.provider_type = 'koboldcpp'
        self.base_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://localhost:11434')

    def get_model(
        self,
        model_name: Optional[str] = None,
        num_ctx: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> OpenAIChatModel:
        """
        Récupère un modèle LLM configuré.
        
        Args:
            model_name: Nom du modèle (utilise le modèle par défaut si None)
            num_ctx: Taille du contexte
            temperature: Température de génération
            top_p: Valeur top_p pour la génération
            
        Returns:
            OpenAIChatModel configuré avec le bon fournisseur
        """
        model_name = model_name or self.default_model
        
        if self.provider_type == 'koboldcpp':
            # KoboldCPP utilise l'API OpenAI
            provider = OpenAIProvider(
                api_key="not-needed",  # KoboldCPP n'utilise pas d'API key
                base_url=f"{self.base_url}/v1"  # Endpoint OpenAI compatible
            )
            logger.debug(f"[LLM] Utilisation de KoboldCPP avec {model_name}")
        else:
            # Ollama par défaut
            provider = OllamaProvider(base_url=self.base_url)
            logger.debug(f"[LLM] Utilisation d'Ollama avec {model_name}")
        
        return OpenAIChatModel(
            model_name=model_name,
            provider=provider,
            max_context_length=num_ctx,
            temperature=temperature,
            top_p=top_p
        )

    def get_model_list(self) -> Dict[str, Any]:
        """
        Récupère la liste des modèles disponibles.
        
        Returns:
            Dict contenant la liste des modèles
        """
        try:
            if self.provider_type == 'koboldcpp':
                response = requests.get(f"{self.base_url}/v1/models", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Format compatible avec Ollama
                    models = []
                    for model in data.get("data", []):
                        models.append({
                            "name": model.get("id", "unknown"),
                            "model": model.get("id", "unknown"),
                            "size": 0,
                            "digest": "",
                            "details": {
                                "format": "gguf",
                                "family": model.get("id", "unknown").split("/")[0] if "/" in model.get("id", "") else "unknown",
                                "families": None,
                                "parameter_size": "",
                                "quantization_level": ""
                            }
                        })
                    return {"models": models}
            else:
                # Ollama par défaut
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {"models": data.get("models", [])}
        except Exception as e:
            logger.error(f"[LLM] Erreur récupération liste modèles: {e}")
        
        return {"models": []}

    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Génère une réponse de chat via l'API LLM.
        
        Args:
            messages: Liste de messages au format OpenAI
            model_name: Nom du modèle à utiliser
            temperature: Température de génération
            max_tokens: Nombre maximum de tokens
            stream: Si True, retourne un stream
            
        Returns:
            Réponse du modèle ou stream
        """
        model_name = model_name or self.default_model
        
        try:
            if self.provider_type == 'koboldcpp':
                # Utiliser l'API OpenAI de KoboldCPP
                url = f"{self.base_url}/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer not-needed"
                }
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": stream
                }
                
                response = requests.post(url, json=payload, headers=headers, timeout=60, stream=stream)
                response.raise_for_status()
                
                if stream:
                    return response  # Retourne l'objet response pour streaming
                else:
                    data = response.json()
                    return {
                        "content": data["choices"][0]["message"]["content"],
                        "model": data.get("model", model_name),
                        "usage": data.get("usage", {})
                    }
            else:
                # Ollama - utiliser l'API native
                url = f"{self.base_url}/api/chat"
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": stream,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                response = requests.post(url, json=payload, timeout=60, stream=stream)
                response.raise_for_status()
                
                if stream:
                    return response
                else:
                    data = response.json()
                    return {
                        "content": data["message"]["content"],
                        "model": data.get("model", model_name),
                        "usage": {}
                    }
                    
        except Exception as e:
            logger.error(f"[LLM] Erreur génération réponse: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Vérifie la santé du service LLM.
        
        Returns:
            Dict avec le statut de santé
        """
        try:
            if self.provider_type == 'koboldcpp':
                response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            else:
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": self.provider_type,
                    "base_url": self.base_url,
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": self.provider_type,
                    "base_url": self.base_url,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_type,
                "base_url": self.base_url,
                "error": str(e)
            }


# Instance globale du service LLM
llm_service = LLMService()
