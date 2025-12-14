from pydantic_ai import Agent
from backend.ai.agents.agent_manager import ensure_agent, ensure_all_agents

def build_orchestrator_agent(cfg):
    """
    Agent maître pour détecter l'intention et router vers les sous-agents
    """
    return Agent(
        name=cfg.name,
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        response_format=cfg.response_schema
    )

async def load_agents_from_db(self):
    await ensure_all_agents()
    # AGENT_CACHE contient les PydanticAI Agent construits
    # replace self.agents mapping
    from backend.ai.agents.agent_manager import AGENT_CACHE
    self.agents = AGENT_CACHE.copy()