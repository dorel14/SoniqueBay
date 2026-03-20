import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.api.models.agent_score_model import AgentScore
from backend.api.services.agent_services import (
    increment_agent_score_usage,
    update_agent_score,
    get_agent_scores_with_metrics,
)
from backend.api.schemas.agent_score_schema import AgentScoreUpdate


@pytest.fixture
async def async_session():
    """Async session mockée pour tests."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(AgentScore.metadata.create_all)
    TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with TestingSessionLocal() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_increment_agent_score_usage(async_session: AsyncSession):
    """Test increment usage/success."""
    score = AgentScore(
        agent_name='test_agent',
        intent='test_intent',
        score=1.0,
        usage_count=5,
        success_count=4,
    )
    async_session.add(score)
    await async_session.commit()

    result = await increment_agent_score_usage(
        async_session, 'test_agent', 'test_intent', success=True
    )
    
    assert result.usage_count == 6
    assert result.success_count == 5
    assert abs(result.score - ((1.0 * 5 + 1.0) / 6)) < 0.001


@pytest.mark.asyncio
async def test_update_agent_score(async_session: AsyncSession):
    """Test update score."""
    score = AgentScore(agent_name='test', intent='test', score=0.5)
    async_session.add(score)
    await async_session.commit()

    data = AgentScoreUpdate(score=0.8, usage_count=10)
    result = await update_agent_score(async_session, 'test', 'test', data)
    
    assert result.score == 0.8
    assert result.usage_count == 10


@pytest.mark.asyncio
async def test_get_agent_scores_with_metrics(async_session: AsyncSession):
    """Test metrics calculées."""
    score1 = AgentScore(agent_name='agent1', intent='intent1', usage_count=10, success_count=8)
    score2 = AgentScore(agent_name='agent1', intent='intent2', usage_count=5, success_count=2)
    async_session.add_all([score1, score2])
    await async_session.commit()

    metrics, total = await get_agent_scores_with_metrics(async_session, agent_name='agent1')

    assert total == 2
    assert len(metrics) == 2
    rates = [m.success_rate for m in metrics]
    assert 0.8 in rates
    assert 0.4 in rates
