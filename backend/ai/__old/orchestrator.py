# orchestrator.py
# Orchestrateur IA pour SoniqueBay – charge les YAML, route les intentions,
# appelle les sous-agents et gère le hot-reload.

import yaml
import time
import threading
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel
from pydantic_ai import Agent
from backend.api.utils.logging import logger

from backend.ai.router import IntentRouter
from backend.ai.loader import ConfigLoader
from backend.ai.__old.context_manager import ConversationContext
from backend.ai.agents import (
    orchestrator_agent,
    search_agent,
    playlist_agent,
    action_agent,
    smalltalk_agent
)

BUILDERS = {
    "orchestrator": orchestrator_agent.build_orchestrator_agent,
    "search_agent": search_agent.build_search_agent,
    "playlist_agent": playlist_agent.build_playlist_agent,
    "action_agent": action_agent.build_action_agent,
    "smalltalk_agent": smalltalk_agent.build_smalltalk_agent,
}


class Orchestrator:
    """
    Agent maître :
    - Charge tous les YAML dans /agents
    - Instancie les sous-agents pydanticAI
    - Gère l’état conversationnel
    - Route vers le bon agent
    - Hot reload auto des YAML si file change
    """

    def __init__(self, agents_dir: str = "./agents"):
        self.agents_dir = Path(agents_dir)
        self.loader = ConfigLoader(self.agents_dir)
        self.loader.load()
        self.context = ConversationContext()
        self.router = IntentRouter()
        self.agents: Dict[str, Agent] = {}
        self.timestamps: Dict[str, float] = {}

        self.load_all_agents()
        self.start_hot_reload_thread()

    # ------------------------------------------------------------
    # Chargement initial
    # ------------------------------------------------------------
    def load_all_agents(self):
        for yaml_file in self.agents_dir.glob("*.yaml"):
            self.load_agent_from_yaml(yaml_file)

    def load_agent_from_yaml(self, yaml_path: Path):
        cfg = self.loader.agents.get(yaml_path.stem)
        if not cfg:
            logger.warning(f"[Orchestrator] Agent YAML introuvable: {yaml_path}")
            return

        builder = BUILDERS.get(cfg.name)
        if not builder:
            logger.warning(f"[Orchestrator] Pas de builder pour l'agent, utilisation générique: {cfg.name}")
            def generic_builder(cfg): 
                return Agent(
                name=cfg.name,
                model=cfg.model,
                system_prompt=cfg.system_prompt,
                response_format=cfg.response_schema
                )
            builder = generic_builder

        agent = builder(cfg)
        self.agents[cfg.name] = agent
        self.timestamps[cfg.name] = yaml_path.stat().st_mtime

        logger.info(f"[Orchestrator] Agent chargé : {agent.name}")

    # ------------------------------------------------------------
    # Hot reload YAML
    # ------------------------------------------------------------
    def start_hot_reload_thread(self):
        def watch():
            while True:
                time.sleep(1)
                for yaml_path in self.agents_dir.glob("*.yaml"):
                    name = yaml_path.stem
                    ts = yaml_path.stat().st_mtime
                    if name in self.timestamps and ts != self.timestamps[name]:
                        logger.info(f"[Hot-reload] Rechargement agent {name}")
                        self.load_agent_from_yaml(yaml_path)

        thread = threading.Thread(target=watch, daemon=True)
        thread.start()

    # ------------------------------------------------------------
    # Traitement utilisateur
    # ------------------------------------------------------------
    async def handle_user_message(self, message: str) -> Dict[str, Any]:
        """Entrée du chatbot : détection de l’intention → sous-agent → résultat."""

        # Étape 1 : identifier l’intention avec orchestrator.yaml
        orch_agent = self.agents.get("orchestrator")
        intent_res = await orch_agent.run(message)

        intent = intent_res.get("intent")
        agent_name = intent_res.get("agent")

        # Mémoriser contexte        
        self.context.add_user_message(message)
        self.context.last_intent = intent

        # Étape 2 : route vers agent choisi
        if agent_name not in self.agents:
            return {"error": f"Agent inconnu: {agent_name}"}

        agent = self.agents[agent_name]
        result = await agent.run(message)

        self.context.add_agent_message(agent_name, result)
        # Étape 3 : mettre à jour contexte humeur si smalltalk
        if agent_name == "smalltalk_agent":
            self.context.mood = result.get("mood")

        return result
