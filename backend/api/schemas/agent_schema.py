from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "koboldcpp/qwen2.5-3b-instruct-q4_k_m")
class AgentCreate(BaseModel):
    name: str
    model: str = DEFAULT_MODEL
    enabled: bool = True
    base_agent: Optional[str] = None
    role: str
    task: str
    constraints: Optional[str] = None
    rules: Optional[str] = None
    output_schema: Optional[str] = None
    state_strategy: Optional[str] = None
    tools: List[Dict[str, Any]] = []
    tags: List[str] = []
    version: str = "1.0"
    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int = 2048

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    enabled: Optional[bool] = None
    base_agent: Optional[str] = None
    role: Optional[str] = None
    task: Optional[str] = None
    constraints: Optional[str] = None
    rules: Optional[str] = None
    output_schema: Optional[str] = None
    state_strategy: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    num_ctx: Optional[int] = None

class AgentOut(BaseModel):
    id: int
    name: str
    model: str
    enabled: bool
    base_agent: Optional[str] = None
    role: str
    task: str
    constraints: Optional[str] = None
    rules: Optional[str] = None
    output_schema: Optional[str] = None
    state_strategy: Optional[str] = None
    tools: Any
    tags: Any
    version: str
    temperature: float
    top_p: float
    num_ctx: int

    class Config:
        from_attributes = True
