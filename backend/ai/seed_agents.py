from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api.models.agent_model import AgentModel
from backend.api.utils.logging import logger
import os

DEFAULT_AGENT_MODEL = os.getenv("AGENT_MODEL", "koboldcpp/qwen2.5-3b-instruct-q4_k_m")
BASE_AGENTS = [
    {
        "name": "orchestrator",
        "model": DEFAULT_AGENT_MODEL,
        # RTCROS fields (required)
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
        "state_strategy": "Stateless",
        "enabled": True,
        "tools": []
    },
    {
        "name": "search_agent",
        "model": DEFAULT_AGENT_MODEL,
        # RTCROS fields (required)
        "role": "Tu recherches des morceaux, artistes et albums dans la base.",
        "task": "Effectuer des recherches précises dans la base de données musicale.",
        "constraints": "Utiliser uniquement les outils de recherche fournis.",
        "rules": "Toujours vérifier les résultats avant de les présenter.",
        "output_schema": "Liste formatée de résultats pertinents.",
        "state_strategy": "Stateless",
        "enabled": True,
        "tools": ["search_tracks", "search_artists"]
    },
    {
        "name": "playlist_agent",
        "model": DEFAULT_AGENT_MODEL,
        # RTCROS fields (required)
        "role": "Tu génères des playlists selon les critères de l'utilisateur.",
        "task": "Créer des playlists personnalisées basées sur les préférences utilisateur.",
        "constraints": "Respecter les limites de taille des playlists.",
        "rules": "Inclure une variété de genres et d'artistes quand c'est possible.",
        "output_schema": "Playlist avec titre, description et liste de morceaux.",
        "state_strategy": "Stateful",
        "enabled": True,
        "tools": ["create_playlist"]
    },
    {
        "name": "smalltalk_agent",
        "model": DEFAULT_AGENT_MODEL,
        # RTCROS fields (required)
        "role": "Tu gères les conversations smalltalk et détectes l'humeur.",
        "task": "Maintenir une conversation naturelle et engageante avec l'utilisateur.",
        "constraints": "Rester concis et pertinent.",
        "rules": "Être amical et respectueux en toutes circonstances.",
        "output_schema": "Réponse conversationnelle avec détection d'humeur optionnelle.",
        "state_strategy": "Stateful",
        "enabled": True,
        "tools": []
    }
]


async def seed_default_agents(session: AsyncSession):
    """
    Vérifie la BDD et insère les agents de base si absents.
    """
    try:
        logger.info("Début de l'insertion des agents par défaut...")
        for agent_data in BASE_AGENTS:
            stmt = select(AgentModel).where(AgentModel.name == agent_data["name"])
            result = await session.execute(stmt)
            agent = result.scalar_one_or_none()

            if not agent:
                # Création
                logger.info(f"Création de l'agent '{agent_data['name']}'...")
                agent = AgentModel(**agent_data)
                session.add(agent)
            else:
                logger.info(f"Agent '{agent_data['name']}' déjà existant.")
    
        await session.commit()
        logger.info("Agents par défaut insérés avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion des agents par défaut: {str(e)}")
        # Rollback en cas d'erreur
        await session.rollback()
        raise
