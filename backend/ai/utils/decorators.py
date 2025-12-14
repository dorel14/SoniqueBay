from backend.ai.utils.registry import ToolRegistry

def ai_tool(
    name: str,
    description: str,
):
    def decorator(func):
        ToolRegistry.register(
            name=name,
            description=description,
            func=func
        )
        return func
    return decorator
