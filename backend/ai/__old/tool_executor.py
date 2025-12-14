import httpx
from backend.ai.utils.registry import TOOL_REGISTRY

class ToolExecutor:

    async def execute(self, name: str, args: dict):
        tool = TOOL_REGISTRY[name]

        if tool.expose == "service":
            return await tool.func(**args)

        if tool.expose == "endpoint":
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"http://backend{tool.func.__route__}",
                    json=args
                )
                return resp.json()
        raise ValueError(f"Unknown tool expose type: {tool.expose}")