from typing import Dict, Any, AsyncIterator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import time

from backend.ai.loader import AgentLoader
from backend.ai.context import ConversationContext
from backend.ai.router import IntentRouter
from backend.ai.runtime import AgentRuntime
from backend.api.utils.logging import logger


class Orchestrator:
    """
    Orchestrateur central optimisé :
    - maintient le contexte conversationnel
    - appelle l'agent orchestrator (intent)
    - choisit le bon agent (fallback + scoring + apprentissage)
    - exécute l'agent avec gestion d'erreurs avancée
    - apprend du résultat et met à jour le scoring
    - monitoring et observabilité avancés
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.loader = AgentLoader(session)
        self.context = ConversationContext()
        self.router = IntentRouter()
        
        # Runtime cache pour le monitoring
        self._runtime_cache: Dict[str, AgentRuntime] = {}
        
        # Statistiques d'orchestration
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "agent_selections": {}
        }

        # Les agents sont chargés via `await self.init()` (méthode async obligatoire)
        # Ne pas appeler load_enabled_agents() ici : c'est une coroutine async
        self.agents: Dict[str, Any] = {}

    # ---------------------------------------------------------
    # Initialisation asynchrone (doit être appelée après __init__)
    # ---------------------------------------------------------
    async def init(self) -> None:
        """
        Initialisation asynchrone de l'orchestrateur.
        Doit être appelée avec `await orchestrator.init()` après l'instanciation.
        Charge les agents depuis la base de données et valide la présence de l'agent orchestrateur.
        """
        self.agents = await self.loader.load_enabled_agents()

        if "orchestrator" not in self.agents:
            logger.error(
                "Agent 'orchestrator' manquant dans la base de données ou désactivé",
                extra={"available_agents": list(self.agents.keys())}
            )
            raise RuntimeError(
                "Agent 'orchestrator' manquant — vérifiez que l'agent est activé en base de données."
            )

        logger.info(
            "Orchestrateur initialisé avec succès",
            extra={
                "agents_loaded": list(self.agents.keys()),
                "total_agents": len(self.agents)
            }
        )

    # ---------------------------------------------------------
    # Appel standard (non streaming) avec monitoring
    # ---------------------------------------------------------
    async def handle(self, message: str) -> Dict[str, Any]:
        """Gestion standard d'une requête avec monitoring complet."""
        start_time = time.time()
        self._stats["total_requests"] += 1
        
        try:
            # 1️⃣ Détection d'intention (LLM) avec timeout
            intent_data = await self._detect_intent_with_timeout(message, timeout=10.0)
            intent = intent_data.get("intent")
            suggested_agent = intent_data.get("agent")

            # 2️⃣ Choix final de l'agent avec fallback intelligent
            agent_name = await self._select_agent_with_fallback(
                intent=intent,
                suggested_agent=suggested_agent,
                fallback_strategy="scoring_then_default"
            )

            # 3️⃣ Exécution avec retry et monitoring
            result = await self._execute_agent_with_monitoring(
                agent_name=agent_name,
                message=message,
                intent=intent
            )

            # 4️⃣ Mise à jour du contexte
            self.context.add_agent(agent_name, result)

            # 5️⃣ Apprentissage et scoring
            await self._update_scoring_and_learning(
                agent_name=agent_name,
                intent=intent,
                success=True,
                response_time=time.time() - start_time
            )

            # Mise à jour des statistiques
            self._update_stats(success=True, response_time=time.time() - start_time, agent_name=agent_name)

            return result

        except Exception as e:
            # Gestion d'erreur globale
            error_result = await self._handle_orchestration_error(e, message, start_time)
            return error_result

    # ---------------------------------------------------------
    # Streaming (WebSocket / SSE) optimisé
    # ---------------------------------------------------------
    async def handle_stream(self, message: str) -> AsyncIterator[Dict[str, Any]]:
        """Streaming optimisé avec gestion d'erreurs et fallback."""
        start_time = time.time()
        self._stats["total_requests"] += 1
        
        try:
            # 1️⃣ Détection d'intention
            intent_data = await self._detect_intent_with_timeout(message, timeout=10.0)
            intent = intent_data.get("intent")
            suggested_agent = intent_data.get("agent")

            # 2️⃣ Choix de l'agent
            agent_name = await self._select_agent_with_fallback(
                intent=intent,
                suggested_agent=suggested_agent,
                fallback_strategy="scoring_then_default"
            )

            # 3️⃣ Streaming avec gestion d'erreurs
            async for chunk in self._stream_with_error_handling(
                agent_name=agent_name,
                message=message,
                intent=intent
            ):
                yield chunk

            # 4️⃣ Apprentissage après succès
            await self._update_scoring_and_learning(
                agent_name=agent_name,
                intent=intent,
                success=True,
                response_time=time.time() - start_time
            )

            # Mise à jour des statistiques
            self._update_stats(success=True, response_time=time.time() - start_time, agent_name=agent_name)

        except Exception as e:
            # Gestion d'erreur en streaming
            async for chunk in self._handle_streaming_error(e, message, start_time):
                yield chunk

    # ---------------------------------------------------------
    # Détection d'intention avec timeout et fallback
    # ---------------------------------------------------------
    async def _detect_intent_with_timeout(self, message: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Détection d'intention avec timeout et fallback."""
        try:
            orch = self.agents["orchestrator"]
            
            intent_res = await asyncio.wait_for(
                orch.run(message),
                timeout=60.0  # Augmenté à 60s pour les modèles plus lents
            )
            
            # Gérer le résultat comme un objet AgentRunResult (pydantic-ai)
            # ou comme un dictionnaire selon le type retourné
            if hasattr(intent_res, 'output'):
                # C'est un AgentRunResult, extraire l'output
                output = intent_res.output
                if isinstance(output, dict):
                    return {
                        "intent": output.get("intent"),
                        "agent": output.get("agent"),
                        "confidence": output.get("confidence", 0.0)
                    }
                elif isinstance(output, str):
                    # L'output est une chaîne, essayer de parser comme JSON
                    try:
                        import json
                        parsed = json.loads(output)
                        return {
                            "intent": parsed.get("intent"),
                            "agent": parsed.get("agent"),
                            "confidence": parsed.get("confidence", 0.0)
                        }
                    except json.JSONDecodeError:
                        # Fallback: utiliser la chaîne comme intent
                        return {
                            "intent": "general",
                            "agent": "smalltalk_agent",
                            "confidence": 0.5
                        }
                else:
                    # Fallback pour tout autre type
                    return {
                        "intent": "general",
                        "agent": "smalltalk_agent",
                        "confidence": 0.5
                    }
            elif isinstance(intent_res, dict):
                # C'est déjà un dictionnaire
                return {
                    "intent": intent_res.get("intent"),
                    "agent": intent_res.get("agent"),
                    "confidence": intent_res.get("confidence", 0.0)
                }
            else:
                # Fallback pour tout autre type
                logger.warning(f"Type de résultat inattendu: {type(intent_res)}")
                return {
                    "intent": "general",
                    "agent": "smalltalk_agent",
                    "confidence": 0.5
                }
            
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout lors de la détection d'intention, fallback vers analyse simple",
                extra={"message_preview": message[:50]}
            )
            
            # Fallback : analyse simple du message
            return self._simple_intent_fallback(message)
            
        except Exception as e:
            logger.error(
                f"Erreur lors de la détection d'intention: {e}",
                extra={"message_preview": message[:50]},
                exc_info=True
            )
            
            # Fallback ultime
            return {"intent": "general", "agent": "smalltalk_agent", "confidence": 0.5}

    def _simple_intent_fallback(self, message: str) -> Dict[str, Any]:
        """Fallback simple pour la détection d'intention."""
        msg_lower = message.lower()
        
        if any(word in msg_lower for word in ["recherche", "cherche", "trouve"]):
            return {"intent": "search", "agent": "search_agent", "confidence": 0.8}
        elif any(word in msg_lower for word in ["playlist", "mets moi", "fais moi"]):
            return {"intent": "playlist", "agent": "playlist_agent", "confidence": 0.8}
        elif any(word in msg_lower for word in ["scan", "rescanner", "bibliothèque"]):
            return {"intent": "scan", "agent": "action_agent", "confidence": 0.8}
        else:
            return {"intent": "general", "agent": "smalltalk_agent", "confidence": 0.6}

    # ---------------------------------------------------------
    # Sélection d'agent avec fallback intelligent
    # ---------------------------------------------------------
    async def _select_agent_with_fallback(
        self,
        intent: Optional[str],
        suggested_agent: Optional[str],
        fallback_strategy: str = "scoring_then_default"
    ) -> str:
        """Sélection d'agent avec plusieurs niveaux de fallback."""
        
        # 1er niveau : agent suggéré par l'orchestrator
        if suggested_agent and suggested_agent in self.agents:
            return suggested_agent
        
        # 2ème niveau : scoring basé sur l'historique
        if intent and fallback_strategy == "scoring_then_default":
            try:
                scored_agent = await self.router.choose_agent(
                    session=self.session,
                    intent=intent,
                    candidate_agents=list(self.agents.keys())
                )
                if scored_agent in self.agents:
                    return scored_agent
            except Exception as e:
                logger.warning(f"Échec du scoring d'agent: {e}")
        
        # 3ème niveau : mapping intent → agent par défaut
        intent_to_agent = {
            "search": "search_agent",
            "playlist": "playlist_agent",
            "scan": "action_agent",
            "smalltalk": "smalltalk_agent"
        }
        
        if intent in intent_to_agent:
            default_agent = intent_to_agent[intent]
            if default_agent in self.agents:
                return default_agent
        
        # 4ème niveau : fallback ultime
        logger.warning(f"Aucun agent trouvé pour l'intention '{intent}', fallback vers smalltalk_agent")
        return "smalltalk_agent"

    # ---------------------------------------------------------
    # Exécution avec monitoring et retry
    # ---------------------------------------------------------
    async def _execute_agent_with_monitoring(
        self,
        agent_name: str,
        message: str,
        intent: Optional[str]
    ) -> Dict[str, Any]:
        """Exécution d'agent avec monitoring avancé et retry."""
        
        runtime = self._get_or_create_runtime(agent_name)
        
        try:
            # Vérification de la santé de l'agent
            health = runtime.get_health_status()
            if not health["is_healthy"]:
                logger.warning(
                    f"Agent {agent_name} en mauvaise santé, tentative de fallback",
                    extra={"health": health}
                )
                # Essayer un agent alternatif
                fallback_agent = await self._get_fallback_agent(intent, agent_name)
                if fallback_agent != agent_name:
                    logger.info(f"Utilisation de l'agent fallback {fallback_agent}")
                    runtime = self._get_or_create_runtime(fallback_agent)
                    agent_name = fallback_agent

            # Exécution avec retry intégré au runtime
            result = await runtime.run(message, self.context.export())
            
            return result
            
        except Exception as e:
            logger.error(
                f"Échec de l'exécution de l'agent {agent_name}",
                extra={
                    "agent_name": agent_name,
                    "intent": intent,
                    "error": str(e)
                },
                exc_info=True
            )
            raise

    # ---------------------------------------------------------
    # Streaming avec gestion d'erreurs
    # ---------------------------------------------------------
    async def _stream_with_error_handling(
        self,
        agent_name: str,
        message: str,
        intent: Optional[str]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Streaming avec gestion avancée des erreurs et fallback."""
        
        runtime = self._get_or_create_runtime(agent_name)
        
        try:
            # Vérification de la santé
            health = runtime.get_health_status()
            if not health["is_healthy"]:
                fallback_agent = await self._get_fallback_agent(intent, agent_name)
                if fallback_agent != agent_name:
                    logger.info(f"Streaming fallback vers {fallback_agent}")
                    runtime = self._get_or_create_runtime(fallback_agent)
                    agent_name = fallback_agent

            # Streaming avec gestion d'erreurs intégrée
            async for chunk in runtime.stream(message, self.context.export()):
                yield chunk
                
        except Exception as e:
            logger.error(
                f"Erreur streaming pour l'agent {agent_name}",
                extra={
                    "agent_name": agent_name,
                    "intent": intent,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Émission d'un événement d'erreur
            yield {
                "agent": agent_name,
                "state": "error",
                "type": "error",
                "content": f"Erreur lors du traitement: {str(e)}",
                "timestamp": time.time()
            }

    # ---------------------------------------------------------
    # Apprentissage et mise à jour du scoring
    # ---------------------------------------------------------
    async def _update_scoring_and_learning(
        self,
        agent_name: str,
        intent: Optional[str],
        success: bool,
        response_time: float
    ) -> None:
        """Mise à jour du scoring et apprentissage."""
        
        try:
            await self.router.register_usage(
                session=self.session,
                agent_name=agent_name,
                intent=intent,
                success=success
            )
            
            # Logging de l'apprentissage
            logger.debug(
                f"Apprentissage mis à jour pour {agent_name}",
                extra={
                    "agent_name": agent_name,
                    "intent": intent,
                    "success": success,
                    "response_time": response_time
                }
            )
            
        except Exception as e:
            logger.error(
                f"Échec de la mise à jour du scoring: {e}",
                extra={"agent_name": agent_name, "intent": intent},
                exc_info=True
            )

    # ---------------------------------------------------------
    # Gestion des erreurs d'orchestration
    # ---------------------------------------------------------
    async def _handle_orchestration_error(
        self,
        error: Exception,
        message: str,
        start_time: float
    ) -> Dict[str, Any]:
        """Gestion centralisée des erreurs d'orchestration."""
        
        self._stats["failed_requests"] += 1
        
        error_result = {
            "error": True,
            "message": f"Désolé, une erreur est survenue: {str(error)}",
            "suggestion": "Veuillez réessayer ou contacter l'administrateur si le problème persiste.",
            "timestamp": time.time(),
            "response_time": time.time() - start_time
        }
        
        logger.error(
            "Erreur d'orchestration",
            extra={
                "error": str(error),
                "message_preview": message[:50],
                "response_time": time.time() - start_time,
                "total_requests": self._stats["total_requests"],
                "failed_requests": self._stats["failed_requests"]
            },
            exc_info=True
        )
        
        return error_result

    async def _handle_streaming_error(
        self,
        error: Exception,
        message: str,
        start_time: float
    ) -> AsyncIterator[Dict[str, Any]]:
        """Gestion des erreurs en streaming."""
        
        self._stats["failed_requests"] += 1
        
        yield {
            "agent": "orchestrator",
            "state": "error",
            "type": "error",
            "content": f"Erreur de streaming: {str(error)}",
            "timestamp": time.time()
        }
        
        yield {
            "agent": "orchestrator",
            "state": "done",
            "type": "final",
            "content": "La conversation a été interrompue en raison d'une erreur.",
            "timestamp": time.time()
        }
        
        logger.error(
            "Erreur streaming d'orchestration",
            extra={
                "error": str(error),
                "message_preview": message[:50],
                "response_time": time.time() - start_time
            },
            exc_info=True
        )

    # ---------------------------------------------------------
    # Helpers et utilities
    # ---------------------------------------------------------
    def _get_or_create_runtime(self, agent_name: str) -> AgentRuntime:
        """Récupère ou crée un runtime pour un agent."""
        if agent_name not in self._runtime_cache:
            self._runtime_cache[agent_name] = AgentRuntime(agent_name, self.agents[agent_name])
        return self._runtime_cache[agent_name]

    async def _get_fallback_agent(self, intent: Optional[str], current_agent: str) -> str:
        """Obtient un agent fallback pour une intention donnée."""
        # Mapping de fallbacks
        fallback_map = {
            "search": ["search_agent", "playlist_agent", "smalltalk_agent"],
            "playlist": ["playlist_agent", "search_agent", "smalltalk_agent"],
            "scan": ["action_agent", "search_agent", "smalltalk_agent"],
            "smalltalk": ["smalltalk_agent", "search_agent"]
        }
        
        candidates = fallback_map.get(intent, ["smalltalk_agent", "search_agent"])
        candidates = [a for a in candidates if a != current_agent and a in self.agents]
        
        if candidates:
            return candidates[0]
        
        # Fallback ultime
        return "smalltalk_agent" if "smalltalk_agent" in self.agents else list(self.agents.keys())[0]

    def _update_stats(
        self,
        success: bool,
        response_time: float,
        agent_name: str
    ) -> None:
        """Met à jour les statistiques d'orchestration."""
        if success:
            self._stats["successful_requests"] += 1
        
        # Mise à jour du temps de réponse moyen
        total = self._stats["successful_requests"] + self._stats["failed_requests"]
        self._stats["avg_response_time"] = (
            (self._stats["avg_response_time"] * (total - 1)) + response_time
        ) / total
        
        # Comptage des sélections d'agents
        if agent_name not in self._stats["agent_selections"]:
            self._stats["agent_selections"][agent_name] = 0
        self._stats["agent_selections"][agent_name] += 1

    # ---------------------------------------------------------
    # Monitoring et observabilité
    # ---------------------------------------------------------
    def get_health_report(self) -> Dict[str, Any]:
        """Génère un rapport de santé de l'orchestrateur."""
        agent_health = {}
        for agent_name, runtime in self._runtime_cache.items():
            agent_health[agent_name] = runtime.get_health_status()
        
        return {
            "orchestrator_stats": self._stats,
            "agent_health": agent_health,
            "context_size": len(self.context.messages),
            "total_agents": len(self.agents),
            "uptime": "N/A",  # À implémenter avec timestamp de démarrage
            "is_healthy": self._stats["failed_requests"] / max(1, self._stats["total_requests"]) < 0.1
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de performance."""
        success_rate = self._stats["successful_requests"] / max(1, self._stats["total_requests"])
        
        return {
            "success_rate": success_rate,
            "avg_response_time": self._stats["avg_response_time"],
            "total_requests": self._stats["total_requests"],
            "error_rate": self._stats["failed_requests"] / max(1, self._stats["total_requests"]),
            "most_used_agents": sorted(
                self._stats["agent_selections"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    # ---------------------------------------------------------
    # Sélection agent (clé)
    # ---------------------------------------------------------
    async def _select_agent(self, intent: str, suggested_agent: str) -> str:
        """
        Logique hybride :
        - fallback sur l'agent proposé par le LLM
        - scoring si existant
        """

        # fallback LLM si agent inconnu
        if suggested_agent not in self.agents:
            return suggested_agent

        # pas encore de scoring → on respecte l'intent de base
        if not await self.router.has_scores(self.session, intent):
            return suggested_agent

        # scoring actif
        return await self.router.choose_agent(
            session=self.session,
            intent=intent,
            candidate_agents=list(self.agents.keys()),
        )
