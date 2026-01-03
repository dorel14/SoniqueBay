from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from backend.api.utils.database import Base

class AgentScore(Base):
    __tablename__ = "agent_scores"

    id = Column(Integer, primary_key=True)
    agent_name = Column(String, index=True)
    intent = Column(String, index=True)

    score = Column(Float, default=1.0)
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("agent_name", "intent", name="uq_agent_intent"),
    )