# Plan de correction : Tests agent_scores_api (9/9 FAILED - socket.gaierror)

## Diagnostic
```
FAILED: socket.gaierror: [Errno 11001] getaddrinfo failed 'localhost:5432'
```
**Cause** : Tests sync `TestClient` → ignore override `get_async_session()` → `AsyncSessionLocal()` → `get_async_database_url()` → `postgresql+asyncpg://...@localhost:5432` (DNS échoue).

**Fichiers impactés** :
- `backend/api/services/agent_services.py` : `async with _get_session() as session:` → `AsyncSessionLocal()`
- `tests/conftest.py` : Manque `app.dependency_overrides[AsyncSessionLocal]`
- `tests/integration/api/test_agent_scores_api.py` : Tests sync OK mais deps async non override

## PLAN D'ACTION (3 étapes)

### 1. ✅ FIX conftest.py (priorité HAUTE)
**Objectif** : Override `AsyncSessionLocal` avec session SQLite test.

```python
# Dans fixture client()
class MockAsyncSessionLocal:
    async def __aenter__(self):
        return db_session  # Sync session réutilisée
    async def __aexit__(self, *args):
        pass

app.dependency_overrides[AsyncSessionLocal] = lambda: MockAsyncSessionLocal()
```

### 2. ✅ MIGRER tests vers `httpx.AsyncClient`
**Objectif** : Tests async → utilisent vraiment `override_get_async_session()`.
```
@pytest.mark.asyncio
async def test_create_agent_score(client: httpx.AsyncClient):
    response = await client.post(...)
```

### 3. 🔄 TEST & COMMIT
```
pytest tests/integration/api/test_agent_scores_api.py::test_create_agent_score -v
git add .
git commit -m "fix(tests): override AsyncSessionLocal pour agent_scores_api

Clôture #TODO-agent-tests"
```

## Vérifications post-fix
```
✅ pytest ... 9/9 PASSED
✅ agent_scores table créée SQLite (existe dans test_db_engine)
✅ Pas de DNS/socket errors
✅ Métriques calculées (success_rate)

TODO: Ajouter test `test_agent_score_increment_recalculates_average`

