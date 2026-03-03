from pydantic_ai import Agent

def build_smalltalk_agent(cfg):
    """
    Agent qui gère le smalltalk et infère le mood
    """
    return Agent(
        name=cfg.name,
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        response_format=cfg.response_schema
    )
