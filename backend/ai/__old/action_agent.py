from pydantic_ai import Agent

def build_action_agent(cfg):
    """
    Agent qui déclenche les actions backend
    """
    return Agent(
        name=cfg.name,
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        response_format=cfg.response_schema
    )
