from sqlalchemy import select
from backend.api.models.agent_model import AgentModel
from backend.ai.agents.builder import build_agent

class AgentLoader:

    def __init__(self, session):
        self.session = session

    async def load_enabled_agents(self):
        agents = {}

        result = await self.session.execute(
            select(AgentModel).where(AgentModel.enabled)
        )

        for row in result.scalars():
            agents[row.name] = build_agent(row)

        return agents