from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime
from backend.database import Base

class Setting(Base):
    __tablename__ = 'settings'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=True)  # Valeur cryptée
    is_encrypted = Column(Boolean, default=False)
    description = Column(String, nullable=True)
    date_added = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
