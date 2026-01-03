from typing import Any, Dict, List, Optional, Callable, TypeVar, ParamSpec
import functools
import inspect
import time
from datetime import datetime

from backend.api.utils.logging import logger
from backend.ai.utils.registry import ToolRegistry


P = ParamSpec('P')
R = TypeVar('R')


def ai_tool(
    name: str,
    description: str,
    allowed_agents: Optional[List[str]] = None,
    requires_session: bool = False,
    timeout: Optional[int] = None,
    tags: Optional[List[str]] = None,
    category: str = "general",
    version: str = "1.0",
    validate_params: bool = True,
    track_usage: bool = True,
):
    """
    Décorateur optimisé pour définir un tool IA avec sécurité et métadonnées.
    
    Args:
        name: Nom unique du tool
        description: Description du tool
        allowed_agents: Liste des agents autorisés à utiliser ce tool
        requires_session: Indique si le tool nécessite une session de base de données
        timeout: Timeout d'exécution en secondes
        tags: Tags pour catégoriser le tool
        category: Catégorie du tool (search, playlist, music, etc.)
        version: Version du tool
        validate_params: Active la validation des paramètres d'entrée
        track_usage: Active le tracking de l'utilisation du tool
        
    Example:
        @ai_tool(
            name="search_tracks",
            description="Recherche des pistes musicales",
            allowed_agents=["search_agent", "playlist_agent"],
            timeout=30,
            category="search",
            tags=["music", "search"]
        )
        async def search_tracks(query: str, session: AsyncSession):
            # Implementation
            pass
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Validation des paramètres du décorateur
        if not name or not isinstance(name, str):
            raise ValueError("Le nom du tool doit être une chaîne non vide")
        
        if not description or not isinstance(description, str):
            raise ValueError("La description doit être une chaîne non vide")
        
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            raise ValueError("Le timeout doit être un entier positif")
        
        if allowed_agents is not None:
            if not isinstance(allowed_agents, list):
                raise ValueError("allowed_agents doit être une liste")
            for agent in allowed_agents:
                if not isinstance(agent, str) or not agent.strip():
                    raise ValueError("Les noms d'agents doivent être des chaînes non vides")
        
        if tags is not None and not isinstance(tags, list):
            raise ValueError("tags doit être une liste")
        
        if not isinstance(category, str) or not category.strip():
            raise ValueError("La catégorie doit être une chaîne non vide")
        
        if not isinstance(version, str) or not version.strip():
            raise ValueError("La version doit être une chaîne non vide")
        
        # Enregistrement dans le registry
        ToolRegistry.register(
            name=name,
            description=description,
            func=func,
            allowed_agents=allowed_agents,
            requires_session=requires_session,
            timeout=timeout,
            tags=tags,
            category=category,
            version=version,
        )
        
        # Ajout de métadonnées enrichies à la fonction
        func._ai_tool_metadata = {
            "name": name,
            "description": description,
            "allowed_agents": allowed_agents or [],
            "requires_session": requires_session,
            "timeout": timeout,
            "tags": tags or [],
            "category": category,
            "version": version,
            "validate_params": validate_params,
            "track_usage": track_usage,
            "created_at": datetime.utcnow().isoformat(),
            "function_signature": str(inspect.signature(func)),
            "is_async": inspect.iscoroutinefunction(func),
        }
        
        # Fonction wrapper pour validation et monitoring
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            agent_name = kwargs.get('agent_name')
            
            try:
                # Validation de session si nécessaire
                if requires_session:
                    _validate_session_parameter(func, args, kwargs)
                
                # Validation des paramètres d'entrée
                if validate_params:
                    _validate_function_parameters(func, args, kwargs)
                
                # Exécution avec monitoring
                result = ToolRegistry.execute_with_monitoring(
                    tool_name=name,
                    func=func,
                    agent_name=agent_name,
                    *args,
                    **kwargs
                )
                
                # Tracking de l'utilisation
                if track_usage:
                    _track_tool_usage(name, agent_name, start_time, success=True)
                
                return result
                
            except Exception as e:
                # Tracking des erreurs
                if track_usage:
                    _track_tool_usage(name, agent_name, start_time, success=False, error=str(e))
                
                logger.error(
                    f"Erreur lors de l'exécution du tool {name}",
                    extra={
                        "tool_name": name,
                        "agent_name": agent_name,
                        "error": str(e),
                        "function": func.__name__,
                    },
                    exc_info=True
                )
                raise
        
        # Version async du wrapper
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()
            agent_name = kwargs.get('agent_name')
            
            try:
                # Validation de session si nécessaire
                if requires_session:
                    _validate_session_parameter(func, args, kwargs)
                
                # Validation des paramètres d'entrée
                if validate_params:
                    _validate_function_parameters(func, args, kwargs)
                
                # Exécution avec monitoring
                result = await ToolRegistry.execute_with_monitoring(
                    tool_name=name,
                    func=func,
                    agent_name=agent_name,
                    *args,
                    **kwargs
                )
                
                # Tracking de l'utilisation
                if track_usage:
                    _track_tool_usage(name, agent_name, start_time, success=True)
                
                return result
                
            except Exception as e:
                # Tracking des erreurs
                if track_usage:
                    _track_tool_usage(name, agent_name, start_time, success=False, error=str(e))
                
                logger.error(
                    f"Erreur lors de l'exécution du tool {name}",
                    extra={
                        "tool_name": name,
                        "agent_name": agent_name,
                        "error": str(e),
                        "function": func.__name__,
                    },
                    exc_info=True
                )
                raise
        
        # Retourner la version appropriée (sync ou async)
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return wrapper  # type: ignore
    
    return decorator


def _validate_session_parameter(func: Callable, args: tuple, kwargs: dict) -> None:
    """Valide que la session est présente dans les paramètres."""
    sig = inspect.signature(func)
    
    # Vérifier si 'session' est dans les paramètres nommés
    if 'session' in kwargs:
        return
    
    # Vérifier si 'session' est dans les paramètres positionnels
    param_names = list(sig.parameters.keys())
    for i, param_name in enumerate(param_names):
        if param_name == 'session' and i < len(args):
            return
    
    raise ValueError(f"Le tool '{func._ai_tool_metadata['name']}' nécessite une session de base de données")


def _validate_function_parameters(func: Callable, args: tuple, kwargs: dict) -> None:
    """Valide les paramètres d'entrée selon la signature de la fonction."""
    try:
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Validation basique des types (si annotations présentes)
        for param_name, param_value in bound_args.arguments.items():
            param = sig.parameters[param_name]
            if param.annotation != inspect.Parameter.empty:
                expected_type = param.annotation
                if not isinstance(param_value, expected_type):
                    logger.warning(
                        f"Type mismatch for parameter '{param_name}' in tool '{func._ai_tool_metadata['name']}'",
                        extra={
                            "expected_type": expected_type.__name__,
                            "actual_type": type(param_value).__name__,
                            "value": str(param_value)[:100]  # Limiter la longueur du log
                        }
                    )
    except Exception as e:
        logger.warning(
            f"Échec de la validation des paramètres pour le tool '{func._ai_tool_metadata['name']}'",
            extra={"error": str(e)}
        )


def _track_tool_usage(tool_name: str, agent_name: Optional[str], start_time: float, success: bool, error: Optional[str] = None) -> None:
    """Track l'utilisation du tool pour les statistiques."""
    execution_time = time.time() - start_time
    
    logger.info(
        f"Tool exécuté: {tool_name}",
        extra={
            "tool_name": tool_name,
            "agent_name": agent_name,
            "execution_time": execution_time,
            "success": success,
            "error": error,
        }
    )


# Décorateur spécialisé pour les tools de recherche
def search_tool(
    name: str,
    description: str,
    allowed_agents: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    **kwargs
):
    """Décorateur spécialisé pour les tools de recherche."""
    return ai_tool(
        name=name,
        description=description,
        allowed_agents=allowed_agents or ["search_agent"],
        timeout=timeout or 30,
        category="search",
        tags=["search", "music"],
        **kwargs
    )


# Décorateur spécialisé pour les tools de playlist
def playlist_tool(
    name: str,
    description: str,
    allowed_agents: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    **kwargs
):
    """Décorateur spécialisé pour les tools de playlist."""
    return ai_tool(
        name=name,
        description=description,
        allowed_agents=allowed_agents or ["playlist_agent"],
        timeout=timeout or 60,
        category="playlist",
        tags=["playlist", "music"],
        **kwargs
    )


# Décorateur spécialisé pour les tools musicaux
def music_tool(
    name: str,
    description: str,
    allowed_agents: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    **kwargs
):
    """Décorateur spécialisé pour les tools musicaux."""
    return ai_tool(
        name=name,
        description=description,
        allowed_agents=allowed_agents or ["search_agent", "playlist_agent"],
        timeout=timeout or 45,
        category="music",
        tags=["music", "library"],
        **kwargs
    )


# Fonction utilitaire pour obtenir les métadonnées d'un tool
def get_tool_metadata(func: Callable) -> Optional[Dict[str, Any]]:
    """Récupère les métadonnées d'un tool décoré."""
    return getattr(func, '_ai_tool_metadata', None)


# Fonction utilitaire pour valider les paramètres d'un tool
def validate_tool_parameters(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Valide les paramètres d'un tool selon sa signature."""
    import inspect
    
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    return dict(bound_args.arguments)
