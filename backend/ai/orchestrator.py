from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.loader import AgentLoader
from backend.ai.context import ConversationContext
from backend.ai.router import IntentRouter


class Orchestrator:
    """
    Orchestrateur central :
    - maintient le contexte
    - appelle l'agent orchestrator (intent)
    - choisit le bon agent (fallback + scoring)
    - exécute l'agent
    - apprend du résultat
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        self.loader = AgentLoader(session)
        self.context = ConversationContext()
        self.router = IntentRouter()

        # { "search_agent": Agent, ... }
        self.agents = self.loader.load_enabled_agents()

        if "orchestrator" not in self.agents:
            raise RuntimeError("Agent 'orchestrator' manquant")

    # ---------------------------------------------------------
    # Appel standard (non streaming)
    # ---------------------------------------------------------
    async def handle(self, message: str) -> Dict[str, Any]:
        self.context.add_user(message)

        # 1️⃣ Détection d'intention (LLM)
        orch = self.agents["orchestrator"]
        intent_res = await orch.run(
            message,
            context=self.context.export()
        )

        intent = intent_res.get("intent")
        suggested_agent = intent_res.get("agent")

        # 2️⃣ Choix final de l'agent
        agent_name = await self._select_agent(
            intent=intent,
            suggested_agent=suggested_agent
        )

        agent = self.agents.get(agent_name)
        if not agent:
            return {"error": f"agent '{agent_name}' not found"}

        # 3️⃣ Exécution
        result = await agent.run(
            message,
            context=self.context.export()
        )

        # 4️⃣ Contexte
        self.context.add_agent(agent_name, result)

        # 5️⃣ Apprentissage
        await self.router.register_usage(
            session=self.session,
            agent_name=agent_name,
            intent=intent,
            success=True,
        )

        return result

    # ---------------------------------------------------------
    # Streaming (WebSocket / SSE)
    # ---------------------------------------------------------
    async def handle_stream(self, message: str):
        self.context.add_user(message)

        orch = self.agents["orchestrator"]
        intent_res = await orch.run(
            message,
            context=self.context.export()
        )

        intent = intent_res.get("intent")
        suggested_agent = intent_res.get("agent")

        agent_name = await self._select_agent(intent, suggested_agent)
        agent = self.agents.get(agent_name)

        if not agent:
            yield {"error": "agent not found"}
            return

        async for chunk in agent.run_stream(
            message,
            context=self.context.export()
        ):
            yield chunk

        self.context.add_agent(agent_name, {"done": True})

        await self.router.register_usage(
            session=self.session,
            agent_name=agent_name,
            intent=intent,
            success=True,
        )

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
