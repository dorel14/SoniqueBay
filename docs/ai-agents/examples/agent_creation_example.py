"""
Exemple complet de création d'un agent IA pour SoniqueBay

Cet exemple montre comment créer un agent spécialisé dans la découverte musicale
en suivant les meilleures pratiques RTCROS et les contraintes RPi4.
"""

from typing import Any, Dict, List

from backend.api.models.artist_model import Artist
from backend.api.models.track_model import Track
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.agents.builder import build_agent, validate_agent_configuration
from backend.ai.utils.decorators import ai_tool
from backend.api.models.agent_model import AgentModel

# ============================================================================
# 1. CRÉATION DES TOOLS
# ============================================================================

@ai_tool(
    name="discover_by_mood",
    description="Découvre des morceaux selon l'humeur de l'utilisateur",
    allowed_agents=["discovery_agent"],
    requires_session=True,
    timeout=25,
    category="discovery",
    tags=["mood", "discovery", "music"],
    validate_params=True,
    track_usage=True
)
async def discover_by_mood(
    mood: str,
    limit: int = 10,
    exclude_recent: bool = True,
    session: AsyncSession = None
) -> List[Dict[str, Any]]:
    """
    Découvre des morceaux selon l'humeur spécifiée.
    
    Args:
        mood: Humeur recherchée (happy, sad, energetic, calm, etc.)
        limit: Nombre maximum de morceaux à retourner
        exclude_recent: Exclure les morceaux écoutés récemment
        session: Session de base de données
    
    Returns:
        List[Dict]: Liste des morceaux avec leurs métadonnées
    """
    # Validation des paramètres
    if limit > 50:
        limit = 50
    
    valid_moods = ["happy", "sad", "energetic", "calm", "romantic", "party"]
    if mood.lower() not in valid_moods:
        raise ValueError(f"Mood invalide. Choix possibles: {', '.join(valid_moods)}")
    
    # Construction de la requête
    query = select(Track).join(Track.artist)
    
    # Filtre par humeur
    query = query.where(
        func.lower(Track.mood) == func.lower(mood)
    )
    
    # Exclusion des morceaux récents si demandé
    if exclude_recent:
        # Logique pour exclure les morceaux écoutés dans les 7 derniers jours
        # (à adapter selon votre modèle de données)
        pass
    
    # Tri aléatoire pour la découverte
    query = query.order_by(func.random()).limit(limit)
    
    # Exécution
    result = await session.execute(query)
    tracks = result.scalars().all()
    
    # Formatage du résultat
    return [
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist.name,
            "album": track.album.title if track.album else None,
            "duration": track.duration,
            "bpm": track.bpm,
            "mood": track.mood,
            "similarity_score": None  # À calculer si besoin
        }
        for track in tracks
    ]


@ai_tool(
    name="get_similar_artists",
    description="Trouve des artistes similaires à un artiste donné",
    allowed_agents=["discovery_agent"],
    requires_session=True,
    timeout=30,
    category="discovery",
    tags=["artist", "similarity", "discovery"]
)
async def get_similar_artists(
    artist_id: int,
    limit: int = 5,
    session: AsyncSession = None
) -> List[Dict[str, Any]]:
    """
    Trouve des artistes similaires en utilisant les tags et le style.
    
    Args:
        artist_id: ID de l'artiste de référence
        limit: Nombre d'artistes similaires à retourner
        session: Session de base de données
    
    Returns:
        List[Dict]: Liste des artistes similaires
    """
    # Récupération de l'artiste de référence
    artist_query = select(Artist).where(Artist.id == artist_id)
    result = await session.execute(artist_query)
    reference_artist = result.scalar_one_or_none()
    
    if not reference_artist:
        raise ValueError(f"Artiste avec ID {artist_id} non trouvé")
    
    # Recherche d'artistes similaires par genre et tags
    similar_query = select(Artist).where(
        Artist.id != artist_id,
        Artist.genre == reference_artist.genre
    ).limit(limit)
    
    result = await session.execute(similar_query)
    similar_artists = result.scalars().all()
    
    return [
        {
            "id": artist.id,
            "name": artist.name,
            "genre": artist.genre,
            "similarity_reason": f"Partage le même genre: {artist.genre}"
        }
        for artist in similar_artists
    ]


@ai_tool(
    name="suggest_new_releases",
    description="Propose les dernières sorties selon les goûts de l'utilisateur",
    allowed_agents=["discovery_agent"],
    requires_session=True,
    timeout=20,
    category="discovery",
    tags=["new", "releases", "discovery"]
)
async def suggest_new_releases(
    user_id: int,
    days_back: int = 30,
    limit: int = 10,
    session: AsyncSession = None
) -> List[Dict[str, Any]]:
    """
    Suggère les nouvelles sorties basées sur les préférences utilisateur.
    
    Args:
        user_id: ID de l'utilisateur
        days_back: Nombre de jours à considérer pour les nouvelles sorties
        limit: Nombre de suggestions à retourner
        session: Session de base de données
    
    Returns:
        List[Dict]: Liste des nouvelles sorties suggérées
    """
    from datetime import datetime, timedelta
    
    # Date limite pour les nouvelles sorties
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Logique pour trouver les goûts de l'utilisateur
    # (à adapter selon votre modèle de données)
    user_preferences = await get_user_music_preferences(user_id, session)
    
    # Recherche de nouvelles sorties selon les préférences
    query = select(Track).join(Track.album).where(
        Track.created_at >= cutoff_date,
        Track.album.release_date >= cutoff_date
    )
    
    # Filtrage selon les préférences (exemple simplifié)
    if user_preferences.get("genres"):
        query = query.join(Track.artist).where(
            Artist.genre.in_(user_preferences["genres"])
        )
    
    query = query.limit(limit)
    
    result = await session.execute(query)
    new_tracks = result.scalars().all()
    
    return [
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist.name,
            "album": track.album.title,
            "release_date": track.album.release_date,
            "reason": "Nouvelle sortie dans vos genres préférés"
        }
        for track in new_tracks
    ]


# ============================================================================
# 2. CONFIGURATION DE L'AGENT RTCROS
# ============================================================================

def create_discovery_agent_model() -> AgentModel:
    """
    Crée le modèle de configuration RTCROS pour l'agent de découverte.
    """
    return AgentModel(
        name="discovery_agent",
        model="phi3:mini",
        
        # RTCROS Configuration
        role="""
Expert en découverte musicale et analyse des préférences utilisateur.
Spécialiste de la musique émergente et des artistes similaires.
Connaissant un large éventail de genres et d'artistes.
        """.strip(),
        
        task="""
Comprendre les goûts musicaux de l'utilisateur à travers la conversation.
Proposer des découvertes musicales pertinentes et variées.
Expliquer les choix de recommandations.
Adapter les suggestions en fonction des retours utilisateur.
        """.strip(),
        
        constraints="""
- Ne jamais suggérer de musique inappropriée ou choquante
- Ne pas inventer d'artistes ou de morceaux inexistants
- Toujours vérifier la disponibilité dans la bibliothèque
- Respecter les limites d'âge et de contenu
- Ne pas suggérer plus de 10 morceaux à la fois
        """.strip(),
        
        rules="""
1. Poser des questions pour affiner les préférences musicales
2. Proposer 3-7 suggestions maximum par interaction
3. Expliquer chaque suggestion avec une raison claire
4. Adapter le ton et le style selon l'humeur détectée
5. Proposer des alternatives si l'utilisateur refuse une suggestion
6. Alterner entre différents genres pour varier les découvertes
7. Tenir compte de l'historique d'écoute pour éviter les doublons
        """.strip(),
        
        output_schema="""
{
  "suggestions": [
    {
      "type": "track|artist|album",
      "id": "int",
      "title": "string",
      "artist": "string",
      "reason": "string",
      "similarity_score": "float|null",
      "metadata": {
        "duration": "int|null",
        "bpm": "int|null",
        "mood": "string|null",
        "genre": "string|null"
      }
    }
  ],
  "total_found": "int",
  "filters_used": ["string"],
  "explanation": "string"
}
        """.strip(),
        
        state_strategy="""
Maintenir le contexte des préférences utilisateur sur toute la conversation.
Se souvenir des goûts exprimés, des refus et des likes.
Adapter progressivement les suggestions selon les feedbacks.
Gérer les clarifications nécessaires pour affiner les recherches.
Conserver l'historique des suggestions pour éviter les doublons.
        """.strip(),
        
        # Configuration LLM
        temperature=0.3,  # Équilibre créativité/précision
        top_p=0.85,       # Sampling nucleus
        num_ctx=2048,     # Contexte suffisant pour le dialogue
        
        # Tools disponibles
        tools=[
            "discover_by_mood",
            "get_similar_artists", 
            "suggest_new_releases"
        ],
        
        # Métadonnées
        tags=["music", "discovery", "recommendation"],
        version="1.0"
    )


# ============================================================================
# 3. FONCTIONS D'AIDE
# ============================================================================

async def get_user_music_preferences(user_id: int, session: AsyncSession) -> Dict[str, Any]:
    """
    Récupère les préférences musicales d'un utilisateur.
    À adapter selon votre modèle de données.
    """
    # Exemple de logique (à adapter selon votre base)
    preferences = {
        "genres": ["electronic", "rock", "jazz"],
        "favorite_artists": [1, 5, 12],
        "moods": ["energetic", "calm"],
        "bpm_range": [100, 140]
    }
    return preferences


async def validate_and_create_agent(session: AsyncSession) -> Any:
    """
    Valide et crée l'agent de découverte.
    
    Returns:
        Agent: Agent PydanticAI prêt à l'emploi
    """
    # 1. Création du modèle
    agent_model = create_discovery_agent_model()
    
    # 2. Validation de la configuration
    validation = validate_agent_configuration(agent_model)
    
    if not validation["is_valid"]:
        raise ValueError(f"Configuration invalide: {validation['issues']}")
    
    print("✅ Configuration RTCROS validée")
    print(f"   - Tools: {len(agent_model.tools)}")
    print(f"   - Température: {agent_model.temperature}")
    print(f"   - Contexte: {agent_model.num_ctx}")
    
    # 3. Construction de l'agent
    agent = build_agent(agent_model)
    
    print("✅ Agent construit avec succès")
    print(f"   - Nom: {agent.name}")
    print(f"   - Modèle: {agent.model}")
    
    return agent


async def test_discovery_agent():
    """
    Fonction de test pour l'agent de découverte.
    """
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Setup de la session (à adapter selon votre configuration)
    engine = create_async_engine("postgresql://user:password@localhost/soniquebay")
    
    async with engine.begin() as conn:
        # Création de l'agent
        agent = await validate_and_create_agent(conn)
        
        # Test 1: Découverte par humeur
        print("\n🎵 Test 1: Découverte par humeur")
        result = await agent.run(
            "Je me sens énergique aujourd'hui, trouve-moi de la musique pour danser",
            context={}
        )
        print(f"Résultat: {result}")
        
        # Test 2: Artistes similaires
        print("\n🎸 Test 2: Artistes similaires")
        result = await agent.run(
            "J'aime Daft Punk, trouve-moi des artistes similaires",
            context={}
        )
        print(f"Résultat: {result}")
        
        # Test 3: Nouveautés
        print("\n🆕 Test 3: Nouveautés")
        result = await agent.run(
            "Quoi de neuf dans la musique électronique ces derniers temps ?",
            context={}
        )
        print(f"Résultat: {result}")


# ============================================================================
# 4. UTILISATION EN PRODUCTION
# ============================================================================

class MusicDiscoveryService:
    """
    Service de découverte musicale utilisant l'agent IA.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent = None
    
    async def initialize(self):
        """Initialise le service avec l'agent."""
        self.agent = await validate_and_create_agent(self.session)
    
    async def discover_music(self, user_message: str, user_id: int = None) -> Dict[str, Any]:
        """
        Découvre de la musique selon le message utilisateur.
        
        Args:
            user_message: Message de l'utilisateur
            user_id: ID de l'utilisateur (optionnel)
        
        Returns:
            Dict: Résultat de la découverte
        """
        if not self.agent:
            await self.initialize()
        
        # Contexte enrichi avec les infos utilisateur
        context = {}
        if user_id:
            preferences = await get_user_music_preferences(user_id, self.session)
            context["user_preferences"] = preferences
        
        # Exécution de l'agent
        result = await self.agent.run(user_message, context=context)
        
        return result
    
    async def discover_streaming(self, user_message: str, user_id: int = None):
        """
        Découverte en streaming pour une expérience interactive.
        """
        if not self.agent:
            await self.initialize()
        
        context = {}
        if user_id:
            preferences = await get_user_music_preferences(user_id, self.session)
            context["user_preferences"] = preferences
        
        async for chunk in self.agent.stream(user_message, context=context):
            yield chunk


# ============================================================================
# 5. EXEMPLE D'INTÉGRATION FASTAPI
# ============================================================================

"""
Exemple d'intégration dans FastAPI (à placer dans api_app.py) :

from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import get_db_session
from backend.api.schemas.discovery_schema import DiscoveryRequest, DiscoveryResponse

router = APIRouter()

@router.post("/api/discover", response_model=DiscoveryResponse)
async def discover_music(
    request: DiscoveryRequest,
    session: AsyncSession = Depends(get_db_session)
):
    \"\"\"Endpoint de découverte musicale.\"\"\"
    try:
        service = MusicDiscoveryService(session)
        result = await service.discover_music(
            request.message, 
            request.user_id
        )
        return DiscoveryResponse(success=True, result=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/discover")
async def discover_music_ws(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_db_session)
):
    \"\"\"WebSocket pour la découverte en streaming.\"\"\"
    await websocket.accept()
    
    service = MusicDiscoveryService(session)
    await service.initialize()
    
    try:
        while True:
            message = await websocket.receive_text()
            async for chunk in service.discover_streaming(message):
                await websocket.send_json(chunk)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
"""

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_discovery_agent())