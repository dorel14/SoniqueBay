from pydantic_ai import Agent

def build_playlist_agent(cfg):
    """
    Agent de génération de playlist
    """
    return Agent(
        name=cfg.name,
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        response_format=cfg.response_schema
    )
