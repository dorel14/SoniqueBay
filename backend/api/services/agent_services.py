# backend/repos/agent_repo.py

from typing import List, Optional, cast

from sqlalchemy import func, select

from backend.api.models.agent_model import AgentModel
from backend.api.models.agent_score_model import AgentScore as AgentScoreModel
from backend.api.schemas.agent_schema import AgentCreate, AgentUpdate
from backend.api.schemas.agent_score_schema import (
    AgentScoreCreate,
    AgentScoreUpdate,
    AgentScoreWithMetrics,
)
from backend.api.utils.database import get_async_session





async def create_agent(data: AgentCreate) -> AgentModel:
    async with get_async_session() as session:
        obj = AgentModel(
            name=data.name,
            model=data.model,
            enabled=data.enabled,
            base_agent=data.base_agent,
            role=data.role,
            task=data.task,
            constraints=data.constraints,
            rules=data.rules,
            output_schema=data.output_schema,
            state_strategy=data.state_strategy,
            tools=data.tools or [],
            tags=data.tags or [],
            version=data.version,
            temperature=data.temperature,
            top_p=data.top_p,
            num_ctx=data.num_ctx,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def get_agent_by_name(name: str) -> Optional[AgentModel]:
    async with get_async_session() as session:
        q = await session.execute(select(AgentModel).where(AgentModel.name == name))
        return q.scalars().first()


async def list_agents() -> List[AgentModel]:
    async with get_async_session() as session:
        q = await session.execute(select(AgentModel))
        return list(q.scalars().all())


async def update_agent(name: str, data: AgentUpdate) -> Optional[AgentModel]:
    async with get_async_session() as session:
        q = await session.execute(select(AgentModel).where(AgentModel.name == name))
        obj = q.scalars().first()
        if not obj:
            return None

        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)

        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def delete_agent(name: str) -> bool:
    async with get_async_session() as session:
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
    async with get_async_session() as session:
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
    async with get_async_session() as session:
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
    async with get_async_session() as session:
        q = select(AgentScoreModel)

        if agent_name:
            q = q.where(AgentScoreModel.agent_name == agent_name)
        if intent:
            q = q.where(AgentScoreModel.intent == intent)

        count_q = select(func.count()).select_from(q.subquery())
        count_result = await session.execute(count_q)
        total = int(count_result.scalar() or 0)

        q = q.limit(limit).offset(offset)

        result = await session.execute(q)
        scores = list(result.scalars().all())

        return scores, total


async def update_agent_score(
    agent_name: str, intent: str, data: AgentScoreUpdate
) -> Optional[AgentScoreModel]:
    """Met à jour un score d'agent existant."""
    async with get_async_session() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        obj = q.scalars().first()
        if not obj:
            return None

        update_data = data.model_dump(exclude_unset=True)
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
    async with get_async_session() as session:
        q = await session.execute(
            select(AgentScoreModel).where(
                (AgentScoreModel.agent_name == agent_name)
                & (AgentScoreModel.intent == intent)
            )
        )
        obj = q.scalars().first()
        if not obj:
            return None

        usage_count = int(cast(int, obj.usage_count)) + 1
        success_count = int(cast(int, obj.success_count)) + (1 if success else 0)
        previous_score = float(cast(float, obj.score))

        obj.usage_count = usage_count
        obj.success_count = success_count
        obj.score = (
            previous_score * (usage_count - 1) + (1.0 if success else 0.0)
        ) / usage_count

        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def delete_agent_score(agent_name: str, intent: str) -> bool:
    """Supprime un score d'agent."""
    async with get_async_session() as session:
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
    async with get_async_session() as session:
        q = select(AgentScoreModel)

        if agent_name:
            q = q.where(AgentScoreModel.agent_name == agent_name)
        if intent:
            q = q.where(AgentScoreModel.intent == intent)

        count_q = select(func.count()).select_from(q.subquery())
        count_result = await session.execute(count_q)
        total = int(count_result.scalar() or 0)

        q = q.limit(limit).offset(offset)

        result = await session.execute(q)
        scores = list(result.scalars().all())

        metrics_scores: List[AgentScoreWithMetrics] = []
        for score in scores:
            usage_count = int(cast(int, score.usage_count))
            success_count = int(cast(int, score.success_count))
            success_rate = (success_count / usage_count) if usage_count > 0 else None

            metrics_scores.append(
                AgentScoreWithMetrics(
                    id=int(cast(int, score.id)),
                    agent_name=str(cast(str, score.agent_name)),
                    intent=str(cast(str, score.intent)),
                    score=float(cast(float, score.score)),
                    usage_count=usage_count,
                    success_count=success_count,
                    success_rate=success_rate,
                    last_used=None,  # TODO: relier à un vrai timestamp d'usage si disponible
                )
            )

        return metrics_scores, total
