from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.api.models.agent_score_model import AgentScore
import math

class IntentRouter:

    def __init__(self):
        pass

    async def choose_agent(
        self,
        session: AsyncSession,
        intent: str,
        candidate_agents: list[str],
    ) -> str:
        """
        Choisit le meilleur agent selon le scoring BDD
        """
        scores = []

        for agent_name in candidate_agents:
            stmt = select(AgentScore).where(
                AgentScore.agent_name == agent_name,
                AgentScore.intent == intent,
            )
            res = await session.execute(stmt)
            row = res.scalar_one_or_none()

            if not row:
                # score par défaut
                final = 1.0
            else:
                final = (
                    row.score
                    + math.log(row.usage_count + 1)
                    + (row.success_count / max(1, row.usage_count))
                )

            scores.append((agent_name, final))

        # meilleur score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]

    async def register_usage(
        self,
        session: AsyncSession,
        agent_name: str,
        intent: str,
        success: bool = True,
    ):
        """
        Apprentissage léger après exécution
        """
        stmt = select(AgentScore).where(
            AgentScore.agent_name == agent_name,
            AgentScore.intent == intent,
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()

        if not row:
            row = AgentScore(
                agent_name=agent_name,
                intent=intent,
                score=1.0,
                usage_count=0,
                success_count=0,
            )
            session.add(row)

        row.usage_count += 1
        if success:
            row.success_count += 1

        await session.commit()
    
    async def has_scores(self, session, intent: str) -> bool:
        from sqlalchemy import select
        from backend.api.models.agent_score_model import AgentScore

        res = await session.execute(
            select(AgentScore).where(AgentScore.intent == intent)
        )
        return res.first() is not None