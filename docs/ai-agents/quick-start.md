# Guide de Démarrage Rapide - Agents IA SoniqueBay

## Table des matières

- [Installation](#installation)
- [Premiers pas](#premiers-pas)
- [Création de votre premier agent](#création-de-votre-premier-agent)
- [Création de votre premier tool](#création-de-votre-premier-tool)
- [Utilisation en production](#utilisation-en-production)
- [Dépannage](#dépannage)

## Installation

### Prérequis

- Python 3.10+
- PostgreSQL
- Redis
- Docker (optionnel)

### Installation des dépendances

```bash
# Backend AI dependencies
pip install -r backend/ai/requirements.txt

# Tests
pip install pytest pytest-asyncio pytest-cov

# Monitoring (optionnel)
pip install psutil
```

### Configuration de l'environnement

```bash
# Variables d'environnement
export AGENT_MODEL="phi3:mini"
export DATABASE_URL="postgresql://user:password@localhost/soniquebay"
export REDIS_URL="redis://localhost:6379/0"
```

## Premiers pas

### 1. Initialisation du système

```python
from sqlalchemy.ext.asyncio import create_async_engine
from backend.ai.loader import AgentLoader
from backend.ai.orchestrator import Orchestrator

# Création de la session
engine = create_async_engine(os.getenv("DATABASE_URL"))
async with engine.begin() as conn:
    # Initialisation du loader
    loader = AgentLoader(conn)
    
    # Chargement des agents
    agents = await loader.load_enabled_agents()
    
    # Création de l'orchestrateur
    orchestrator = Orchestrator(conn)
```

### 2. Test de base

```python
# Test simple
message = "Bonjour, comment ça va ?"
result = await orchestrator.handle(message)
print(f"Réponse: {result}")

# Test en streaming
async for chunk in orchestrator.handle_stream("Parle moi de musique"):
    if chunk.get("type") == "text":
        print(f"Agent: {chunk.get('content')}")
```

## Création de votre premier agent

### Étape 1 : Créer le modèle en base de données

```sql
-- Création de l'agent dans la base
INSERT INTO ai_agents (
    name, 
    model, 
    role, 
    task, 
    constraints, 
    rules, 
    output_schema,
    enabled,
    temperature,
    top_p,
    num_ctx
) VALUES (
    'music_expert',
    'phi3:mini',
    'Expert musical spécialisé dans les recommandations',
    'Proposer des morceaux en fonction des goûts et de l''humeur',
    'Ne jamais suggérer de musique inappropriée ou inexistante',
    '["Toujours demander les préférences", "Proposer 3-5 suggestions", "Expliquer chaque choix"]',
    '{"recommendations": "list", "reasoning": "string"}',
    true,
    0.3,
    0.8,
    2048
);
```

### Étape 2 : Créer les tools associés

```python
from backend.ai.utils.decorators import ai_tool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api.models.track_model import Track

@ai_tool(
    name="get_user_preferences",
    description="Récupère les préférences musicales d'un utilisateur",
    allowed_agents=["music_expert"],
    requires_session=True
)
async def get_user_preferences(user_id: int, session: AsyncSession):
    """Récupère les préférences utilisateur."""
    # Logique de récupération des préférences
    preferences = await get_user_music_preferences(user_id, session)
    return preferences

@ai_tool(
    name="search_similar_tracks",
    description="Recherche des morceaux similaires à un morceau donné",
    allowed_agents=["music_expert"],
    requires_session=True
)
async def search_similar_tracks(track_id: int, limit: int = 10, session: AsyncSession):
    """Recherche des morceaux similaires."""
    # Logique de recherche vectorielle
    similar_tracks = await find_similar_tracks(track_id, limit, session)
    return similar_tracks

@ai_tool(
    name="get_genre_recommendations",
    description="Propose des morceaux par genre musical",
    allowed_agents=["music_expert"],
    requires_session=True
)
async def get_genre_recommendations(genre: str, mood: str = None, session: AsyncSession):
    """Recommandations par genre et humeur."""
    query = select(Track).join(Track.artist).where(Track.artist.genre == genre)
    
    if mood:
        query = query.where(Track.mood == mood)
    
    result = await session.execute(query.limit(20))
    return result.scalars().all()
```

### Étape 3 : Associer les tools à l'agent

```sql
-- Mise à jour des tools de l'agent
UPDATE ai_agents 
SET tools = ['get_user_preferences', 'search_similar_tracks', 'get_genre_recommendations']
WHERE name = 'music_expert';
```

### Étape 4 : Tester l'agent

```python
# Rechargement de l'agent
agent = await loader.load_agent_by_name("music_expert")

# Test de base
result = await agent.run(
    "Je cherche de la musique electro pour faire la fête",
    context={}
)
print(result)

# Test en streaming
async for chunk in agent.stream("Quelles sont les meilleures chansons electro ?", context={}):
    print(f"Chunk: {chunk}")
```

## Création de votre premier tool

### Exemple : Tool de recherche de playlists

```python
from backend.ai.utils.decorators import ai_tool
from backend.api.models.playlist_model import Playlist
from sqlalchemy import select, func

@ai_tool(
    name="search_playlists",
    description="Recherche des playlists selon critères",
    allowed_agents=["playlist_agent", "music_expert"],
    requires_session=True,
    timeout=30,
    category="playlist",
    tags=["search", "music", "playlist"],
    validate_params=True,
    track_usage=True
)
async def search_playlists(
    query: str = None,
    genre: str = None,
    mood: str = None,
    min_duration: int = None,
    max_duration: int = None,
    limit: int = 20,
    session: AsyncSession = None
):
    """
    Recherche des playlists selon différents critères.
    
    Args:
        query: Texte à rechercher dans le nom/description
        genre: Genre musical de la playlist
        mood: Humeur de la playlist
        min_duration: Durée minimale en secondes
        max_duration: Durée maximale en secondes
        limit: Nombre maximum de résultats
        session: Session de base de données
    
    Returns:
        List[Playlist]: Liste des playlists correspondantes
    """
    # Validation des paramètres
    if limit > 100:
        limit = 100
    
    if min_duration and max_duration and min_duration > max_duration:
        raise ValueError("min_duration ne peut pas être supérieur à max_duration")
    
    # Construction de la requête
    query_obj = select(Playlist)
    
    if query:
        query_obj = query_obj.where(
            func.lower(Playlist.name).contains(func.lower(query)) |
            func.lower(Playlist.description).contains(func.lower(query))
        )
    
    if genre:
        query_obj = query_obj.where(Playlist.genre == genre)
    
    if mood:
        query_obj = query_obj.where(Playlist.mood == mood)
    
    if min_duration:
        query_obj = query_obj.where(Playlist.duration >= min_duration)
    
    if max_duration:
        query_obj = query_obj.where(Playlist.duration <= max_duration)
    
    # Exécution de la requête
    result = await session.execute(query_obj.limit(limit))
    playlists = result.scalars().all()
    
    # Formatage du résultat
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "genre": p.genre,
            "mood": p.mood,
            "duration": p.duration,
            "track_count": len(p.tracks)
        }
        for p in playlists
    ]
```

### Test du tool

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test_tool():
    # Setup session
    engine = create_async_engine("postgresql://user:password@localhost/soniquebay")
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Test du tool
        result = await search_playlists(
            query="electro",
            genre="electronic",
            limit=5,
            session=session
        )
        
        print(f"Found {len(result)} playlists:")
        for playlist in result:
            print(f"- {playlist['name']} ({playlist['genre']})")

# Exécution
asyncio.run(test_tool())
```

## Utilisation en production

### 1. Configuration du monitoring

```python
from backend.ai.utils.registry import ToolRegistry
from backend.ai.orchestrator import Orchestrator

# Endpoint de monitoring FastAPI
@app.get("/api/ai/health")
async def get_ai_health():
    """Endpoint de monitoring de santé IA."""
    return {
        "registry": ToolRegistry.get_health_report(),
        "orchestrator": orchestrator.get_health_report(),
        "performance": orchestrator.get_performance_metrics()
    }

# Endpoint de statistiques
@app.get("/api/ai/stats")
async def get_ai_stats():
    """Endpoint de statistiques d'utilisation."""
    return ToolRegistry.get_statistics()
```

### 2. Configuration des alertes

```python
import logging
from backend.api.utils.logging import setup_logging

# Configuration du logging
setup_logging()

# Alertes performance
async def check_performance_alerts():
    """Vérifie les alertes de performance."""
    stats = ToolRegistry.get_statistics()
    
    if stats["error_rate"] > 0.1:  # > 10% d'erreurs
        logging.critical(
            f"Taux d'erreur élevé: {stats['error_rate']:.2%}",
            extra={"error_rate": stats["error_rate"]}
        )
    
    performance = orchestrator.get_performance_metrics()
    if performance["avg_response_time"] > 5.0:  # > 5s
        logging.warning(
            f"Temps de réponse élevé: {performance['avg_response_time']:.2f}s",
            extra={"response_time": performance["avg_response_time"]}
        )
```

### 3. Déploiement Docker

```dockerfile
# Dockerfile pour le backend IA
FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances
COPY backend/ai/requirements.txt .
RUN pip install -r requirements.txt

# Copie du code
COPY backend/ai/ ./ai/
COPY backend/api/ ./api/

# Configuration
ENV PYTHONPATH=/app
ENV AGENT_MODEL=phi3:mini

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from ai.orchestrator import Orchestrator; print('OK')"

CMD ["python", "-m", "api.api_app"]
```

### 4. Configuration Nginx (optionnel)

```nginx
# Configuration Nginx pour le load balancing
upstream ai_backend {
    server ai-backend-1:8000;
    server ai-backend-2:8000;
}

server {
    listen 80;
    
    location /api/ai/ {
        proxy_pass http://ai_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws {
        proxy_pass http://ai_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Dépannage

### Problèmes courants

#### 1. Agent non trouvé

```python
# Vérification de l'agent
loader = AgentLoader(session)
agent = await loader.load_agent_by_name("my_agent")

if agent is None:
    print("Agent non trouvé ou désactivé")
    
    # Vérification en base
    result = await session.execute(
        select(AgentModel).where(AgentModel.name == "my_agent")
    )
    agent_db = result.scalar_one_or_none()
    
    if agent_db:
        print(f"Agent trouvé mais enabled={agent_db.enabled}")
    else:
        print("Agent non présent en base")
```

#### 2. Tool non enregistré

```python
# Vérification du registry
from backend.ai.utils.registry import ToolRegistry

tools = ToolRegistry.all()
if "my_tool" not in tools:
    print("Tool non enregistré")
    
    # Vérification de l'import
    try:
        from my_module import my_tool_function
        print("Fonction importée avec succès")
    except ImportError as e:
        print(f"Erreur d'import: {e}")
```

#### 3. Problèmes de performance

```python
# Monitoring des performances
runtime = orchestrator._get_or_create_runtime("problematic_agent")
health = runtime.get_health_status()

print(f"Erreurs consécutives: {health['consecutive_errors']}")
print(f"Temps depuis dernière erreur: {health['time_since_last_error']}")
print(f"Taille buffer: {health['buffer_size']}")

# Si problème de mémoire
import gc
gc.collect()  # Force le garbage collection
```

#### 4. Erreurs de streaming

```python
# Debug streaming
async def debug_streaming():
    try:
        async for chunk in agent.stream("test", context):
            print(f"Chunk reçu: {chunk}")
    except Exception as e:
        print(f"Erreur streaming: {e}")
        import traceback
        traceback.print_exc()
```

### Logs utiles

```python
# Logs à surveiller
logging.getLogger('backend.ai.runtime').setLevel(logging.DEBUG)
logging.getLogger('backend.ai.orchestrator').setLevel(logging.DEBUG)
logging.getLogger('backend.ai.registry').setLevel(logging.DEBUG)

# Logs spécifiques
logger = logging.getLogger('backend.ai')
logger.info("Démarrage de l'agent", extra={"agent_name": "test_agent"})
logger.error("Erreur agent", extra={"agent_name": "test_agent", "error": str(error)})
```

### Commandes de diagnostic

```bash
# Vérification de la santé
curl http://localhost:8000/api/ai/health

# Statistiques d'utilisation
curl http://localhost:8000/api/ai/stats

# Test d'un agent spécifique
curl -X POST http://localhost:8000/api/ai/test \
  -H "Content-Type: application/json" \
  -d '{"agent": "music_expert", "message": "Test message"}'
```

## Support

Pour toute question ou problème :

1. **Consultez les logs** : `tail -f logs/ai.log`
2. **Vérifiez le monitoring** : `/api/ai/health`
3. **Testez les composants** : Scripts de test dans `tests/`
4. **Documentation** : `docs/ai-agents/README.md`

N'hésitez pas à créer une issue GitHub avec :
- Description du problème
- Logs pertinents
- Étapes pour reproduire
- Version de Python et des dépendances