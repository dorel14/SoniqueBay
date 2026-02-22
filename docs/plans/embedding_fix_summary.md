# Fix: Embedding Generation for MIR Synonyms

## Problem
The `backend/api/services/mir_synonym_service.py` was using `np.random.randn(768).tolist()` as a placeholder for generating embeddings (lines 466-469). This made the semantic search completely non-functional in production.

## Solution
Implemented a complete fix following the architecture rules (all embeddings must be generated in `backend_worker/`):

### Changes Made

#### 1. `backend_worker/services/ollama_embedding_service.py`
- **Changed model**: From `all-MiniLM-L6-v2` (384 dimensions) to `nomic-embed-text` (768 dimensions)
- **Updated documentation**: Reflects the new model and dimension count
- **Reason**: The database schema expects 768-dimensional vectors (Vector(768) in pgvector)

#### 2. `backend_worker/services/ollama_synonym_service.py`
- **Updated EMBEDDING_MODEL constant**: Changed from "all-MiniLM-L6-v2" to "nomic-embed-text"
- **Updated docstring**: Changed "384 dimensions" to "768 dimensions"

#### 3. `backend_worker/api/schemas/embedding_schema.py` (NEW FILE)
- Created separate Pydantic schemas for embedding requests/responses
- Follows the project convention of separating schemas from routers

#### 4. `backend_worker/api/schemas/__init__.py` (NEW FILE)
- Exports the embedding schemas

#### 5. `backend_worker/api/vectorization_router.py`
- **Added new endpoint**: `POST /api/vectorization/embed`
- **Uses separate schemas**: Imports from `backend_worker.api.schemas`
- **Generates real embeddings**: Calls `OllamaEmbeddingService` with nomic-embed-text
- **Updated status endpoint**: Changed model info from "all-MiniLM-L6-v2" to "nomic-embed-text"

#### 6. `backend/api/services/mir_synonym_service.py`
- **Replaced placeholder**: The `_generate_embedding` method now calls the backend_worker API
- **Uses httpx.AsyncClient**: Async HTTP call to worker service
- **Environment variable**: Uses `BACKEND_WORKER_URL` (defaults to `http://backend_worker:8003`)
- **Proper error handling**: Timeout and exception handling with fallback to None

## Architecture Compliance
✅ **Rule #2**: No direct Postgres access from backend_worker - The worker only exposes an API
✅ **Rule #3**: Uses environment variables from docker-compose (BACKEND_WORKER_URL)
✅ **Rule #5**: Schemas are in a separate folder (`backend_worker/api/schemas/`)
✅ **Rule #6**: Includes TODO comments for memory limits and fallbacks
✅ **Rule #8**: Plan documented in `docs/plans/`

## API Flow
```
Backend API (mir_synonym_service)
    ↓ HTTP POST /api/vectorization/embed
Backend Worker (vectorization_router)
    ↓ Calls
OllamaEmbeddingService (nomic-embed-text, 768D)
    ↓ Returns
Embedding vector (768 dimensions)
    ↓ Stored in
PostgreSQL (pgvector Vector(768))
```

## Testing Recommendations
1. Test the embedding endpoint directly:
   ```bash
   curl -X POST http://backend_worker:8003/api/vectorization/embed \
     -H "Content-Type: application/json" \
     -d '{"text": "rock music"}'
   ```

2. Test the full flow via the API:
   ```bash
   curl -X POST http://api:8001/api/mir/synonyms/search \
     -H "Content-Type: application/json" \
     -d '{"query": "rock", "tag_type": "genre"}'
   ```

## Notes
- The GMM clustering service (`gmm_clustering_service.py`) works with existing 64D audio feature embeddings - it doesn't generate embeddings, it clusters them. No changes needed there.
- The embedding dimension (768) matches the database schema exactly
- The worker service uses `sentence-transformers` library with the `nomic-embed-text` model
- All async operations use proper `async/await` patterns with `asyncio.to_thread` for CPU-bound embedding generation
