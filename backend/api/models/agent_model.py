from sqlalchemy import String, Text, JSON, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin
import os

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "koboldcpp/qwen2.5-3b-instruct-q4_k_m")


class AgentModel(Base, TimestampMixin):
    __tablename__ = "ai_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    model: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_MODEL)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    base_agent: Mapped[str | None] = mapped_column(String, nullable=True)

    # RTCROS
    role: Mapped[str] = mapped_column(Text, nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[str | None] = mapped_column(Text)
    output_schema: Mapped[str | None] = mapped_column(Text)
    state_strategy: Mapped[str | None] = mapped_column(Text)

    # tools & meta
    tools: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[str] = mapped_column(String, default="1.0")

    # runtime LLM params
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    top_p: Mapped[float] = mapped_column(Float, default=0.9)
    num_ctx: Mapped[int] = mapped_column(Integer, default=2048)
