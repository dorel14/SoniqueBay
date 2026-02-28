from pydantic_ai import Agent
from backend.ai.utils.registry import TOOL_REGISTRY
from backend.api.models.agent_model import AgentModel

class AgentLoader:

    def __init__(self, session):
        self.session = session

    def load_agents(self):
        agents = {}
        rows = self.session.query(AgentModel).filter_by(enabled=True)

        for row in rows:
            tools = [
                TOOL_REGISTRY[name]["callable"]
                for name in row.metadata.get("tools", [])
            ]

            agents[row.name] = Agent(
                name=row.name,
                model=f"ollama:{row.model}",
                system_prompt=row.system_prompt,
                tools=tools
            )

        return agents
