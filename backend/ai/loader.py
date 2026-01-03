from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.models.agent_model import AgentModel
from backend.ai.agents.builder import build_agent, build_agent_with_inheritance, validate_agent_configuration
from backend.api.utils.logging import logger


class AgentLoader:
    """
    Chargeur d'agents avec support de l'héritage et de la validation RTCROS.
    
    Cette classe gère :
    - Le chargement des agents depuis la base de données
    - La validation de la configuration RTCROS
    - La construction avec héritage des agents
    - Le caching des agents construits
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._agent_cache: Dict[str, Any] = {}
        self._base_agents_cache: Dict[str, AgentModel] = {}

    async def load_enabled_agents(self) -> Dict[str, Any]:
        """
        Charge tous les agents activés avec gestion de l'héritage.
        
        Returns:
            Dict: Dictionnaire des agents construits {nom: agent}
        """
        # Chargement des agents de base (sans héritage)
        base_agents = await self._load_base_agents()
        
        # Chargement et construction des agents enfants
        all_agents = await self._load_and_build_agents(base_agents)
        
        logger.info(
            f"Loader: {len(all_agents)} agents chargés avec succès",
            extra={
                "base_agents_count": len(base_agents),
                "total_agents": len(all_agents),
                "agent_names": list(all_agents.keys())
            }
        )
        
        return all_agents

    async def _load_base_agents(self) -> Dict[str, AgentModel]:
        """
        Charge les agents de base (ceux qui n'héritent pas d'autres agents).
        
        Returns:
            Dict: Dictionnaire des modèles d'agents de base
        """
        result = await self.session.execute(
            select(AgentModel).where(
                AgentModel.enabled is True,
                AgentModel.base_agent.is_(None)
            )
        )
        
        base_agents = {row.name: row for row in result.scalars()}
        self._base_agents_cache = base_agents
        
        logger.debug(
            f"Loader: {len(base_agents)} agents de base chargés",
            extra={"base_agent_names": list(base_agents.keys())}
        )
        
        return base_agents

    async def _load_and_build_agents(self, base_agents: Dict[str, AgentModel]) -> Dict[str, Any]:
        """
        Charge et construit tous les agents avec gestion de l'héritage.
        
        Args:
            base_agents: Dictionnaire des agents de base
            
        Returns:
            Dict: Dictionnaire des agents construits
        """
        # Chargement de tous les agents enfants (avec héritage)
        result = await self.session.execute(
            select(AgentModel).where(
                AgentModel.enabled is True,
                AgentModel.base_agent.isnot(None)
            )
        )
        
        child_agents = {row.name: row for row in result.scalars()}
        
        # Construction de tous les agents (base + enfants)
        all_agents = {}
        
        # Construction des agents de base
        for name, model in base_agents.items():
            try:
                agent = build_agent(model)
                all_agents[name] = agent
                self._agent_cache[name] = agent
            except Exception as e:
                logger.error(
                    f"Erreur lors de la construction de l'agent de base '{name}'",
                    extra={
                        "agent_name": name,
                        "error": str(e)
                    },
                    exc_info=True
                )
        
        # Construction des agents enfants avec héritage
        for name, model in child_agents.items():
            try:
                agent = build_agent_with_inheritance(model, base_agents)
                all_agents[name] = agent
                self._agent_cache[name] = agent
            except Exception as e:
                logger.error(
                    f"Erreur lors de la construction de l'agent enfant '{name}'",
                    extra={
                        "agent_name": name,
                        "base_agent": model.base_agent,
                        "error": str(e)
                    },
                    exc_info=True
                )
        
        return all_agents

    async def load_agent_by_name(self, agent_name: str) -> Optional[Any]:
        """
        Charge un agent spécifique par son nom.
        
        Args:
            agent_name: Nom de l'agent à charger
            
        Returns:
            Agent construit ou None si non trouvé
        """
        # Vérification du cache
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
        
        # Recherche dans la base
        result = await self.session.execute(
            select(AgentModel).where(
                AgentModel.name == agent_name,
                AgentModel.enabled is True
            )
        )
        
        agent_model = result.scalar_one_or_none()
        if not agent_model:
            logger.warning(f"Agent '{agent_name}' non trouvé ou désactivé")
            return None
        
        # Construction de l'agent
        try:
            if agent_model.base_agent:
                # Agent avec héritage
                base_agents = await self._load_base_agents()
                agent = build_agent_with_inheritance(agent_model, base_agents)
            else:
                # Agent de base
                agent = build_agent(agent_model)
            
            # Mise en cache
            self._agent_cache[agent_name] = agent
            
            logger.info(f"Agent '{agent_name}' chargé à la demande")
            return agent
            
        except Exception as e:
            logger.error(
                f"Erreur lors du chargement de l'agent '{agent_name}'",
                extra={
                    "agent_name": agent_name,
                    "error": str(e)
                },
                exc_info=True
            )
            return None

    async def validate_all_agents(self) -> Dict[str, Any]:
        """
        Valide la configuration de tous les agents.
        
        Returns:
            Dict: Rapport de validation pour tous les agents
        """
        result = await self.session.execute(
            select(AgentModel).where(AgentModel.enabled is True)
        )
        
        validation_report = {
            "total_agents": 0,
            "valid_agents": 0,
            "invalid_agents": 0,
            "warnings": 0,
            "details": {}
        }
        
        for agent_model in result.scalars():
            validation_report["total_agents"] += 1
            
            report = validate_agent_configuration(agent_model)
            validation_report["details"][agent_model.name] = report
            
            if report["is_valid"]:
                validation_report["valid_agents"] += 1
            else:
                validation_report["invalid_agents"] += 1
            
            if report["warnings"]:
                validation_report["warnings"] += len(report["warnings"])
        
        logger.info(
            "Validation des agents terminée",
            extra={
                "total": validation_report["total_agents"],
                "valid": validation_report["valid_agents"],
                "invalid": validation_report["invalid_agents"],
                "warnings": validation_report["warnings"]
            }
        )
        
        return validation_report

    async def reload_agents(self) -> Dict[str, Any]:
        """
        Recharge tous les agents (utile pour le hot-reload).
        
        Returns:
            Dict: Rapport de rechargement
        """
        # Nettoyage du cache
        self._agent_cache.clear()
        self._base_agents_cache.clear()
        
        # Rechargement
        try:
            agents = await self.load_enabled_agents()
            
            reload_report = {
                "success": True,
                "reloaded_count": len(agents),
                "agent_names": list(agents.keys()),
                "errors": []
            }
            
            logger.info(
                "Rechargement des agents terminé avec succès",
                extra={
                    "reloaded_count": reload_report["reloaded_count"],
                    "agent_names": reload_report["agent_names"]
                }
            )
            
            return reload_report
            
        except Exception as e:
            reload_report = {
                "success": False,
                "reloaded_count": 0,
                "agent_names": [],
                "errors": [str(e)]
            }
            
            logger.error(
                "Erreur lors du rechargement des agents",
                extra={"error": str(e)},
                exc_info=True
            )
            
            return reload_report

    def get_cached_agents(self) -> Dict[str, Any]:
        """
        Retourne les agents actuellement en cache.
        
        Returns:
            Dict: Agents en cache
        """
        return self._agent_cache.copy()

    def clear_cache(self) -> None:
        """
        Nettoie le cache des agents.
        """
        self._agent_cache.clear()
        self._base_agents_cache.clear()
        logger.debug("Cache des agents nettoyé")