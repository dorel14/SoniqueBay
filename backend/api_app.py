# -*- coding: UTF-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import Base, engine

# Initialiser la base de données avant d'importer les modèles
Base.metadata.create_all(bind=engine)

# Importer les routes après l'initialisation de la base
from backend.api import api_router

app = FastAPI(title="SoniqueBay API",
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json")

# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les origines exactes
    allow_credentials=True,
    allow_methods=["*"],
)

app.include_router(api_router)
def create_api():
    """
    This function returns the FastAPI app instance.
    """
    return app

