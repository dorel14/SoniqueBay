from pydantic_ai import Agent
from backend.ai.ollama import get_ollama_model
from backend.ai.utils.registry import ToolRegistry
from backend.api.models.agent_model import AgentModel

def build_agent(agent_model: AgentModel) -> Agent:
    tools = []

    for tool_name in agent_model.tools:
        tool = ToolRegistry.get(tool_name)
        if tool:
            tools.append(tool["func"])

    ollama_model = get_ollama_model(
        model_name=agent_model.model,
        num_ctx=agent_model.num_ctx
    )

    return Agent(
        name=agent_model.name,
        model=ollama_model,
        system_prompt=agent_model.system_prompt,
        tools=tools,
    )
