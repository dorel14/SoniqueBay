# -*- coding: UTF-8 -*-

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
import os
import sys


# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.api_app import create_api

app = create_api()
# Add socketio app to the main app

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )

if __name__ == "__main__":
    uvicorn.run("backend.api_app:app",
                host="0.0.0.0",
                port=8001,
                forwarded_allow_ips="*",  # Permettre les en-têtes forwarded
                proxy_headers=True,  # Activer le support des proxy headers
                reload=True,  # Recharger l'application automatiquement en cas de modification du code
                reload_dirs=("/backend"))