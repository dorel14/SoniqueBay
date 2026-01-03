from typing import List, Dict, Any
from pydantic_ai import Agent
from backend.ai.ollama import get_ollama_model
from backend.ai.utils.registry import ToolRegistry
from backend.api.models.agent_model import AgentModel
from backend.api.utils.logging import logger


def build_rtcros_prompt(agent_model: AgentModel) -> str:
    """
    Construit le prompt système à partir des champs RTCROS du modèle AgentModel.
    
    Args:
        agent_model: Instance du modèle AgentModel contenant les champs RTCROS
        
    Returns:
        str: Le prompt système construit selon le format RTCROS
    """
    parts = []
    
    # ROLE
    if agent_model.role:
        parts.append(f"ROLE:\n{agent_model.role}")
    
    # TASK
    if agent_model.task:
        parts.append(f"TASK:\n{agent_model.task}")
    
    # CONSTRAINTS
    if agent_model.constraints:
        parts.append(f"CONSTRAINTS:\n{agent_model.constraints}")
    
    # RULES
    if agent_model.rules:
        parts.append(f"RULES:\n{agent_model.rules}")
    
    # OUTPUT_SCHEMA
    if agent_model.output_schema:
        parts.append(f"OUTPUT_SCHEMA:\n{agent_model.output_schema}")
    
    # STATE_STRATEGY
    if agent_model.state_strategy:
        parts.append(f"STATE_STRATEGY:\n{agent_model.state_strategy}")
    
    # Ajout d'instructions générales pour les agents IA
    parts.append("""INSTRUCTIONS:
- Tu es un agent IA spécialisé dans la gestion musicale
- Tu dois toujours répondre de manière concise et précise
- Tu dois utiliser les tools disponibles lorsque c'est approprié
- Tu dois respecter les contraintes et règles définies ci-dessus
- Tu dois retourner les résultats au format spécifié dans OUTPUT_SCHEMA""")
    
    return "\n\n".join(parts)


def build_agent(agent_model: AgentModel) -> Agent:
    """
    Construit un agent PydanticAI à partir d'un modèle AgentModel.
    
    Cette fonction :
    1. Construit le prompt système RTCROS
    2. Récupère les tools autorisés
    3. Configure le modèle LLM avec les paramètres appropriés
    4. Valide la configuration
    
    Args:
        agent_model: Instance du modèle AgentModel
        
    Returns:
        Agent: Agent PydanticAI configuré
        
    Raises:
        ValueError: Si la configuration de l'agent est invalide
    """
    # Validation de base
    if not agent_model.name:
        raise ValueError("Le nom de l'agent est requis")
    
    if not agent_model.model:
        raise ValueError("Le modèle LLM est requis")
    
    if not agent_model.role or not agent_model.task:
        raise ValueError("Les champs ROLE et TASK sont requis pour un agent RTCROS valide")
    
    # Construction du prompt système RTCROS
    system_prompt = build_rtcros_prompt(agent_model)
    
    # Récupération des tools autorisés
    tools = []
    for tool_name in agent_model.tools or []:
        tool_metadata = ToolRegistry.get(tool_name)
        if tool_metadata:
            tools.append(tool_metadata.func)
        else:
            logger.warning(
                f"Tool '{tool_name}' non trouvé dans le registry pour l'agent '{agent_model.name}'",
                extra={
                    "agent_name": agent_model.name,
                    "missing_tool": tool_name,
                    "available_tools": list(ToolRegistry.all().keys())
                }
            )
    
    # Configuration du modèle LLM avec paramètres RTCROS
    try:
        ollama_model = get_ollama_model(
            model_name=agent_model.model,
            num_ctx=agent_model.num_ctx,
            temperature=agent_model.temperature,
            top_p=agent_model.top_p
        )
    except Exception as e:
        logger.error(
            f"Erreur lors de la configuration du modèle LLM pour l'agent '{agent_model.name}'",
            extra={
                "agent_name": agent_model.name,
                "model": agent_model.model,
                "error": str(e)
            },
            exc_info=True
        )
        raise ValueError(f"Impossible de configurer le modèle LLM: {e}")
    
    # Création de l'agent
    try:
        agent = Agent(
            name=agent_model.name,
            model=ollama_model,
            system_prompt=system_prompt,
            tools=tools,
            result_type=agent_model.output_schema  # Support du schema de sortie RTCROS
        )
        
        logger.info(
            f"Agent construit avec succès: {agent_model.name}",
            extra={
                "agent_name": agent_model.name,
                "model": agent_model.model,
                "tools_count": len(tools),
                "temperature": agent_model.temperature,
                "top_p": agent_model.top_p,
                "num_ctx": agent_model.num_ctx
            }
        )
        
        return agent
        
    except Exception as e:
        logger.error(
            f"Erreur lors de la création de l'agent '{agent_model.name}'",
            extra={
                "agent_name": agent_model.name,
                "error": str(e)
            },
            exc_info=True
        )
        raise ValueError(f"Impossible de créer l'agent: {e}")


def build_agent_with_inheritance(agent_model: AgentModel, base_agents: Dict[str, AgentModel]) -> Agent:
    """
    Construit un agent en héritant des capacités d'un agent parent.
    
    Args:
        agent_model: Instance du modèle AgentModel enfant
        base_agents: Dictionnaire des agents parents disponibles
        
    Returns:
        Agent: Agent PydanticAI avec héritage
    """
    if not agent_model.base_agent:
        return build_agent(agent_model)
    
    # Récupération de l'agent parent
    parent_model = base_agents.get(agent_model.base_agent)
    if not parent_model:
        logger.warning(
            f"Agent parent '{agent_model.base_agent}' non trouvé, création sans héritage",
            extra={
                "agent_name": agent_model.name,
                "base_agent": agent_model.base_agent,
                "available_base_agents": list(base_agents.keys())
            }
        )
        return build_agent(agent_model)
    
    # Construction de l'agent parent
    parent_agent = build_agent(parent_model)
    
    # Construction de l'agent enfant avec spécialisation
    child_prompt = _build_specialized_prompt(agent_model, parent_model)
    child_tools = _merge_tools(agent_model, parent_model)
    
    # Création de l'agent spécialisé
    specialized_agent = Agent(
        name=agent_model.name,
        model=parent_agent.model,  # Hérite du modèle du parent
        system_prompt=child_prompt,
        tools=child_tools,
        result_type=agent_model.output_schema
    )
    
    logger.info(
        f"Agent spécialisé créé avec héritage: {agent_model.name} (hérite de {agent_model.base_agent})",
        extra={
            "agent_name": agent_model.name,
            "base_agent": agent_model.base_agent,
            "specialized_tools": len(child_tools) - len(parent_agent.tools) if hasattr(parent_agent, 'tools') else 0
        }
    )
    
    return specialized_agent


def _build_specialized_prompt(child_model: AgentModel, parent_model: AgentModel) -> str:
    """Construit le prompt spécialisé en combinant le parent et l'enfant."""
    parent_prompt = build_rtcros_prompt(parent_model)
    child_prompt = build_rtcros_prompt(child_model)
    
    # Le prompt enfant remplace les parties spécifiques du parent
    return f"""{parent_prompt}

--- SPÉCIALISATION ENFANT ---
{child_prompt}

--- FIN SPÉCIALISATION ---
"""


def _merge_tools(child_model: AgentModel, parent_model: AgentModel) -> List[Any]:
    """Fusionne les tools de l'enfant avec ceux du parent."""
    # Tools du parent
    parent_tools = []
    for tool_name in parent_model.tools or []:
        tool_metadata = ToolRegistry.get(tool_name)
        if tool_metadata:
            parent_tools.append(tool_metadata.func)
    
    # Tools de l'enfant (remplacent ceux du parent si même nom)
    child_tools = []
    for tool_name in child_model.tools or []:
        tool_metadata = ToolRegistry.get(tool_name)
        if tool_metadata:
            child_tools.append(tool_metadata.func)
    
    # Fusion : les tools enfants remplacent les tools parents en cas de conflit
    merged_tools = parent_tools.copy()
    child_tool_names = {ToolRegistry.get(name).name for name in (child_model.tools or []) if ToolRegistry.get(name)}
    
    # Supprimer les tools parents qui sont remplacés
    merged_tools = [
        tool for tool in merged_tools
        if ToolRegistry.get(tool.__name__).name not in child_tool_names
    ]
    
    # Ajouter les tools enfants
    merged_tools.extend(child_tools)
    
    return merged_tools


def validate_agent_configuration(agent_model: AgentModel) -> Dict[str, Any]:
    """
    Valide la configuration d'un agent et retourne un rapport de validation.
    
    Args:
        agent_model: Instance du modèle AgentModel à valider
        
    Returns:
        Dict: Rapport de validation avec succès/échec et détails
    """
    validation_report = {
        "agent_name": agent_model.name,
        "is_valid": True,
        "issues": [],
        "warnings": [],
        "details": {}
    }
    
    # Validation des champs RTCROS obligatoires
    required_fields = ["role", "task"]
    for field in required_fields:
        if not getattr(agent_model, field):
            validation_report["is_valid"] = False
            validation_report["issues"].append(f"Champ RTCROS obligatoire manquant: {field}")
    
    # Validation des tools
    missing_tools = []
    for tool_name in agent_model.tools or []:
        if not ToolRegistry.get(tool_name):
            missing_tools.append(tool_name)
    
    if missing_tools:
        validation_report["warnings"].append(f"Tools manquants: {missing_tools}")
    
    # Validation du modèle LLM
    try:
        # Test de création du modèle (sans l'instancier complètement)
        from backend.ai.ollama import get_ollama_model
        get_ollama_model(
            model_name=agent_model.model,
            num_ctx=agent_model.num_ctx,
            temperature=agent_model.temperature,
            top_p=agent_model.top_p
        )
        validation_report["details"]["model_validation"] = "success"
    except Exception as e:
        validation_report["is_valid"] = False
        validation_report["issues"].append(f"Modèle LLM invalide: {e}")
        validation_report["details"]["model_validation"] = str(e)
    
    # Validation de l'héritage
    if agent_model.base_agent:
        # Cette validation est faite au moment de la construction
        validation_report["details"]["inheritance"] = f"Hérite de: {agent_model.base_agent}"
    
    # Détails de configuration
    validation_report["details"].update({
        "model": agent_model.model,
        "temperature": agent_model.temperature,
        "top_p": agent_model.top_p,
        "num_ctx": agent_model.num_ctx,
        "tools_count": len(agent_model.tools or []),
        "has_output_schema": bool(agent_model.output_schema),
        "has_state_strategy": bool(agent_model.state_strategy)
    })
    
    return validation_report
