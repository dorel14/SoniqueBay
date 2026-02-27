"""
Service LLM unifié pour SoniqueBay.
Gère l'accès aux modèles LLM via Ollama ou KoboldCPP.
Fournit une interface commune pour les différents fournisseurs de LLM.

Auteur: SoniqueBay Team
"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any, List
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.ollama import OllamaProvider
from backend.api.utils.logging import logger


# Singleton instance storage
_llm_service_instance: Optional['LLMService'] = None
_llm_service_lock: Optional[asyncio.Lock] = None


def _get_llm_lock() -> asyncio.Lock:
    """
    Lazy initialization de l'asyncio.Lock pour éviter les erreurs liées
    à la création du lock au moment de l'import du module.
    
    En Python 3.10+, créer un asyncio.Lock() au niveau du module
    (au moment de l'import) peut générer des warnings ou erreurs
    car le lock est lié à l'event loop existant à ce moment-là.
    
    Returns:
        asyncio.Lock: Instance du lock (lazy-initialized)
    """
    global _llm_service_lock
    if _llm_service_lock is None:
        # Vérifier si un event loop est en cours
        try:
            loop = asyncio.get_running_loop()
            # Créer le lock dans le contexte de l'event loop courant
            _llm_service_lock = asyncio.Lock()
            logger.debug("[LLM] asyncio.Lock créé avec event loop actif")
        except RuntimeError as e:
            # Pas d'event loop en cours - utiliser un lock factice ou
            # créer le lock plus tard lors du premier appel async
            logger.warning(f"[LLM] Pas d'event loop actif à l'initialisation du lock: {e}")
            # On crée quand même le lock - il sera fonctionnel quand usedans un context async
            _llm_service_lock = asyncio.Lock()
    return _llm_service_lock


class LLMService:
    """
    Service unifié pour l'accès aux modèles LLM (Ollama et KoboldCPP).
    Fournit une interface commune pour les différents fournisseurs de LLM.
    """

    def __init__(self, provider_type: str = None, lazy_init: bool = False):
        """
        Initialise le service LLM avec le fournisseur spécifié.
        
        Args:
            provider_type: Type de fournisseur ('ollama', 'koboldcpp', ou None pour auto-détection)
            lazy_init: Si True, diffère la détection du fournisseur à la première utilisation
        """
        # Configuration par défaut
        self.provider_type = provider_type or os.getenv('LLM_PROVIDER', 'auto')
        self.base_url = os.getenv('LLM_BASE_URL', None)
        self.default_model = os.getenv('AGENT_MODEL', 'Qwen/Qwen3-4B-Instruct:Q3_K_M')
        self._initialized = False
        # TODO(dev): En Docker, KOBOLDCPP_BASE_URL doit pointer vers le service Docker
        # (ex: http://llm-service:5001) et non vers localhost.
        # En développement local, http://localhost:11434 est correct.
        
        # Client HTTP persistant pour le connection pooling
        # Timeout par défaut de 120s pour les requêtes longues (streaming)
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.debug("[LLM] httpx.AsyncClient persistant initialisé")
        
        # Auto-détection du fournisseur si nécessaire (sauf en mode lazy)
        if self.provider_type == 'auto' and not lazy_init:
            self._auto_detect_provider()
            self._initialized = True
        
        # Configuration des URLs par défaut selon le fournisseur (si déjà connu)
        if not self.base_url and self.provider_type != 'auto':
            if self.provider_type == 'ollama':
                self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            elif self.provider_type == 'koboldcpp':
                # Défaut Docker : http://llm-service:5001 (nom du service Docker Compose)
                # Défaut local  : http://localhost:11434
                self.base_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://llm-service:5001')
        
        if self._initialized:
            logger.info(f"[LLM] Service initialisé avec {self.provider_type} à {self.base_url}")

    async def initialize(self):
        """
        Détecte explicitement le fournisseur et configure le service.
        À appeler avant la première utilisation si lazy_init=True.
        """
        if self._initialized:
            return
        
        if self.provider_type == 'auto':
            await self._auto_detect_provider()
        
        # Configuration des URLs par défaut selon le fournisseur
        if not self.base_url:
            if self.provider_type == 'ollama':
                self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            elif self.provider_type == 'koboldcpp':
                # Défaut Docker : http://llm-service:5001 (nom du service Docker Compose)
                # Défaut local  : http://localhost:11434
                self.base_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://llm-service:5001')
        
        self._initialized = True
        logger.info(
            f"[LLM] Service initialisé avec {self.provider_type} à {self.base_url}. "
            "Si une erreur de connexion survient, vérifiez que KOBOLDCPP_BASE_URL "
            "pointe vers le bon service (ex: http://llm-service:5001 en Docker)."
        )

    async def _auto_detect_provider(self):
        """
        Auto-détecte le fournisseur LLM disponible.
        Essaie d'abord KoboldCPP, puis Ollama.

        Note: En contexte Docker, les URLs doivent utiliser les noms de services
        (ex: http://llm-service:5001) et non localhost.
        """
        # Essayer KoboldCPP
        # Défaut Docker : http://llm-service:5001
        kobold_url = os.getenv('KOBOLDCPP_BASE_URL', 'http://llm-service:5001')
        try:
            response = await self._client.get(f"{kobold_url}/v1/models", timeout=2)
            if response.status_code == 200:
                self.provider_type = 'koboldcpp'
                self.base_url = kobold_url
                logger.info(f"[LLM] KoboldCPP détecté à {kobold_url}")
                return
        except Exception as e:
            logger.debug(
                f"[LLM] KoboldCPP non détecté à {kobold_url}: {e}. "
                "Vérifiez que KOBOLDCPP_BASE_URL est correct (Docker: http://llm-service:5001)."
            )

        # Essayer Ollama
        try:
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
            response = await self._client.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.provider_type = 'ollama'
                self.base_url = ollama_url
                logger.info(f"[LLM] Ollama détecté à {ollama_url}")
                return
        except Exception as e:
            logger.debug(f"[LLM] Ollama non détecté: {e}")

        # Fallback sur KoboldCPP (par défaut pour l'utilisateur)
        logger.warning(
            "[LLM] Aucun fournisseur LLM détecté automatiquement. "
            "Fallback sur KoboldCPP. "
            "Assurez-vous que KOBOLDCPP_BASE_URL est défini correctement "
            "(Docker: http://llm-service:5001, local: http://localhost:11434)."
        )
        self.provider_type = 'koboldcpp'
        self.base_url = kobold_url

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
            # KoboldCPP utilise l'API OpenAI-compatible
            # En Docker : base_url = http://llm-service:5001/v1
            # En local  : base_url = http://localhost:11434/v1
            provider = OpenAIProvider(
                api_key="not-needed",  # KoboldCPP n'utilise pas d'API key
                base_url=f"{self.base_url}/v1"  # Endpoint OpenAI compatible
            )
            logger.debug(f"[LLM] Utilisation de KoboldCPP avec modèle={model_name} url={self.base_url}/v1")
        else:
            # Ollama par défaut
            provider = OllamaProvider(base_url=self.base_url)
            logger.debug(f"[LLM] Utilisation d'Ollama avec modèle={model_name} url={self.base_url}")
        
        return OpenAIChatModel(
            model_name=model_name,
            provider=provider
        )

    async def get_model_list(self) -> Dict[str, Any]:
        """
        Récupère la liste des modèles disponibles.
        
        Returns:
            Dict contenant la liste des modèles
        """
        try:
            if self.provider_type == 'koboldcpp':
                response = await self._client.get(f"{self.base_url}/v1/models", timeout=5)
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
                response = await self._client.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {"models": data.get("models", [])}
        except Exception as e:
            logger.error(f"[LLM] Erreur récupération liste modèles: {e}")
        
        return {"models": []}

    async def _stream_chat_response(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ):
        """
        Génère une réponse de chat en streaming via l'API LLM.
        Yields les chunks de texte au fur et à mesure de leur génération.
        
        Args:
            messages: Liste de messages au format OpenAI
            model_name: Nom du modèle à utiliser
            temperature: Température de génération
            max_tokens: Nombre maximum de tokens
            
        Yields:
            Chunks de texte (str) au fur et à mesure
        """
        import json
        model_name = model_name or self.default_model
        
        logger.debug(f"[LLM] Démarrage du streaming avec {self.provider_type} sur {self.base_url}")
        
        try:
            if self.provider_type == 'koboldcpp':
                # Utiliser l'API OpenAI de KoboldCPP avec streaming
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
                    "stream": True
                }
                
                # Utiliser le client persistant pour le connection pooling
                async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    
                    logger.debug(f"[LLM] Connexion SSE établie, début du streaming")
                    
                    # Utiliser aiter_lines() pour le streaming asynchrone non-bloquant
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                            
                        # Gestion des lignes de données SSE
                        if line.startswith('data: '):
                            data_str = line[6:]  # Enlever 'data: '
                            
                            # Détection de la fin du stream SSE
                            if data_str.strip() == '[DONE]':
                                logger.debug("[LLM] Fin du stream SSE détectée ([DONE])")
                                break
                            
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                # Ligne non-JSON, ignorer silencieusement
                                continue
                            except (KeyError, AttributeError):
                                continue
                        elif line.startswith(':'):
                            # Commentaire SSE (heartbeat), ignorer
                            continue
                            
                logger.debug("[LLM] Streaming SSE terminé proprement")
                
            else:
                # Ollama - utiliser l'API native avec streaming
                url = f"{self.base_url}/api/chat"
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                # Utiliser le client persistant pour le connection pooling
                async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    
                    logger.debug(f"[LLM] Connexion Ollama établie, début du streaming")
                    
                    # Utiliser aiter_lines() pour le streaming asynchrone non-bloquant
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                            
                        try:
                            data = json.loads(line)
                            if 'message' in data:
                                content = data['message'].get('content', '')
                                if content:
                                    yield content
                            # Ollama envoie aussi un champ 'done' à la fin
                            if data.get('done', False):
                                logger.debug("[LLM] Fin du stream Ollama détectée (done=true)")
                                break
                        except json.JSONDecodeError:
                            continue
                        except (KeyError, AttributeError):
                            continue
                            
                logger.debug("[LLM] Streaming Ollama terminé proprement")
                    
        except Exception as e:
            logger.error(f"[LLM] Erreur streaming réponse: {e}", exc_info=True)
            raise

    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ):
        """
        Génère une réponse de chat via l'API LLM.
        
        Args:
            messages: Liste de messages au format OpenAI
            model_name: Nom du modèle à utiliser
            temperature: Température de génération
            max_tokens: Nombre maximum de tokens
            stream: Si True, retourne un async iterator pour le streaming
            
        Returns:
            Dict avec la réponse complète si stream=False,
            AsyncIterator yieldant des chunks de texte si stream=True
        """
        model_name = model_name or self.default_model
        
        if stream:
            # Retourner l'async iterator pour le streaming
            return self._stream_chat_response(
                messages=messages,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        # Mode non-streaming : récupérer la réponse complète
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
                    "stream": False
                }
                
                response = await self._client.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", model_name),
                    "usage": data.get("usage", {})
                }
            else:
                # Ollama - utiliser l'API native
                url = f"{self.base_url}/api/chat"
                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                response = await self._client.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                return {
                    "content": data["message"]["content"],
                    "model": data.get("model", model_name),
                    "usage": {}
                }
                    
        except Exception as e:
            logger.error(f"[LLM] Erreur génération réponse: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie la santé du service LLM.
        
        Returns:
            Dict avec le statut de santé
        """
        import time
        start_time = time.time()
        try:
            if self.provider_type == 'koboldcpp':
                response = await self._client.get(f"{self.base_url}/v1/models", timeout=5)
            else:
                response = await self._client.get(f"{self.base_url}/api/tags", timeout=5)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": self.provider_type,
                    "base_url": self.base_url,
                    "response_time_ms": elapsed_ms
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


async def get_llm_service() -> LLMService:
    """
    Récupère l'instance singleton du service LLM avec lazy initialization.
    
    Cette fonction garantit que:
    1. L'import du module ne déclenche pas d'appels HTTP bloquants
    2. La détection du fournisseur est faite au premier appel
    3. L'instance est réutilisée pour les appels suivants (thread-safe)
    
    Returns:
        LLMService: Instance initialisée du service LLM
    """
    global _llm_service_instance
    
    # Utiliser le lock lazy-initialisé
    lock = _get_llm_lock()
    
    if _llm_service_instance is None:
        async with lock:
            # Double-check pattern pour éviter les race conditions
            if _llm_service_instance is None:
                _llm_service_instance = LLMService(lazy_init=True)
                await _llm_service_instance.initialize()
    
    return _llm_service_instance


def get_llm_service_sync() -> LLMService:
    """
    Version synchrone pour les contextes non-async (ex: imports au niveau module).
    Crée une instance avec lazy_init=True sans l'initialiser.
    L'initialisation sera faite lors du premier appel effectif.
    
    Returns:
        LLMService: Instance du service LLM (non initialisée jusqu'au premier usage)
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        _llm_service_instance = LLMService(lazy_init=True)
        # Note: L'initialisation est différée. Pour un usage immédiat, appeler initialize()
    
    return _llm_service_instance


# Pour compatibilité ascendante - sera supprimé après migration complète
# Déprécié: Utiliser get_llm_service() ou get_llm_service_sync() à la place
llm_service = get_llm_service_sync()
