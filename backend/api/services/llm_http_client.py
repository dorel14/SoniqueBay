"""
Client HTTPX partagé pour les connexions LLM.

Ce module fournit un singleton AsyncClient optimisé pour les connexions
LLM longues avec KoboldCpp. Le client est configuré avec des paramètres
keep-alive pour maintenir une connexion persistante entre les requêtes.

Usage:
    from backend.api.services.llm_http_client import get_llm_http_client
    
    client = get_llm_http_client()
    response = await client.post(...)
"""
import httpx
from typing import Optional
from backend.api.utils.logging import logger

# Singleton instance
_llm_http_client: Optional[httpx.AsyncClient] = None


def get_llm_http_client() -> httpx.AsyncClient:
    """
    Récupère l'instance singleton du client HTTPX pour les connexions LLM.
    
    Le client est configuré avec :
    - Timeouts adaptés aux requêtes LLM longues
    - Keep-alive activé pour maintenir les connexions ouvertes
    - Pool de connexions limité pour RPi4
    
    Returns:
        httpx.AsyncClient: Client HTTPX configuré et partagé
    """
    global _llm_http_client
    
    if _llm_http_client is None:
        _llm_http_client = _create_llm_http_client()
        logger.info(
            "[LLM_HTTP_CLIENT] Client HTTPX partagé initialisé avec keep-alive"
        )
    
    return _llm_http_client


def _create_llm_http_client() -> httpx.AsyncClient:
    """
    Crée un nouveau client HTTPX optimisé pour les connexions LLM.
    
    Configuration optimisée pour KoboldCpp :
    - Connect timeout: 10s (temps pour établir la connexion TCP)
    - Read timeout: None (pas de limite, réponses LLM peuvent être longues)
    - Write timeout: 30s (temps pour envoyer le payload)
    - Pool timeout: 10s (temps d'attente d'une connexion du pool)
    - Keep-alive: 300s (maintient les connexions ouvertes 5 minutes)
    - Max connections: 10 (limité pour RPi4)
    - Max keepalive connections: 5
    
    Returns:
        httpx.AsyncClient: Client configuré
    """
    # Configuration des timeouts pour les requêtes LLM
    timeout = httpx.Timeout(
        connect=10.0,      # Temps pour établir la connexion TCP
        read=None,         # Pas de timeout de lecture (réponses LLM longues)
        write=30.0,        # Temps pour envoyer le payload
        pool=10.0,         # Temps d'attente d'une connexion du pool
    )
    
    # Configuration des limites de connexion
    limits = httpx.Limits(
        max_connections=10,              # Maximum total de connexions
        max_keepalive_connections=5,     # Connexions keep-alive maintenues ouvertes
        keepalive_expiry=300.0,        # Garder les connexions ouvertes 5 minutes
    )
    
    # Headers par défaut pour keep-alive
    headers = {
        "Connection": "keep-alive",
        "Keep-Alive": "timeout=300, max=1000",
    }
    
    client = httpx.AsyncClient(
        timeout=timeout,
        limits=limits,
        headers=headers,
        http2=False,  # HTTP/1.1 avec keep-alive est plus stable pour LLM
    )
    
    logger.debug(
        f"[LLM_HTTP_CLIENT] Configuration: timeout={timeout}, "
        f"limits={limits}, keepalive_expiry=300s"
    )
    
    return client


async def close_llm_http_client() -> None:
    """
    Ferme proprement le client HTTPX partagé.
    
    À appeler lors de l'arrêt de l'application pour libérer les ressources.
    """
    global _llm_http_client
    
    if _llm_http_client is not None:
        await _llm_http_client.aclose()
        _llm_http_client = None
        logger.info("[LLM_HTTP_CLIENT] Client HTTPX fermé proprement")


def reset_llm_http_client() -> httpx.AsyncClient:
    """
    Réinitialise le client HTTPX (ferme l'ancien et crée un nouveau).
    
    Utile en cas de problèmes de connexion persistante.
    
    Returns:
        httpx.AsyncClient: Nouveau client HTTPX
    """
    global _llm_http_client
    
    if _llm_http_client is not None:
        # Fermeture asynchrone dans un contexte synchrone
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si on est dans un event loop, créer une tâche
                loop.create_task(_llm_http_client.aclose())
            else:
                loop.run_until_complete(_llm_http_client.aclose())
        except Exception as e:
            logger.warning(f"[LLM_HTTP_CLIENT] Erreur fermeture ancien client: {e}")
        
        _llm_http_client = None
    
    return get_llm_http_client()
