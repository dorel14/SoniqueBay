# backend/repos/agent_repo.py
from sqlalchemy import select, func
from backend.api.utils.database import AsyncSessionLocal
from backend.api.models.agent_model import AgentModel
from backend.api.models.agent_score_model import AgentScore as AgentScoreModel
from backend.api.schemas.agent_schema import AgentCreate, AgentUpdate
from backend.api.schemas.agent_score_schema import (
    AgentScoreCreate,
    AgentScoreUpdate,
    AgentScoreWithMetrics,
)
from typing import List, Optional

async def create_agent(data: AgentCreate) -> AgentModel:
    async with AsyncSessionLocal() as session:
        obj = AgentModel(
            name=data.name,
            model=data.model,
            system_prompt=data.system_prompt,
            rules=data.rules,
            tools=[t.dict() for t in data.tools] if data.tools else [],
            ui_blocks=[u.dict() for u in data.ui_blocks] if data.ui_blocks else [],
            response_schema=data.response_schema,
            enabled=data.enabled
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

async def get_agent_by_name(name: str) -> Optional[AgentModel]:
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(AgentModel).where(AgentModel.name == name))
        return q.scalars().first()

async def list_agents() -> List[AgentModel]:
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(AgentModel))
        return q.scalars().all()

async def update_agent(name: str, data: AgentUpdate) -> Optional[AgentModel]:
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(AgentModel).where(AgentModel.name == name))
        obj = q.scalars().first()
        if not obj:
            return None
        for k, v in data.dict(exclude_unset=True).items():
            setattr(obj, k, v)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

async def delete_agent(name: str) -> bool:
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(AgentModel).where(AgentModel.name == name))
        obj = q.scalars().first()
        if not obj:
            return False
        await session.delete(obj)
        await session.commit()
        return True


# Agent Score Services


async def create_agent_score(data: AgentScoreCreate) -> AgentScoreModel:
    """Crée un nouveau score pour un agent."""
    async with AsyncSessionLocal() as session:
        obj = AgentScoreModel(
            agent_name=data.agent_name,
            intent=data.intent,
            score=data.score,
            usage_count=data.usage_count,
            success_count=data.success_count,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def get_agent_score(agent_name: str, intent: str) -> Optional[AgentScoreModel]:
    """Récupère un score d'agent par nom et intention."""
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        return q.scalars().first()


async def list_agent_scores(
    agent_name: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[AgentScoreModel], int]:
    """Liste les scores d'agents avec pagination."""
    async with AsyncSessionLocal() as session:
        q = select(AgentScoreModel)
        
        if agent_name:
            q = q.where(AgentScoreModel.agent_name == agent_name)
        if intent:
            q = q.where(AgentScoreModel.intent == intent)
        
        # Compter le total
        count_q = select([q.with_only_columns([func.count()])])
        count_result = await session.execute(count_q)
        total = count_result.scalar()
        
        # Appliquer pagination
        q = q.limit(limit).offset(offset)
        
        result = await session.execute(q)
        scores = result.scalars().all()
        
        return scores, total


async def update_agent_score(
    agent_name: str, intent: str, data: AgentScoreUpdate
) -> Optional[AgentScoreModel]:
    """Met à jour un score d'agent existant."""
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        obj = q.scalars().first()
        if not obj:
            return None
        
        # Mettre à jour uniquement les champs fournis
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(obj, key, value)
        
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def increment_agent_score_usage(
    agent_name: str, intent: str, success: bool = True
) -> Optional[AgentScoreModel]:
    """Incrémente le compteur d'utilisation et de succès."""
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        obj = q.scalars().first()
        if not obj:
            return None
        
        obj.usage_count += 1
        if success:
            obj.success_count += 1
        
        # Recalculer le score (moyenne pondérée)
        if obj.usage_count > 0:
            obj.score = (obj.score * (obj.usage_count - 1) + (1.0 if success else 0.0)) / obj.usage_count
        
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def delete_agent_score(agent_name: str, intent: str) -> bool:
    """Supprime un score d'agent."""
    async with AsyncSessionLocal() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        obj = q.scalars().first()
        if not obj:
            return False
        await session.delete(obj)
        await session.commit()
        return True


async def get_agent_scores_with_metrics(
    agent_name: Optional[str] = None,
    intent: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[AgentScoreWithMetrics], int]:
    """Récupère les scores avec métriques calculées."""
    async with AsyncSessionLocal() as session:
        q = select(AgentScoreModel)
        
        if agent_name:
            q = q.where(AgentScoreModel.agent_name == agent_name)
        if intent:
            q = q.where(AgentScoreModel.intent == intent)
        
        # Compter le total
        count_q = select([q.with_only_columns([func.count()])])
        count_result = await session.execute(count_q)
        total = count_result.scalar()
        
        # Appliquer pagination
        q = q.limit(limit).offset(offset)
        
        result = await session.execute(q)
        scores = result.scalars().all()
        
        # Convertir en schémas avec métriques
        metrics_scores = []
        for score in scores:
            success_rate = (
                score.success_count / score.usage_count
                if score.usage_count > 0
                else None
            )
            metrics_scores.append(
                AgentScoreWithMetrics(
                    id=score.id,
                    agent_name=score.agent_name,
                    intent=score.intent,
                    score=score.score,
                    usage_count=score.usage_count,
                    success_count=score.success_count,
                    success_rate=success_rate,
                    last_used=None,  # À implémenter si nécessaire
                )
            )
        
        return metrics_scores, total
