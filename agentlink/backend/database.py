"""
Database models and connection
"""
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL from environment (no default password for security)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agentlink@localhost:5432/agentlink")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AgentStateDB(Base):
    """SQLAlchemy model for Agent States"""
    __tablename__ = "agent_states"

    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Store complex objects as JSON
    task = Column(JSON, nullable=False)
    context = Column(JSON, nullable=False)
    knowledge = Column(JSON, nullable=False)
    working_memory = Column(JSON, nullable=False)
    handoff = Column(JSON, nullable=True)
    
    # Phase 5: State Locking & Coordination
    claimed_by = Column(String, nullable=True, index=True)
    claimed_at = Column(DateTime, nullable=True)
    claim_expires_at = Column(DateTime, nullable=True, index=True)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
