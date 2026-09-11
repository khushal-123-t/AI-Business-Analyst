import os
from pathlib import Path
from dotenv import load_dotenv

# Locate project root reliably regardless of current working directory
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")

class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()  # "gemini" (sole provider)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///database/business.db")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CSV_CHUNK_SIZE: int = int(os.getenv("CSV_CHUNK_SIZE", "10000"))

settings = Settings()
