
# -*- coding: UTF-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import api_router


app = FastAPI(title="SoniqueBay API",
                version="1.0.0",
                docs_url="/api/docs",
                openapi_url="/api/openapi.json",)
# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les origines exactes
    allow_credentials=True,
    allow_methods=["*"],
)

app.include_router(api_router)
def create_api():
    return app
