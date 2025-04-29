# -*- coding: UTF-8 -*-
from annotated_types import T
import uvicorn
import os
import sys
import multiprocessing

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api_app import create_api

app = create_api()

if __name__ == "__main__":
    uvicorn.run("backend.api_app:app",
                host="0.0.0.0",
                port=8001,
                reload=True,
                reload_dirs=["backend"])