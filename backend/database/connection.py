import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

db_url = settings.DATABASE_URL

# Normalize SQLite database path to be absolute relative to workspace root
if db_url.startswith("sqlite:///"):
    db_relative_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_relative_path):
        # backend/database/connection.py -> parent -> parent -> root
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_absolute_path = os.path.join(root_dir, db_relative_path)
        db_absolute_path = db_absolute_path.replace("\\", "/")
        db_url = f"sqlite:///{db_absolute_path}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False, "timeout": 30} if db_url.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
