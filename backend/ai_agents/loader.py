from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
from pathlib import Path
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, List
from backend.api.utils.logging import logger


# --- Pydantic Models --------------------------------------------------

class ActionDef(BaseModel):
    name: str
    description: str | None = None
    params: Dict[str, Any] = {}
    endpoint: str


class AgentDef(BaseModel):
    name: str
    model: str
    system_prompt: str
    actions: List[ActionDef] = []


class RouterRule(BaseModel):
    condition: str
    agent: str


class RouterDef(BaseModel):
    rules: List[RouterRule]


# --- Loader Class -----------------------------------------------------

class ConfigLoader:

    def __init__(self, base_dir: str = "orchestrator"):
        self.base = Path(base_dir)
        self.agents_dir = self.base / "agents"
        self.router_file = self.base / "router.yaml"

        self.agents: Dict[str, AgentDef] = {}
        self.router: RouterDef | None = None

    # Load all YAML files
    def load(self):
        self._load_agents()
        self._load_router()

    # --- Load agents definitions --------------------------------------

    def _load_agents(self):
        self.agents = {}
        for file in self.agents_dir.glob("*.yaml"):
            logger.info(f"[loader] Loading agent: {file.name}")
            try:
                with open(file, "r") as f:
                    raw = yaml.safe_load(f)
                    agent = AgentDef(**raw)
                    self.agents[agent.name] = agent
            except ValidationError as e:
                logger.info(f"[loader] ❌ Agent validation error in {file}: {e}")
            except Exception as e:
                logger.info(f"[loader] ❌ Error loading {file}: {e}")

    # --- Load router ---------------------------------------------------

    def _load_router(self):
        if not self.router_file.exists():
            logger.info("[loader] ⚠️ No router.yaml found")
            return

        try:
            with open(self.router_file, "r") as f:
                raw = yaml.safe_load(f)
                self.router = RouterDef(**raw)
                logger.info("[loader] Router loaded with", len(self.router.rules), "rules")
        except ValidationError as e:
            logger.info(f"[loader] ❌ Router validation error: {e}")
        except Exception as e:
            logger.info(f"[loader] ❌ Error loading router.yaml: {e}")

    # --- API -----------------------------------------------------------

    def get_agent(self, name: str) -> AgentDef | None:
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        return list(self.agents.keys())

    def get_router(self) -> RouterDef | None:
        return self.router

class ReloadHandler(FileSystemEventHandler):
    def __init__(self, loader: ConfigLoader):
        self.loader = loader

    def on_modified(self, event):
        if event.src_path.endswith(".yaml"):
            logger.info("\n[loader] 🔄 YAML updated → Reloading…\n")
            self.loader.load()


def enable_hot_reload(loader: ConfigLoader):
    event_handler = ReloadHandler(loader)
    observer = Observer()
    observer.schedule(event_handler, loader.base, recursive=True)
    observer.start()
    logger.info("[loader] 🔥 Hot reload enabled")
