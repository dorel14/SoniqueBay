"""
Script pour mettre à jour le prompt de l'orchestrator dans la base de données.
À exécuter après modification de seed_agents.py pour appliquer les changements.
"""
import asyncio
import os
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.utils.database import get_async_session
from backend.api.models.agent_model import AgentModel
from backend.api.utils.logging import logger


NEW_ORCHESTRATOR_CONFIG = {
    "role": "Tu es l'agent orchestrateur central. Tu analyses chaque message utilisateur et décides quel sous-agent doit le traiter.",
    "task": """Pour chaque message utilisateur:
1. Détecte l'intention principale (search, playlist, scan, smalltalk, general)
2. Route vers l'agent approprié:
   - 'search_agent' pour recherches (mots-clés: recherche, cherche, trouve, artiste, album, morceau)
   - 'playlist_agent' pour playlists (mots-clés: playlist, crée, mets-moi, fais-moi une liste)
   - 'action_agent' pour actions système (mots-clés: scan, rescan, bibliothèque, mise à jour)
   - 'smalltalk_agent' pour conversations simples (mots-clés: bonjour, salut, coucou, comment ça va, merci, au revoir, conversation générale sans but précis)
3. Retourne UNIQUEMENT un JSON: {"intent": "...", "agent": "...", "confidence": 0.9}""",
    "constraints": "Tu ne traites jamais directement la requête. Tu routes uniquement vers un sous-agent.",
    "rules": """RÈGLES DE ROUTAGE STRICTES:
- Pour 'coucou', 'salut', 'bonjour', 'comment ça va' → agent: 'smalltalk_agent', intent: 'smalltalk'
- Pour 'merci', 'au revoir', 'à plus' → agent: 'smalltalk_agent', intent: 'smalltalk'
- Pour toute conversation générale sans but précis → agent: 'smalltalk_agent', intent: 'general'
- Pour recherches musicales → agent: 'search_agent', intent: 'search'
- Pour création de playlists → agent: 'playlist_agent', intent: 'playlist'
- Pour actions système → agent: 'action_agent', intent: 'scan'
- Si l'intention est incertaine → agent: 'smalltalk_agent', intent: 'general'""",
    "output_schema": "JSON strict: {\"intent\": \"search|playlist|scan|smalltalk|general\", \"agent\": \"search_agent|playlist_agent|action_agent|smalltalk_agent\", \"confidence\": 0.0-1.0}",
}


async def update_orchestrator():
    """Met à jour l'agent orchestrator dans la base de données."""
    async with asynccontextmanager(get_async_session)() as session:
        from sqlalchemy import select
        stmt = select(AgentModel).where(AgentModel.name == "orchestrator")
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.error("Agent 'orchestrator' non trouvé dans la base de données")
            return False
        
        # Mise à jour des champs
        agent.role = NEW_ORCHESTRATOR_CONFIG["role"]
        agent.task = NEW_ORCHESTRATOR_CONFIG["task"]
        agent.constraints = NEW_ORCHESTRATOR_CONFIG["constraints"]
        agent.rules = NEW_ORCHESTRATOR_CONFIG["rules"]
        agent.output_schema = NEW_ORCHESTRATOR_CONFIG["output_schema"]
        
        await session.commit()
        logger.info("Agent 'orchestrator' mis à jour avec succès")
        return True


if __name__ == "__main__":
    from contextlib import asynccontextmanager
    asyncio.run(update_orchestrator())
