import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

logger = logging.getLogger("ai_analyst.database")

# ==============================================================================
# IMPORTANT RENDER / PRODUCTION DATABASE NOTICE:
# Render's default Web Service filesystem is EPHEMERAL. Any SQLite database file
# (e.g. database/business.db) created on disk will be reset or lost upon service
# redeployments or container restarts.
#
# FOR PRODUCTION DATA PERSISTENCE:
# Set the DATABASE_URL environment variable in your Render dashboard to a managed
# PostgreSQL instance (e.g., postgresql://user:password@host/dbname).
# The code below automatically detects PostgreSQL and connects seamlessly without
# modifying any code or table schemas.
# ==============================================================================

# Locate project root reliably regardless of current working directory:
# backend/database/connection.py -> parent: backend/database -> parent: backend -> parent: project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_database_url_and_prep() -> tuple[str, dict]:
    """
    Parses and prepares the DATABASE_URL for SQLAlchemy:
    1. For SQLite:
       - Converts relative paths to absolute paths anchored to project root.
       - Ensures the target directory exists (mkdir -p) before engine creation.
       - Applies SQLite connect_args (check_same_thread=False, timeout=30).
    2. For PostgreSQL:
       - Normalizes legacy 'postgres://' schema prefix to 'postgresql://'.
       - Leaves connection args clean for PostgreSQL driver.
    """
    raw_url = (settings.DATABASE_URL or "").strip()
    if not raw_url:
        raw_url = "sqlite:///database/business.db"

    # 1. PostgreSQL Support
    if raw_url.startswith("postgres://") or raw_url.startswith("postgresql://") or raw_url.startswith("postgresql+"):
        # Fix Render/Heroku legacy postgres:// schema prefix for SQLAlchemy 1.4+
        normalized_url = raw_url.replace("postgres://", "postgresql://", 1)
        safe_url = normalized_url.split("@")[-1] if "@" in normalized_url else "configured"
        logger.info(f"[Database] Configured PostgreSQL database connection target: @{safe_url}")
        print(f"[Database] Using PostgreSQL connection (target: @{safe_url})")
        return normalized_url, {}

    # 2. SQLite Support
    if raw_url.startswith("sqlite:"):
        # Special case for in-memory databases
        if ":memory:" in raw_url:
            logger.info("[Database] Using in-memory SQLite database.")
            return raw_url, {"check_same_thread": False, "timeout": 30}

        # Strip sqlite:/// or sqlite:// prefix to get the file path
        if raw_url.startswith("sqlite:///"):
            path_part = raw_url[len("sqlite:///"):]
        elif raw_url.startswith("sqlite://"):
            path_part = raw_url[len("sqlite://"):]
        else:
            path_part = raw_url

        # Check if path_part is absolute
        if os.path.isabs(path_part):
            resolved_path = Path(path_part).resolve()
        else:
            resolved_path = (PROJECT_ROOT / path_part).resolve()

        # PRODUCTION FIX: Ensure parent directory exists BEFORE create_engine is invoked
        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[Database] Verified database directory: {resolved_path.parent}")
        except Exception as dir_err:
            logger.error(f"[Database] CRITICAL: Failed to create database directory '{resolved_path.parent}': {dir_err}")
            raise

        # Convert to POSIX format for SQLAlchemy URL
        posix_path = resolved_path.as_posix()
        # On Linux: starts with '/' -> sqlite:////opt/render/project/src/database/business.db (valid absolute path)
        # On Windows: starts with 'C:/' -> sqlite:///C:/.../database/business.db (valid Windows path)
        final_url = f"sqlite:///{posix_path}"
        logger.info(f"[Database] SQLite resolved to: {resolved_path}")
        print(f"[Database] SQLite resolved to: {resolved_path}")
        return final_url, {"check_same_thread": False, "timeout": 30}

    # 3. Fallback for other databases
    logger.info(f"[Database] Using custom database URL: {raw_url.split('://')[0]}://...")
    return raw_url, {}


# Prepare engine with resolved URL and appropriate connect_args
db_url, connect_args = get_database_url_and_prep()

engine = create_engine(
    db_url,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
