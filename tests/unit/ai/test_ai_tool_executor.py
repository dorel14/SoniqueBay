import pytest

from backend.ai.utils.registry import ToolRegistry
from backend.ai.tool_executor import execute_tool


def teardown_function(fn):
    # Clear registry between tests
    try:
        ToolRegistry._tools = {}
    except Exception:
        pass


@pytest.mark.asyncio
async def test_execute_sync_tool():
    def sync_double(x: int):
        return {"value": x * 2}

    ToolRegistry.register(name="sync_double", description="double", func=sync_double)

    res = await execute_tool("sync_double", {"x": 3})
    assert res["success"] is True
    assert isinstance(res["result"], dict)
    assert res["result"]["value"] == 6


@pytest.mark.asyncio
async def test_execute_async_tool():
    async def async_inc(x: int):
        return {"value": x + 1}

    ToolRegistry.register(name="async_inc", description="inc", func=async_inc)

    res = await execute_tool("async_inc", {"x": 4})
    assert res["success"] is True
    assert res["result"]["value"] == 5


@pytest.mark.asyncio
async def test_tool_not_found():
    res = await execute_tool("no_such_tool", {})
    assert res["success"] is False
    assert "Outil non trouvé" in res["message"]
