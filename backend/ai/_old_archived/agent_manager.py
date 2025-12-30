# backend/agent_manager.py
import json
from typing import Dict, Any, Optional
from backend.api.services.agent_services import get_agent_by_name, list_agents
from backend.api.models.agent_model import AgentModel
from backend.ai.models.ollama_stream_model import OllamaStreamModel
from pydantic_ai import Agent as PydanticAgent

# cache in-memory of built agents
AGENT_CACHE: Dict[str, PydanticAgent] = {}

def build_system_prompt(db_agent: AgentModel) -> str:
    # assemble RTCROS style prompt from fields
    rules_text = "\n".join(f"- {r}" for r in (db_agent.rules or []))
    tools_text = "\n".join(f"* {t.get('name')}: {t.get('description','')}" for t in (db_agent.tools or []))
    ui_blocks = json.dumps([b for b in (db_agent.ui_blocks or [])], indent=2)
    return f"""ROLE:
You are {db_agent.name}.

TASK:
{db_agent.system_prompt}

RULES:
{rules_text}

TOOLS:
{tools_text}

UI_BLOCKS:
{ui_blocks}

OUTPUT_SCHEMA:
{json.dumps(db_agent.response_schema or {}, indent=2)}
"""

async def ensure_agent(name: str) -> Optional[PydanticAgent]:
    if name in AGENT_CACHE:
        return AGENT_CACHE[name]
    db_agent = await get_agent_by_name(name)
    if not db_agent or not db_agent.enabled:
        return None
    system_prompt = build_system_prompt(db_agent)
    # create Ollama streaming model
    ollama_model = OllamaStreamModel(db_agent.model)
    # If pydantic_ai accepts a Pydantic model/class as response_format, you can pass the JSON schema.
    response_format = db_agent.response_schema
    agent = PydanticAgent(name=db_agent.name, model=ollama_model, system_prompt=system_prompt, response_format=response_format)
    AGENT_CACHE[name] = agent
    return agent

async def ensure_all_agents():
    rows = await list_agents()
    for r in rows:
        await ensure_agent(r.name)
