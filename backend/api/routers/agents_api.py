# backend/api/routes/agents.py
from fastapi import APIRouter, HTTPException, Query
from backend.api.schemas.agent_schema import AgentCreate, AgentUpdate, AgentOut
from backend.api.schemas.agent_score_schema import (
    AgentScoreCreate,
    AgentScoreUpdate,
    AgentScore,
    AgentScoreListResponse,
)
from backend.api.services.agent_services import (
    create_agent,
    get_agent_by_name,
    list_agents,
    update_agent,
    delete_agent,
    create_agent_score,
    get_agent_score,
    list_agent_scores,
    update_agent_score,
    delete_agent_score,
    get_agent_scores_with_metrics,
    increment_agent_score_usage,
)
from typing import List, Optional
from backend.ai.utils.registry import ToolRegistry

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/", response_model=AgentOut)
async def api_create_agent(payload: AgentCreate):
    existing = await get_agent_by_name(payload.name)
    if existing:
        raise HTTPException(400, "Agent exists")
    obj = await create_agent(payload)
    return AgentOut.from_orm(obj)

@router.get("/", response_model=List[AgentOut])
async def api_list_agents():
    rows = await list_agents()
    return [AgentOut.from_orm(r) for r in rows]

@router.get("/{name}", response_model=AgentOut)
async def api_get_agent(name: str):
    obj = await get_agent_by_name(name)
    if not obj:
        raise HTTPException(404, "Not found")
    return AgentOut.from_orm(obj)

@router.put("/{name}", response_model=AgentOut)
async def api_update_agent(name: str, payload: AgentUpdate):
    obj = await update_agent(name, payload)
    if not obj:
        raise HTTPException(404, "Not found")
    return AgentOut.from_orm(obj)

@router.delete("/{name}")
async def api_delete_agent(name: str):
    ok = await delete_agent(name)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"status": "deleted"}

@router.get("/ai/tools")
def list_tools():
    return [
        {
            "name": t.name,
            "description": t.description,
            "expose": t.expose,
            "signature": str(t.signature)
        }
        for t in ToolRegistry.values()
    ]


# Agent Score Endpoints


@router.post("/scores", response_model=AgentScore)
async def api_create_agent_score(payload: AgentScoreCreate):
    """Crée un nouveau score pour un agent."""
    obj = await create_agent_score(payload)
    return AgentScore.from_orm(obj)


@router.get("/scores/{agent_name}/{intent}", response_model=AgentScore)
async def api_get_agent_score(agent_name: str, intent: str):
    """Récupère un score d'agent spécifique."""
    obj = await get_agent_score(agent_name, intent)
    if not obj:
        raise HTTPException(404, "Score not found")
    return AgentScore.from_orm(obj)


@router.get("/scores", response_model=AgentScoreListResponse)
async def api_list_agent_scores(
    agent_name: Optional[str] = Query(None, description="Filtrer par nom d'agent"),
    intent: Optional[str] = Query(None, description="Filtrer par intention"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
):
    """Liste les scores d'agents avec pagination."""
    scores, total = await list_agent_scores(agent_name, intent, limit, offset)
    return AgentScoreListResponse(count=total, results=[AgentScore.from_orm(s) for s in scores])


@router.put("/scores/{agent_name}/{intent}", response_model=AgentScore)
async def api_update_agent_score(
    agent_name: str, intent: str, payload: AgentScoreUpdate
):
    """Met à jour un score d'agent existant."""
    obj = await update_agent_score(agent_name, intent, payload)
    if not obj:
        raise HTTPException(404, "Score not found")
    return AgentScore.from_orm(obj)


@router.patch("/scores/{agent_name}/{intent}/usage", response_model=AgentScore)
async def api_increment_agent_score_usage(
    agent_name: str, intent: str, success: bool = True
):
    """Incrémente le compteur d'utilisation d'un score d'agent."""
    obj = await increment_agent_score_usage(agent_name, intent, success)
    if not obj:
        raise HTTPException(404, "Score not found")
    return AgentScore.from_orm(obj)


@router.delete("/scores/{agent_name}/{intent}")
async def api_delete_agent_score(agent_name: str, intent: str):
    """Supprime un score d'agent."""
    ok = await delete_agent_score(agent_name, intent)
    if not ok:
        raise HTTPException(404, "Score not found")
    return {"status": "deleted"}


@router.get("/scores/metrics", response_model=AgentScoreListResponse)
async def api_get_agent_scores_with_metrics(
    agent_name: Optional[str] = Query(None, description="Filtrer par nom d'agent"),
    intent: Optional[str] = Query(None, description="Filtrer par intention"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
):
    """Récupère les scores avec métriques calculées (taux de succès, etc.)."""
    scores, total = await get_agent_scores_with_metrics(agent_name, intent, limit, offset)
    return AgentScoreListResponse(count=total, results=scores)
