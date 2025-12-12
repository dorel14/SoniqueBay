from pydantic_ai import Agent

def build_search_agent(cfg):
    """
    Agent de recherche musicale :
    - retourne SQL filters
    - vector query
    - fulltext query
    """
    return Agent(
        name=cfg.name,
        model=cfg.model,
        system_prompt=cfg.system_prompt,
        response_format=cfg.response_schema
    )
