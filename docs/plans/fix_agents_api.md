# Fix Agents API - Plan de Correction des Tests

## État Initial (test_results.txt)
```
FAILED integration\api\test_agents_api.py::test_create_agent_score - TypeError: 'async_generator' object does not support the asynchronous context manager protocol
```

## Diagnostic
- **Cause** : TestClient (sync) ne peut pas utiliser `async generator` retourné par `Depends(get_async_session)`
- **Règles projet** : Tests utilisent `db_session` sync fixture
- **Services** : `agent_services.py` mélangé async/sync cassé par ruff

## Correction Appliquée (✅ TERMINÉ)

### 1. **Fix Fixtures Test** (priorité 1)
```
tests/integration/api/test_agents_api.py
tests/integration/api/test_agent_scores_api.py
```
```python
def override_get_async_session():
    try
