"""
Application FastAPI pour le backend worker.
Permet la communication HTTP avec les autres services sans imports directs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend_worker.api.vectorization_router import router as vectorization_router


# Créer l'application FastAPI
app = FastAPI(
    title="SoniqueBay Backend Worker API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers
app.include_router(vectorization_router)

@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "healthy", "service": "backend_worker"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
