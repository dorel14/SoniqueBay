import os
import pytest

from backend.api.utils.database import (
    get_async_session,
    get_db,
)


@pytest.fixture(autouse=True)
def testing_env():
    """Force TESTING=true pour tous les tests."""

    os.environ["TESTING"] = "true"
    yield
    del os.environ["TESTING"]


class TestDatabaseSessions:
    """Tests unitaires des sessions/générateurs database."""

    def test_get_db_raises_in_test_mode(self):
        """Vérifie que get_db lève RuntimeError en mode test."""

        with pytest.raises(RuntimeError, match=r"get_db.*test mode"):
            next(get_db())

    @pytest.mark.asyncio
    async def test_get_async_session_raises_in_test_mode(self):
        """Vérifie que get_async_session lève RuntimeError en mode test."""

        with pytest.raises(RuntimeError, match=r"get_async_session.*test mode"):
            async for _ in get_async_session():
                pass

    def test_sessionlocal_is_none_in_test(self):
        """Vérifie SessionLocal/AsyncSessionLocal == None en mode test."""

        from backend.api.utils.database import SessionLocal, AsyncSessionLocal
        assert SessionLocal is None
        assert AsyncSessionLocal is None

    def test_get_db_raises_when_sessionlocal_none(self):
        """Vérifie la garde explicite SessionLocal is None."""

        with pytest.raises(RuntimeError, match=r"get_db.*test mode|SessionLocal is None"):
            next(get_db())

    @pytest.mark.asyncio
    async def test_get_async_session_raises_when_asyncsessionlocal_none(self):
        """Vérifie la garde explicite AsyncSessionLocal is None."""

        with pytest.raises(RuntimeError, match=r"AsyncSessionLocal is None"):
            async for _ in get_async_session():
                pass


@pytest.mark.skip("Runtime seulement - nécessite DB réelle")
class TestRuntimeSessions:
    """Tests runtime (hors TESTING=true)."""

    @pytest.fixture(autouse=True)
    def runtime_env(self):
        if "TESTING" in os.environ:
            del os.environ["TESTING"]

    def test_get_db_runtime(self):
        """Test get_db() en runtime (non-test)."""

        try:
            gen = get_db()
            session = next(gen)
            assert hasattr(session, "close")
            session.close()
        except RuntimeError as e:
            pytest.skip(f"Runtime test skipped: {e}")

    @pytest.mark.asyncio
    async def test_get_async_session_runtime(self):
        """Test get_async_session() en runtime."""

        try:
            db_gen = get_async_session()
            async for db in db_gen:
                assert hasattr(db, "commit")
                await db.close()
                break
        except RuntimeError as e:
            pytest.skip(f"Runtime test skipped: {e}")


# Tests d'intégration pour agent_services
@pytest.mark.asyncio
async def test_agent_services_uses_correct_session():
    """Vérifie que agent_services lève erreur en test mode."""

    from backend.api.services.agent_services import create_agent, AgentCreate

    data = AgentCreate(
        name="test-agent",
        model="gpt-4o-mini",
        enabled=True,
        role="test",
        task="test task",
        output_schema="{}",
    )

    with pytest.raises(RuntimeError, match=r"get_async_session.*test mode"):
        await create_agent(data)
