from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio
import functools
import inspect
import time

from backend.api.utils.logging import logger


class AIToolMetadata:
    """Métadonnées enrichies pour un tool IA."""
    
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        allowed_agents: Optional[List[str]] = None,
        requires_session: bool = False,
        timeout: Optional[int] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        version: str = "1.0",
        validate_params: bool = True,
        track_usage: bool = True,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.allowed_agents = allowed_agents or []
        self.requires_session = requires_session
        self.timeout = timeout
        self.tags = tags or []
        self.category = category or "general"
        self.version = version
        self.validate_params = validate_params
        self.track_usage = track_usage
        self.created_at = datetime.utcnow()
        self.call_count = 0
        self.error_count = 0
        self.success_count = 0
        self.avg_execution_time = 0.0
        self.total_execution_time = 0.0
        self.min_execution_time = float('inf')
        self.max_execution_time = 0.0
        self.function_signature = str(inspect.signature(func))
        self.is_async = inspect.iscoroutinefunction(func)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit les métadonnées en dictionnaire."""
        return {
            "name": self.name,
            "description": self.description,
            "allowed_agents": self.allowed_agents,
            "requires_session": self.requires_session,
            "timeout": self.timeout,
            "tags": self.tags,
            "category": self.category,
            "version": self.version,
            "validate_params": self.validate_params,
            "track_usage": self.track_usage,
            "created_at": self.created_at.isoformat(),
            "call_count": self.call_count,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "avg_execution_time": self.avg_execution_time,
            "total_execution_time": self.total_execution_time,
            "min_execution_time": self.min_execution_time if self.min_execution_time != float('inf') else 0.0,
            "max_execution_time": self.max_execution_time,
            "function_signature": self.function_signature,
            "is_async": self.is_async,
            "success_rate": self.success_count / max(1, self.call_count),
        }

    def update_stats(self, execution_time: float, success: bool) -> None:
        """Met à jour les statistiques d'exécution."""
        self.call_count += 1
        self.total_execution_time += execution_time
        
        if execution_time < self.min_execution_time:
            self.min_execution_time = execution_time
        if execution_time > self.max_execution_time:
            self.max_execution_time = execution_time
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        
        # Mise à jour de la moyenne pondérée
        self.avg_execution_time = self.total_execution_time / self.call_count


class ToolRegistry:
    """Registry amélioré pour les tools IA avec sécurité et métadonnées avancées."""
    
    _tools: Dict[str, AIToolMetadata] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        func: Callable,
        allowed_agents: Optional[List[str]] = None,
        requires_session: bool = False,
        timeout: Optional[int] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        version: str = "1.0",
        validate_params: bool = True,
        track_usage: bool = True,
    ) -> None:
        """Enregistre un tool avec ses métadonnées enrichies."""
        
        # Vérification de non-doublon
        if name in cls._tools:
            logger.warning(f"Tool '{name}' déjà enregistré, mise à jour des métadonnées")
        
        metadata = AIToolMetadata(
            name=name,
            description=description,
            func=func,
            allowed_agents=allowed_agents,
            requires_session=requires_session,
            timeout=timeout,
            tags=tags,
            category=category,
            version=version,
            validate_params=validate_params,
            track_usage=track_usage,
        )
        
        cls._tools[name] = metadata
        
        logger.info(
            f"Tool enregistré: {name}",
            extra={
                "tool_name": name,
                "category": category,
                "allowed_agents": allowed_agents,
                "timeout": timeout,
                "version": version,
                "is_async": metadata.is_async,
            }
        )

    @classmethod
    def get(cls, name: str) -> Optional[AIToolMetadata]:
        """Récupère les métadonnées d'un tool."""
        return cls._tools.get(name)

    @classmethod
    def all(cls) -> Dict[str, AIToolMetadata]:
        """Retourne tous les tools enregistrés."""
        return cls._tools.copy()

    @classmethod
    def get_by_category(cls, category: str) -> Dict[str, AIToolMetadata]:
        """Retourne les tools d'une catégorie."""
        return {name: tool for name, tool in cls._tools.items() if tool.category == category}

    @classmethod
    def get_by_agent(cls, agent_name: str) -> Dict[str, AIToolMetadata]:
        """Retourne les tools autorisés pour un agent."""
        return {
            name: tool
            for name, tool in cls._tools.items()
            if not tool.allowed_agents or agent_name in tool.allowed_agents
        }

    @classmethod
    def get_by_tags(cls, tags: List[str]) -> Dict[str, AIToolMetadata]:
        """Retourne les tools contenant certains tags."""
        return {
            name: tool
            for name, tool in cls._tools.items()
            if any(tag in tool.tags for tag in tags)
        }

    @classmethod
    def validate_access(cls, tool_name: str, agent_name: str) -> bool:
        """Valide si un agent peut accéder à un tool."""
        tool = cls._tools.get(tool_name)
        if not tool:
            return False
        
        # Si pas de restriction d'agents, accès libre
        if not tool.allowed_agents:
            return True
        
        return agent_name in tool.allowed_agents

    @classmethod
    def execute_with_monitoring(
        cls,
        tool_name: str,
        func: Callable,
        agent_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """Exécute un tool avec monitoring avancé des performances."""
        tool = cls._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' non trouvé")

        # Validation d'accès
        if agent_name and not cls.validate_access(tool_name, agent_name):
            logger.warning(
                f"Accès refusé au tool {tool_name} pour l'agent {agent_name}",
                extra={"tool_name": tool_name, "agent_name": agent_name}
            )
            raise PermissionError(f"Agent '{agent_name}' non autorisé à utiliser le tool '{tool_name}'")

        start_time = time.time()
        execution_time = 0.0
        success = False

        try:
            # Exécution avec timeout si spécifié
            if tool.timeout:
                if inspect.iscoroutinefunction(func):
                    result = asyncio.wait_for(func(*args, **kwargs), timeout=tool.timeout)
                else:
                    # Pour les fonctions synchrones, on utilise un thread pool
                    loop = asyncio.get_event_loop()
                    result = loop.run_in_executor(
                        None,
                        functools.partial(func, *args, **kwargs)
                    )
                    result = asyncio.wait_for(result, timeout=tool.timeout)
            else:
                if inspect.iscoroutinefunction(func):
                    result = func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

            success = True
            return result

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout lors de l'exécution du tool {tool_name}",
                extra={
                    "tool_name": tool_name,
                    "agent_name": agent_name,
                    "timeout": tool.timeout,
                }
            )
            raise TimeoutError(f"Le tool '{tool_name}' a dépassé le timeout de {tool.timeout}s")
        
        except Exception as e:
            logger.error(
                f"Erreur lors de l'exécution du tool {tool_name}",
                extra={
                    "tool_name": tool_name,
                    "agent_name": agent_name,
                    "error": str(e),
                    "function": func.__name__,
                },
                exc_info=True
            )
            raise

        finally:
            # Mise à jour des statistiques
            if tool.track_usage:
                execution_time = time.time() - start_time
                tool.update_stats(execution_time, success)
                
                logger.info(
                    f"Tool exécuté: {tool_name}",
                    extra={
                        "tool_name": tool_name,
                        "agent_name": agent_name,
                        "execution_time": execution_time,
                        "success": success,
                        "call_count": tool.call_count,
                        "success_rate": tool.success_count / max(1, tool.call_count),
                    }
                )

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation avancées des tools."""
        total_tools = len(cls._tools)
        total_calls = sum(tool.call_count for tool in cls._tools.values())
        total_errors = sum(tool.error_count for tool in cls._tools.values())
        total_success = sum(tool.success_count for tool in cls._tools.values())
        
        categories = {}
        for tool in cls._tools.values():
            if tool.category not in categories:
                categories[tool.category] = {
                    "count": 0,
                    "calls": 0,
                    "errors": 0,
                    "success": 0,
                    "avg_time": 0.0
                }
            categories[tool.category]["count"] += 1
            categories[tool.category]["calls"] += tool.call_count
            categories[tool.category]["errors"] += tool.error_count
            categories[tool.category]["success"] += tool.success_count
            categories[tool.category]["avg_time"] += tool.total_execution_time

        # Calcul du temps moyen par catégorie
        for category in categories.values():
            if category["calls"] > 0:
                category["avg_time"] /= category["calls"]

        # Tools les plus utilisés
        most_used = sorted(
            cls._tools.items(),
            key=lambda x: x[1].call_count,
            reverse=True
        )[:10]

        # Tools avec le plus d'erreurs
        most_errors = sorted(
            cls._tools.items(),
            key=lambda x: x[1].error_count,
            reverse=True
        )[:5]

        # Performance moyenne par catégorie
        avg_performance = {
            category: data["avg_time"]
            for category, data in categories.items()
        }

        return {
            "total_tools": total_tools,
            "total_calls": total_calls,
            "total_errors": total_errors,
            "total_success": total_success,
            "error_rate": total_errors / max(1, total_calls),
            "success_rate": total_success / max(1, total_calls),
            "categories": categories,
            "most_used_tools": [
                {
                    "name": name,
                    "calls": tool.call_count,
                    "success_rate": tool.success_count / max(1, tool.call_count),
                    "avg_time": tool.avg_execution_time
                }
                for name, tool in most_used
            ],
            "most_error_tools": [
                {
                    "name": name,
                    "errors": tool.error_count,
                    "total_calls": tool.call_count,
                    "error_rate": tool.error_count / max(1, tool.call_count)
                }
                for name, tool in most_errors
            ],
            "avg_performance_by_category": avg_performance,
            "tools": {name: tool.to_dict() for name, tool in cls._tools.items()},
        }

    @classmethod
    def get_health_report(cls) -> Dict[str, Any]:
        """Génère un rapport de santé du système de tools."""
        stats = cls.get_statistics()
        
        # Vérification des anomalies
        issues = []
        
        # Tools avec un taux d'erreur élevé (> 20%)
        for tool_name, tool_data in stats["tools"].items():
            if tool_data["call_count"] > 10 and tool_data["error_rate"] > 0.2:
                issues.append({
                    "type": "high_error_rate",
                    "tool": tool_name,
                    "error_rate": tool_data["error_rate"],
                    "calls": tool_data["call_count"]
                })
        
        # Tools avec un temps d'exécution moyen élevé (> 5s)
        for tool_name, tool_data in stats["tools"].items():
            if tool_data["call_count"] > 5 and tool_data["avg_execution_time"] > 5.0:
                issues.append({
                    "type": "slow_execution",
                    "tool": tool_name,
                    "avg_time": tool_data["avg_execution_time"],
                    "calls": tool_data["call_count"]
                })
        
        # Catégories sous-utilisées
        for category, data in stats["categories"].items():
            if data["calls"] == 0:
                issues.append({
                    "type": "unused_category",
                    "category": category
                })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "global_stats": {
                "total_tools": stats["total_tools"],
                "total_calls": stats["total_calls"],
                "success_rate": stats["success_rate"],
                "error_rate": stats["error_rate"],
            },
            "issues": issues,
            "recommendations": cls._generate_recommendations(issues, stats),
            "status": "healthy" if len(issues) == 0 else "warning" if len(issues) < 5 else "critical"
        }

    @classmethod
    def _generate_recommendations(cls, issues: List[Dict], stats: Dict) -> List[str]:
        """Génère des recommandations basées sur les problèmes détectés."""
        recommendations = []
        
        error_issues = [issue for issue in issues if issue["type"] == "high_error_rate"]
        if error_issues:
            recommendations.append(f"Vérifier et corriger les {len(error_issues)} tools avec un taux d'erreur élevé")
        
        slow_issues = [issue for issue in issues if issue["type"] == "slow_execution"]
        if slow_issues:
            recommendations.append(f"Optimiser les {len(slow_issues)} tools lents (> 5s d'exécution moyenne)")
        
        if stats["success_rate"] < 0.95:
            recommendations.append("Améliorer la fiabilité globale du système (taux de succès < 95%)")
        
        if stats["total_calls"] == 0:
            recommendations.append("Aucun tool n'a été exécuté récemment - vérifier l'intégration")
        
        return recommendations


# Alias pour compatibilité
ToolRegistry = ToolRegistry