from sqlalchemy import String, Float, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.api.utils.database import Base


class AgentScore(Base):
    __tablename__ = "agent_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_name: Mapped[str] = mapped_column(String, index=True)
    intent: Mapped[str] = mapped_column(String, index=True)

    score: Mapped[float] = mapped_column(Float, default=1.0)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (UniqueConstraint("agent_name", "intent", name="uq_agent_intent"),)
