# core/task_system.py

import asyncio
import uuid
import json
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from tinydb import TinyDB, Query
from fastapi.websockets import WebSocket

# Base de stockage des tâches planifiées et exécutées
db = TinyDB('./data/task_log.json')
TaskEntry = Query()

connected_clients: list[WebSocket] = []
running_tasks: Dict[str, dict] = {}

# --- Wrapper retourné par le décorateur --- #
class AsyncTaskRunner:
    def __init__(self, task_name: str, wrapper_func: Callable, max_retries: int = 3, retry_delay: float = 1.0):
        self.task_name = task_name
        self._wrapped = wrapper_func
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def run(self, *args, **kwargs):
        attempts = 0
        last_error = None

        while attempts < self.max_retries:
            try:
                return await self._wrapped(*args, **kwargs)
            except Exception as e:
                attempts += 1
                last_error = e
                if "connection attempts failed" in str(e).lower():
                    if attempts < self.max_retries:
                        await asyncio.sleep(self.retry_delay * attempts)
                        continue
                raise

        raise last_error or Exception(f"Task {self.task_name} failed after {self.max_retries} attempts")

# --- DÉCORATEUR --- #
class AsyncTask:
    registry: dict[str, 'AsyncTask'] = {}

    def __init__(self, name: Optional[str] = None, description: str = ""):
        self.name = name
        self.description = description
        self.func: Optional[Callable] = None

    def __call__(self, func: Callable):
        self.func = func
        self.name = self.name or func.__name__
        AsyncTask.registry[self.name] = self
        return self  # Retourne l'instance au lieu d'un wrapper

    async def run(self, *args, **kwargs):
        """Exécute la tâche avec monitoring."""
        task_id = str(uuid.uuid4())
        running_tasks[task_id] = {
            "name": self.name,
            "status": "running",
            "progress": 0,
            "started_at": datetime.utcnow().isoformat()
        }
        self.broadcast_update(task_id)

        update = self._monitor(task_id)

        try:
            if self.func:
                await self.func(update, *args, **kwargs)
            running_tasks[task_id]["status"] = "completed"
        except Exception as e:
            running_tasks[task_id]["status"] = "failed"
            running_tasks[task_id]["error"] = str(e)
            raise
        finally:
            running_tasks[task_id]["ended_at"] = datetime.utcnow().isoformat()
            db.insert({**running_tasks[task_id], "id": task_id})
            self.broadcast_update(task_id)

    def _monitor(self, task_id: str) -> Callable[[float, str], None]:
        def update(progress: float, message: str = ""):
            running_tasks[task_id]["progress"] = progress
            if message:
                running_tasks[task_id]["message"] = message
            self.broadcast_update(task_id)
        return update

    def broadcast_update(self, task_id: str):
        data = {"task_id": task_id, **running_tasks[task_id]}
        for ws in connected_clients:
            try:
                asyncio.create_task(ws.send_text(json.dumps(data)))
            except Exception:
                continue

# --- WebSocket --- #
async def register_ws(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

# --- Planification différée --- #
async def schedule_task(task_name: str, delay_sec: int = 0, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
    await asyncio.sleep(delay_sec)
    task = AsyncTask.registry.get(task_name)
    if task:
        runner = AsyncTaskRunner(task.name, task.run, max_retries=max_retries, retry_delay=retry_delay)
        await runner.run(**kwargs)
