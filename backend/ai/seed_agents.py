from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api.models.agent_model import AgentModel
from backend.ai.agents.builder import build_agent
import os

DEFAULT_AGENT_MODEL = os.getenv("AGENT_MODEL", "phi3:mini")
BASE_AGENTS = [
    {
        "name": "orchestrator",
        "model": DEFAULT_AGENT_MODEL,
        "system_prompt": "Tu es l'agent orchestrateur, tu détectes les intents et routes vers les sous-agents.",
        "enabled": True,
        "tools": []
    },
    {
        "name": "search_agent",
        "model": DEFAULT_AGENT_MODEL,
        "system_prompt": "Tu recherches des morceaux, artistes et albums dans la base.",
        "enabled": True,
        "tools": ["search_tracks", "search_artists"]
    },
    {
        "name": "playlist_agent",
        "model": DEFAULT_AGENT_MODEL,
        "system_prompt": "Tu génères des playlists selon les critères de l'utilisateur.",
        "enabled": True,
        "tools": ["create_playlist"]
    },
    {
        "name": "smalltalk_agent",
        "model": DEFAULT_AGENT_MODEL,
        "system_prompt": "Tu gères les conversations smalltalk et détectes l’humeur.",
        "enabled": True,
        "tools": []
    }
]

async def seed_default_agents(session: AsyncSession):
    """
    Vérifie la BDD et insère les agents de base si absents.
    """
    for agent_data in BASE_AGENTS:
        stmt = select(AgentModel).where(AgentModel.name == agent_data["name"])
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            # Création
            agent = AgentModel(**agent_data)
            session.add(agent)
    
    await session.commit()
