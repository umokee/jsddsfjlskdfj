"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Store database outside project directory to prevent data loss on git pull
# Default: /var/lib/task-manager/tasks.db (production)
# Fallback: ./tasks.db (development)
DB_DIR = os.getenv("TASK_MANAGER_DB_DIR", "/var/lib/task-manager")
DB_FILE = "tasks.db"

try:
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    DB_PATH = Path(DB_DIR) / DB_FILE
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
except PermissionError:
    # Fallback to local directory for development
    SQLALCHEMY_DATABASE_URL = "sqlite:///./tasks.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
