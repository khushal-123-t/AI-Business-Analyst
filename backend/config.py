import os
from dotenv import load_dotenv

# Load env file from the parent directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(root_dir, ".env"))

class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()  # "gemini" (sole provider)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///database/business.db")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")
    CSV_CHUNK_SIZE: int = int(os.getenv("CSV_CHUNK_SIZE", "10000"))

settings = Settings()

