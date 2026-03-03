from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
import inspect

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.utils.registry import ToolRegistry


async def execute_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    agent_name: Optional[str] = None,
    session: Optional[AsyncSession] = None,
    allowed_agents: Optional[List[str]] = None,
):
    """Exécute un outil enregistré de façon sécurisée.

    Returns a dict matching AgentToolResult schema.
    """
    tool = ToolRegistry.get(tool_name)
    if not tool:
        return {
            "tool_name": tool_name,
            "success": False,
            "result": None,
            "message": "Outil non trouvé",
            "tool_call_id": parameters.get("tool_call_id"),
            "timestamp": datetime.now(timezone.utc),
        }

    # If allowed_agents is provided, enforce it
    if allowed_agents is not None and agent_name is not None:
        if len(allowed_agents) > 0 and agent_name not in allowed_agents:
            return {
                "tool_name": tool_name,
                "success": False,
                "result": None,
                "message": "Outil non autorisé pour cet agent",
                "tool_call_id": parameters.get("tool_call_id"),
                "timestamp": datetime.now(timezone.utc),
            }

    func = tool.get("func")

    try:
        # If the function expects a session parameter and a session was provided, inject it
        sig = inspect.signature(func)
        kwargs = {}
        if "session" in sig.parameters and session is not None:
            kwargs["session"] = session

        # Merge provided parameters as kwargs when possible
        if isinstance(parameters, dict):
            kwargs.update(parameters)

        if inspect.iscoroutinefunction(func):
            result = await func(**kwargs)
        else:
            result = func(**kwargs)

        return {
            "tool_name": tool_name,
            "success": True,
            "result": result if result is not None else {},
            "message": "OK",
            "tool_call_id": parameters.get("tool_call_id"),
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        return {
            "tool_name": tool_name,
            "success": False,
            "result": None,
            "message": str(e),
            "tool_call_id": parameters.get("tool_call_id"),
            "timestamp": datetime.now(timezone.utc),
        }
