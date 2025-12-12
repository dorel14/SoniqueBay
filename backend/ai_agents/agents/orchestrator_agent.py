from pydantic_ai import Agent

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
