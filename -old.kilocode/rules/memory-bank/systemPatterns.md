# System Patterns

## Architecture Globale
`Frontend (NiceGUI)` ↔ `API (FastAPI/GraphQL)` ↔ `Workers (Celery)` ↔ `Data (Postgres/Redis)`

## Règles de Conception (Design Patterns)
- **Separation of Concerns** :
    - Le code métier lourd va dans les **Services** ou **Workers**.
    - L'API ne fait que de la validation et du dispatch.
    - Le Frontend ne contient aucune logique métier complexe.
- **Gestion des Données** :
    - L'API est la **seule** autorisée à effectuer des opérations CRUD sur PostgreSQL.
    - Redis est utilisé pour le cache et le Pub/Sub (SSE).
- **Asynchronisme** :
    - Utilisation intensive de `asyncio` pour les I/O.
    - Celery pour tout traitement > 500ms (Scan, Vectorisation).

## Conventions de Code (Python)
- **Style** : PEP8, typage strict (`typing`), docstrings obligatoires.
- **Logs** : **Pas de `print`**. Utiliser exclusivement `utils/logging.py`.
- **Tests** : Pytest + pytest-xdist. Tests modulaires dans `tests/`.

## Règles Spécifiques IA
- Ne jamais modifier `.env` ou toucher aux secrets.
- Ne pas introduire de dépendances bloquantes.
- Réutiliser le code existant avant de réécrire.
- Prioriser la maintenabilité sur la vitesse d'écriture.

## Workflow Git
- Branches : `feat/`, `fix/`, `refactor/`.
- Commits : `<type>(scope): message` (ex: `feat(player): add crossfade`).