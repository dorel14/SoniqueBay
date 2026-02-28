from sqlalchemy import Column, Integer, String, Text, JSON, Boolean,Float

from backend.api.utils.database import Base, TimestampMixin
import os

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "koboldcpp/qwen2.5-3b-instruct-q4_k_m")

class AgentModel(Base, TimestampMixin):
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True, index=True)
    model = Column(String, nullable=False, default=DEFAULT_MODEL)
    enabled = Column(Boolean, default=True)

    base_agent = Column(String, nullable=True)

    # RTCROS
    role = Column(Text, nullable=False)
    task = Column(Text, nullable=False)
    constraints = Column(Text)
    rules = Column(Text)
    output_schema = Column(Text)
    state_strategy = Column(Text)

    # tools & meta
    tools = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    version = Column(String, default="1.0")

    # runtime LLM params
    temperature = Column(Float, default=0.2)
    top_p = Column(Float, default=0.9)
    num_ctx = Column(Integer, default=2048)
