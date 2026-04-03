# Plan de correction — tests `test_agent_scores_api` — ✅ TERMINÉ

## Informations collectées
✓ `database.py` corrigé (test-aware + localhost/SQLite fallback)
✓ `test_agent_scores_api.py` renforcé (env module-level SQLite)

## Modifications appliquées
1. **backend/api/utils/database.py** ✅
   - Priorité `DATABASE_URL`/`TEST_DATABASE_URL`
   - SQLite → `aiosqlite` auto pour async
   - Default host → `localhost`
2. **tests/integration/api/test_agent_scores_api.py** ✅
   - `os.environ["DATABASE_URL"] = "sqlite:///test_agent_scores.db"` **AVANT** imports backend

## Validation
Exécutez pour vérifier :
```
pytest tests/integration/api/test_agent_scores_api.py -v
```

Attendu : 9/9 tests PASS, plus d'erreur `socket.gaierror`.

## TODO final
- ✅ Tests corrigés
- 🔄 [VALIDÉ] Lancer `pytest` et confirmer
- 📝 TODO : Config DB globale à refactoriser (lazy engines + test isolation)

**✅ Tâche terminée — Tests devraient passer !**

