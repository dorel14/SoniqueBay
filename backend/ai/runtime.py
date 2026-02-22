import inspect
import asyncio
import time
from typing import AsyncIterator, Optional, Dict, Any
from collections import deque
from dataclasses import dataclass

from pydantic_ai import Agent as PydanticAgent
from backend.api.schemas.agent_response_schema import AgentMessageType, AgentState, StreamEvent
from backend.api.utils.logging import logger


@dataclass
class StreamingBuffer:
    """Gestion du buffer pour le streaming optimisé."""
    chunks: deque
    max_buffer_size: int = 100
    flush_interval: float = 0.1  # Secondes
    last_flush: float = 0.0
    
    def __init__(self):
        self.chunks = deque()
        self.max_buffer_size = 100
        self.flush_interval = 0.1
        self.last_flush = time.time()
    
    def add_chunk(self, chunk: str) -> None:
        """Ajoute un chunk au buffer."""
        self.chunks.append(chunk)
        
        # Nettoyage du buffer si trop gros
        while len(self.chunks) > self.max_buffer_size:
            self.chunks.popleft()
    
    def should_flush(self) -> bool:
        """Détermine si le buffer doit être vidé."""
        current_time = time.time()
        return (
            len(self.chunks) >= 10 or  # Buffer assez gros
            current_time - self.last_flush >= self.flush_interval  # Temps écoulé
        )
    
    def flush(self) -> str:
        """Vide le buffer et retourne le contenu."""
        if not self.chunks:
            return ""
        
        content = "".join(self.chunks)
        self.chunks.clear()
        self.last_flush = time.time()
        return content


class AgentRuntime:
    """
    Runtime d'agent optimisé pour le streaming et la gestion des états.
    
    Cette classe gère :
    - Le streaming intelligent avec bufferisation
    - La gestion avancée des états d'agents
    - La gestion d'erreurs robuste
    - L'optimisation mémoire pour RPi4
    """
    
    def __init__(self, name: str, agent: PydanticAgent):
        self.name = name
        self.agent = agent
        self.buffer = StreamingBuffer()
        self._last_error_time = 0.0
        self._error_count = 0
        self._consecutive_errors = 0

    # -------------------------------------------------
    # Exécution non-stream (JSON / résultat final)
    # -------------------------------------------------
    async def run(self, message: str, context) -> dict:
        """Exécution standard avec gestion d'erreurs et retry."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                result = await self._call_agent_with_retry(self.agent.run, message, context, attempt)
                
                # Réinitialisation des erreurs après succès
                if self._consecutive_errors > 0:
                    logger.info(
                        f"Agent {self.name} récupéré après {self._consecutive_errors} erreurs",
                        extra={"agent_name": self.name, "consecutive_errors": self._consecutive_errors}
                    )
                    self._consecutive_errors = 0
                
                # Normalisation du résultat
                return self._normalize_result(result)
                
            except Exception as e:
                await self._handle_error(e, attempt, max_retries)
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
        
        # Tous les retries échoués
        raise RuntimeError(f"Agent {self.name} a échoué après {max_retries} tentatives")

    # -------------------------------------------------
    # Exécution stream optimisée
    # -------------------------------------------------
    async def stream(
        self,
        message: str,
        context,
    ) -> AsyncIterator[StreamEvent]:
        """Streaming optimisé avec bufferisation intelligente."""
        
        # État initial
        yield StreamEvent(
            agent=self.name,
            state=AgentState.THINKING,
            type=AgentMessageType.TEXT,
            timestamp=time.time()
        )

        try:
            async for event in self._stream_with_buffering(message, context):
                yield event

        except Exception as e:
            # Gestion d'erreur en streaming
            logger.error(
                f"Erreur lors du streaming pour l'agent {self.name}",
                extra={
                    "agent_name": self.name,
                    "error": str(e),
                    "msg_preview": message[:100]  # Limiter la longueur du log
                },
                exc_info=True
            )
            
            # Émission d'un événement d'erreur
            yield StreamEvent(
                agent=self.name,
                state=AgentState.ERROR,
                type=AgentMessageType.ERROR,
                content=f"Erreur de streaming: {str(e)}",
                timestamp=time.time()
            )

        finally:
            # État final
            yield StreamEvent(
                agent=self.name,
                state=AgentState.DONE,
                type=AgentMessageType.FINAL,
                timestamp=time.time()
            )

    # -------------------------------------------------
    # Streaming avec bufferisation intelligente
    # -------------------------------------------------
    async def _stream_with_buffering(
        self,
        message: str,
        context
    ) -> AsyncIterator[StreamEvent]:
        """Streaming avec bufferisation pour optimiser les performances RPi4."""
        
        buffer = StreamingBuffer()
        last_chunk_time = time.time()
        max_silence = 5.0  # Augmenté à 5s pour éviter les interruptions prématurées
        
        # Timeout augmenté à 90s pour les réponses longues
        async for event in self._call_agent_stream_with_timeout(message, context, timeout=90):
            normalized = self._normalize_stream_event(event)
            
            if normalized is None:
                continue
            
            # Gestion spéciale du texte pour bufferisation
            if normalized.type == AgentMessageType.TEXT and normalized.content:
                buffer.add_chunk(normalized.content)
                
                # Vérification si on doit flusher
                if buffer.should_flush():
                    content = buffer.flush()
                    if content.strip():  # Ne pas envoyer de contenu vide
                        yield StreamEvent(
                            agent=self.name,
                            state=AgentState.STREAMING,
                            type=AgentMessageType.TEXT,
                            content=content,
                            timestamp=time.time()
                        )
                        last_chunk_time = time.time()
                
                # Vérification du timeout de silence
                if time.time() - last_chunk_time > max_silence:
                    content = buffer.flush()
                    if content.strip():
                        yield StreamEvent(
                            agent=self.name,
                            state=AgentState.STREAMING,
                            type=AgentMessageType.TEXT,
                            content=content,
                            timestamp=time.time()
                        )
                    last_chunk_time = time.time()
            
            else:
                # Flush immédiat pour les événements non-texte
                remaining_content = buffer.flush()
                if remaining_content.strip():
                    yield StreamEvent(
                        agent=self.name,
                        state=AgentState.STREAMING,
                        type=AgentMessageType.TEXT,
                        content=remaining_content,
                        timestamp=time.time()
                    )
                
                # Émission de l'événement non-texte
                yield normalized
                last_chunk_time = time.time()

        # Flush final - toujours envoyer le contenu restant même si vide
        final_content = buffer.flush()
        if final_content.strip():
            yield StreamEvent(
                agent=self.name,
                state=AgentState.STREAMING,
                type=AgentMessageType.TEXT,
                content=final_content,
                timestamp=time.time()
            )
        
        # Log de fin de bufferisation
        logger.debug(
            f"Bufferisation terminée pour {self.name}",
            extra={"agent_name": self.name, "final_buffer_size": len(final_content)}
        )

    # -------------------------------------------------
    # Appels agents avec retry et timeout
    # -------------------------------------------------
    async def _call_agent_with_retry(
        self,
        fn,
        message: str,
        context,
        attempt: int
    ):
        """Appel agent avec retry et gestion d'erreurs."""
        
        timeout = 60 + (attempt * 30)  # Timeout croissant avec les retries
        
        try:
            return await asyncio.wait_for(
                self._call_agent(fn, message, context),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout pour l'agent {self.name} (tentative {attempt + 1})",
                extra={
                    "agent_name": self.name,
                    "attempt": attempt + 1,
                    "timeout": timeout
                }
            )
            raise
        except Exception as e:
            logger.debug(
                f"Erreur agent {self.name} (tentative {attempt + 1}): {str(e)}",
                extra={
                    "agent_name": self.name,
                    "attempt": attempt + 1,
                    "error": str(e)
                }
            )
            raise

    async def _call_agent_stream_with_timeout(
        self,
        message: str,
        context,
        timeout: float = 90.0
    ):
        """Appel stream avec timeout global augmenté pour les réponses longues."""
        
        try:
            # Appel avec timeout sur le premier élément (initialisation)
            stream_gen = self._call_agent_stream(self.agent.run_stream, message, context)
            # Utiliser wait_for sur l'itération avec timeout entre chaque chunk
            start_time = asyncio.get_event_loop().time()
            chunk_count = 0
            
            async for event in stream_gen:
                chunk_count += 1
                # Vérifier le timeout global
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout:
                    logger.warning(
                        f"Streaming timeout global atteint pour l'agent {self.name}",
                        extra={
                            "agent_name": self.name,
                            "timeout": timeout,
                            "chunks_received": chunk_count,
                            "elapsed_time": current_time - start_time
                        }
                    )
                    raise asyncio.TimeoutError()
                yield event
            
            # Log de fin de streaming réussi
            logger.debug(
                f"Streaming terminé avec succès pour {self.name}",
                extra={
                    "agent_name": self.name,
                    "total_chunks": chunk_count,
                    "elapsed_time": asyncio.get_event_loop().time() - start_time
                }
            )
                
        except asyncio.TimeoutError:
            logger.warning(
                f"Streaming timeout pour l'agent {self.name}",
                extra={
                    "agent_name": self.name,
                    "timeout": timeout
                }
            )
            raise
        except Exception as e:
            logger.error(
                f"Erreur lors du streaming pour l'agent {self.name}: {e}",
                extra={
                    "agent_name": self.name,
                    "error": str(e),
                    "chunks_received": chunk_count if 'chunk_count' in locals() else 0
                },
                exc_info=True
            )
            raise

    # -------------------------------------------------
    # Helpers internes optimisés
    # -------------------------------------------------
    async def _call_agent(self, fn, message, context):
        """Appel agent avec détection de signature optimisée."""
        sig = inspect.signature(fn)
        
        # Cache de la signature pour éviter les appels répétés
        if not hasattr(self, '_cached_signature'):
            self._cached_signature = sig
        
        if "context" in self._cached_signature.parameters:
            return await fn(message, context=context)
        elif "messages" in self._cached_signature.parameters:
            return await fn(context.messages)
        else:
            return await fn(message)

    async def _call_agent_stream(self, fn, message, context):
        """Appel stream agent avec détection de signature optimisée."""
        sig = getattr(self, '_cached_signature', inspect.signature(fn))
        
        if "context" in sig.parameters:
            async with fn(message, context=context) as result:
                async for text in result.stream_text():
                    yield text
        elif "messages" in sig.parameters:
            async with fn(context.messages) as result:
                async for text in result.stream_text():
                    yield text
        else:
            async with fn(message) as result:
                async for text in result.stream_text():
                    yield text

    # -------------------------------------------------
    # Normalisation avancée des événements
    # -------------------------------------------------
    def _normalize_stream_event(self, event) -> Optional[StreamEvent]:
        """Normalisation avancée des événements de streaming."""
        
        current_time = time.time()
        
        # Gestion des événements pydantic-ai (objets avec méthodes is_*)
        if hasattr(event, 'is_output_text'):
            # Texte progressif avec gestion de la ponctuation
            if event.is_output_text():
                content = event.delta
                
                # Optimisation pour RPi4 : éviter les chunks trop petits
                if len(content.strip()) < 3 and content.strip() not in ".!?;:,":
                    return None  # Skip chunks trop petits
                
                return StreamEvent(
                    agent=self.name,
                    state=AgentState.STREAMING,
                    type=AgentMessageType.TEXT,
                    content=content,
                    timestamp=current_time
                )

            # Appel de tool avec validation
            elif event.is_tool_call():
                return StreamEvent(
                    agent=self.name,
                    state=AgentState.TOOL_CALLING,
                    type=AgentMessageType.TOOL_CALL,
                    payload={
                        "tool": event.tool_name,
                        "args": event.args,
                    },
                    timestamp=current_time
                )

            # Résultat de tool
            elif event.is_tool_result():
                return StreamEvent(
                    agent=self.name,
                    state=AgentState.ACTING,
                    type=AgentMessageType.TOOL_RESULT,
                    payload=event.result,
                    timestamp=current_time
                )
        
        # Gestion des chaînes de texte brutes (stream_text())
        elif isinstance(event, str):
            content = event
            
            # Optimisation pour RPi4 : éviter les chunks trop petits
            if len(content.strip()) < 3 and content.strip() not in ".!?;:,":
                return None  # Skip chunks trop petits
            
            return StreamEvent(
                agent=self.name,
                state=AgentState.STREAMING,
                type=AgentMessageType.TEXT,
                content=content,
                timestamp=current_time
            )

        return None

    # -------------------------------------------------
    # Gestion avancée des erreurs
    # -------------------------------------------------
    async def _handle_error(self, error: Exception, attempt: int, max_retries: int) -> None:
        """Gestion avancée des erreurs avec backoff et monitoring."""
        
        current_time = time.time()
        self._error_count += 1
        self._consecutive_errors += 1
        
        # Calcul du backoff progressif
        retry_delay = min(1.0 * (2 ** attempt), 10.0)  # Max 10s de delay
        
        # Logging avec contexte
        logger.error(
            f"Erreur agent {self.name} (tentative {attempt + 1}/{max_retries})",
            extra={
                "agent_name": self.name,
                "attempt": attempt + 1,
                "max_retries": max_retries,
                "error": str(error),
                "error_count": self._error_count,
                "consecutive_errors": self._consecutive_errors,
                "retry_delay": retry_delay
            },
            exc_info=True
        )
        
        # Alertes pour erreurs fréquentes
        if self._consecutive_errors >= 5:
            logger.critical(
                f"Agent {self.name} en état d'erreur persistante",
                extra={
                    "agent_name": self.name,
                    "consecutive_errors": self._consecutive_errors,
                    "total_errors": self._error_count
                }
            )
        
        self._last_error_time = current_time

    # -------------------------------------------------
    # Normalisation des résultats
    # -------------------------------------------------
    def _normalize_result(self, result) -> dict:
        """Normalisation avancée des résultats."""
        
        if hasattr(result, "output"):
            return result.output
        elif hasattr(result, "dict"):
            return result.dict()
        elif hasattr(result, "__dict__"):
            return result.__dict__
        else:
            return {"result": result}

    # -------------------------------------------------
    # Monitoring et statistiques
    # -------------------------------------------------
    def get_health_status(self) -> Dict[str, Any]:
        """Retourne le statut de santé du runtime."""
        current_time = time.time()
        
        return {
            "agent_name": self.name,
            "error_count": self._error_count,
            "consecutive_errors": self._consecutive_errors,
            "last_error_time": self._last_error_time,
            "time_since_last_error": current_time - self._last_error_time,
            "buffer_size": len(self.buffer.chunks),
            "is_healthy": self._consecutive_errors < 3,
            "recommendations": self._get_health_recommendations()
        }
    
    def _get_health_recommendations(self) -> list:
        """Génère des recommandations basées sur l'état de santé."""
        recommendations = []
        
        if self._consecutive_errors >= 3:
            recommendations.append("Redémarrer l'agent ou vérifier la configuration")
        
        if self._error_count > 10:
            recommendations.append("Vérifier les dépendances et le modèle LLM")
        
        if len(self.buffer.chunks) > 50:
            recommendations.append("Optimiser le buffer de streaming")
        
        return recommendations
